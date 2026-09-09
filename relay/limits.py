"""Atomic limits for the single-instance, ephemeral public demo."""

import os
import sqlite3
import time
from pathlib import Path


def take(kind, limit, seconds=86400):
    if os.getenv("RELAY_PUBLIC_DEMO") != "1":
        return
    path = os.getenv("RELAY_LIMIT_DB", "work/limits.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bucket = int(time.time()) // seconds
    with sqlite3.connect(path, timeout=10) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS limits (kind TEXT, bucket INTEGER, used INTEGER, PRIMARY KEY(kind, bucket))"
        )
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT used FROM limits WHERE kind=? AND bucket=?", (kind, bucket)).fetchone()
        if row and row[0] >= limit:
            raise ValueError(
                "The public demo has reached its shared usage limit. Please try later or watch the recorded demo."
            )
        db.execute(
            "INSERT INTO limits VALUES (?, ?, 1) ON CONFLICT(kind, bucket) DO UPDATE SET used=used+1",
            (kind, bucket),
        )
        db.execute("DELETE FROM limits WHERE kind=? AND bucket<?", (kind, bucket - 1))
