"""Durable bounded jobs; the public web process never owns agent execution."""

import json
import os
import time
import uuid

import boto3
from botocore.config import Config

from . import domain
from .store import Store

REGISTRY = "system-workspaces"
LEASE_SECONDS = 960


def due(data):
    from .negotiation import needs_negotiation

    return [
        i["id"]
        for i in data["incidents"]
        if i["status"] in {"reported", "delayed"}
        or needs_negotiation(data, i)
        or (i["status"] == "scheduled" and i["next_check"] and i["next_check"] <= domain.now())
    ]


def register(store, token):
    def change(data):
        if token not in data["workspaces"]:
            if len(data["workspaces"]) >= 100:
                raise ValueError("The AWS demonstration has reached its workspace limit.")
            data["workspaces"].append(token)

    store.mutate(REGISTRY, change)


def take_persistent(kind, limit):
    def change(data):
        used = data.setdefault("usage", {}).get(kind, 0)
        if used >= limit:
            raise ValueError("The AWS demonstration has reached its shared usage limit.")
        data["usage"][kind] = used + 1

    Store().mutate(REGISTRY, change)


def running(store, token):
    lease = store.read(REGISTRY)[1].get("lease") or {}
    return lease.get("workspace") == token and lease.get("expires", 0) > time.time()


def dispatch(store, token, automatic=False):
    data = store.read(token)[1]
    if automatic and data["runs"] and data["runs"][-1]["error"]:
        return {"started": False}
    ids = due(data)
    if not ids:
        return {"started": False, "message": "No agent work is due. Waiting for a human action."}
    job = uuid.uuid4().hex

    def claim(registry):
        lease = registry.get("lease") or {}
        if lease.get("expires", 0) > time.time():
            raise ValueError("The demo agent is busy. Please try again shortly.")
        if registry.get("runs", 0) >= 100:
            raise ValueError("The AWS demonstration has reached its total agent-run limit.")
        registry["runs"] = registry.get("runs", 0) + 1
        registry["lease"] = {
            "job": job,
            "workspace": token,
            "expires": int(time.time()) + LEASE_SECONDS,
            "claimed": False,
        }

    store.mutate(REGISTRY, claim)
    try:
        boto3.client("lambda").invoke(
            FunctionName=os.environ["RELAY_DISPATCH_FUNCTION"],
            InvocationType="Event",
            Payload=json.dumps({"workspace_id": token, "incident_ids": ids, "job": job}),
        )
    except Exception:
        release(store, job)
        raise
    return {"started": True}


def release(store, job):
    def change(data):
        if (data.get("lease") or {}).get("job") == job:
            data["lease"] = None

    store.mutate(REGISTRY, change)


def claim_execution(store, job):
    def change(data):
        lease = data.get("lease") or {}
        if lease.get("job") != job or lease.get("claimed") or lease.get("expires", 0) <= time.time():
            return False
        lease["claimed"] = True
        return True

    return store.mutate(REGISTRY, change)


def handler(event, context):
    store = Store()
    if event.get("source") == "aws.events":
        for token in store.read(REGISTRY)[1]["workspaces"]:
            try:
                if dispatch(store, token, automatic=True).get("started"):
                    return {"dispatched": True}
            except ValueError:
                continue
        return {"dispatched": False}
    job = event["job"]
    if not claim_execution(store, job):
        return {"duplicate_or_expired": True}
    client = boto3.client("bedrock-agentcore", config=Config(read_timeout=850, retries={"max_attempts": 0}))
    session = str(uuid.uuid4())
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=os.environ["RELAY_AGENT_ARN"],
            runtimeSessionId=session,
            payload=json.dumps(event),
            contentType="application/json",
        )
        # Consume the response so execution finishes before releasing the durable lease.
        response["response"].read()
        return {"completed": True, "job": job}
    except Exception as exc:
        error_name = type(exc).__name__

        def fail(data):
            data["runs"] = (
                data["runs"]
                + [
                    {
                        "id": domain.uid("run"),
                        "at": domain.now(),
                        "provider": "bedrock",
                        "model": os.environ["RELAY_MODEL_ID"],
                        "calls": [],
                        "stages": [],
                        "summary": "AWS agent invocation failed. Completed actions are preserved; retry manually.",
                        "error": error_name,
                        "status": "failed",
                        "seconds": 0,
                    }
                ]
            )[-12:]

        store.mutate(event["workspace_id"], fail)
        raise
    finally:
        try:
            client.stop_runtime_session(
                agentRuntimeArn=os.environ["RELAY_AGENT_ARN"], runtimeSessionId=session
            )
        finally:
            release(store, job)
