"""Bounded live proof for the existing DynamoDB Store adapter; synthetic records only."""

import argparse
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime

import boto3

from relay.store import Conflict, Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="society-relay-hackathon-proof")
    args = parser.parse_args()
    if args.table != "society-relay-hackathon-proof":
        parser.error("This proof only writes to the dedicated hackathon proof table.")

    first = Store(table=args.table)
    second = Store(table=args.table)
    token = "proof-" + uuid.uuid4().hex
    first.create(token, {"incidents": [], "runs": [], "proof_counter": 0})
    version, body = first.read(token)
    assert version == 0 and body["proof_counter"] == 0
    body["proof_counter"] = 1
    first.write(token, version, body)
    try:
        second.write(token, version, {"proof_counter": 999})
    except Conflict:
        pass
    else:
        raise AssertionError("A stale write overwrote the current record")

    attempts = 0

    def race_once(current):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            other_version, other_body = second.read(token)
            other_body["proof_counter"] = 10
            second.write(token, other_version, other_body)
        current["proof_counter"] += 1

    first.mutate(token, race_once)
    assert attempts == 2
    final_version, final_body = second.read(token)
    assert final_body["proof_counter"] == 11
    # A separate interpreter must read the same committed state without any local database.
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,sys; from relay.store import Store; print(json.dumps(Store(table=sys.argv[1]).read(sys.argv[2])))",
            args.table,
            token,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(child.stdout) == [final_version, final_body]
    print(
        json.dumps(
            {
                "verified_at": datetime.now(UTC).isoformat(),
                "table": args.table,
                "region": boto3.session.Session().region_name,
                "boto3_version": boto3.__version__,
                "status": "passed",
                "checks": [
                    "create and strongly consistent read",
                    "stale conditional write rejected",
                    "mutation retries against newer state",
                    "separate process reads committed state",
                ],
                "retry_attempts": attempts,
                "final_version": final_version,
                "final_counter": final_body["proof_counter"],
                "synthetic_records_created": 1,
                "ai_invoked": False,
                "public_app_uses_this_table": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
