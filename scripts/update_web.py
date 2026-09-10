"""Update only the web Lambda from a reviewed commit; preserve deployed dependencies and IAM."""

import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile

import boto3

FILES = ["relay/app.py", "relay/static/index.html", "relay/static/app.js",
         "relay/static/style.css", "relay/static/journey.js", "relay/static/repair.html",
         "relay/static/repair.css", "relay/static/repair.js", "relay/static/repair-proof.json", "relay/static/architecture.svg"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_ref):
        raise SystemExit("Use an exact reviewed commit SHA.")
    print(json.dumps({"function": "society-relay-live-web", "source": args.source_ref,
                      "files": FILES, "apply": args.apply}))
    if not args.apply:
        return
    if boto3.client("sts").get_caller_identity()["Account"] != args.expected_account:
        raise SystemExit("Account mismatch.")
    client = boto3.client("lambda", region_name="us-east-1")
    current = client.get_function(FunctionName="society-relay-live-web")
    # The signed download URL is used in memory only and is never printed or persisted.
    with urllib.request.urlopen(current["Code"]["Location"], timeout=60) as response:
        original = response.read()
    replacements = {}
    for path in FILES:
        url = f"https://raw.githubusercontent.com/sarthakagrawal927/society-relay/{args.source_ref}/{path}"
        with urllib.request.urlopen(url, timeout=30) as response:
            replacements[path] = response.read()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as old, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as new:
        for entry in old.infolist():
            if entry.filename not in replacements:
                new.writestr(entry, old.read(entry.filename))
        for path, content in replacements.items():
            new.writestr(path, content)
    artifact = output.getvalue()
    bucket = f"society-relay-live-artifacts-{args.expected_account}"
    key = f"web-updates/{args.source_ref}.zip"
    boto3.client("s3", region_name="us-east-1").put_object(Bucket=bucket, Key=key, Body=artifact)
    result = client.update_function_code(
        FunctionName="society-relay-live-web", S3Bucket=bucket, S3Key=key,
        RevisionId=current["Configuration"]["RevisionId"], Publish=False,
    )
    client.get_waiter("function_updated_v2").wait(FunctionName="society-relay-live-web")
    print(json.dumps({"updated": result["FunctionName"], "code_sha256": result["CodeSha256"],
                      "source_sha256": {p: hashlib.sha256(c).hexdigest() for p, c in replacements.items()}}))


if __name__ == "__main__":
    main()
