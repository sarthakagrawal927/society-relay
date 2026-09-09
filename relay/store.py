"""Versioned, atomic workspace storage. No agent conversation owns durable state."""

import copy
import json
import os
import sqlite3
from pathlib import Path


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path=None, table=None):
        self.table = table or os.getenv("RELAY_TABLE")
        self.path = str(path or os.getenv("RELAY_DB", "work/relay.db"))
        if self.table:
            import boto3

            self.ddb = boto3.resource("dynamodb").Table(self.table)
        else:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with self.connection() as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, version INTEGER, body TEXT)"
                )

    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def create(self, workspace_id, body):
        encoded = json.dumps(body)
        if self.table:
            self.ddb.put_item(
                Item={"id": workspace_id, "version": 0, "body": encoded},
                ConditionExpression="attribute_not_exists(id)",
            )
        else:
            with self.connection() as db:
                db.execute("INSERT INTO workspaces VALUES (?, 0, ?)", (workspace_id, encoded))

    def read(self, workspace_id):
        if self.table:
            row = self.ddb.get_item(Key={"id": workspace_id}, ConsistentRead=True).get("Item")
            if not row:
                raise KeyError(workspace_id)
            return int(row["version"]), json.loads(row["body"])
        with self.connection() as db:
            row = db.execute("SELECT version, body FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
        if not row:
            raise KeyError(workspace_id)
        return row[0], json.loads(row[1])

    def write(self, workspace_id, version, body):
        encoded = json.dumps(body)
        if len(encoded.encode()) > 300_000:
            raise ValueError("This demo workspace is full. Start a new demo workspace.")
        if self.table:
            from botocore.exceptions import ClientError

            try:
                self.ddb.put_item(
                    Item={"id": workspace_id, "version": version + 1, "body": encoded},
                    ConditionExpression="#v = :v",
                    ExpressionAttributeNames={"#v": "version"},
                    ExpressionAttributeValues={":v": version},
                )
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    raise Conflict() from exc
                raise
        else:
            with self.connection() as db:
                result = db.execute(
                    "UPDATE workspaces SET version=?, body=? WHERE id=? AND version=?",
                    (version + 1, encoded, workspace_id, version),
                )
                if result.rowcount != 1:
                    raise Conflict()

    def mutate(self, workspace_id, fn):
        for _ in range(8):
            version, body = self.read(workspace_id)
            updated = copy.deepcopy(body)
            result = fn(updated)
            try:
                self.write(workspace_id, version, updated)
                return result
            except Conflict:
                continue
        raise Conflict("Workspace is busy; please retry.")

    def workspace_ids(self):
        """Small demo scheduler inventory. DynamoDB production scheduling uses explicit events."""
        if self.table:
            return []
        with self.connection() as db:
            return [row[0] for row in db.execute("SELECT id FROM workspaces")]
