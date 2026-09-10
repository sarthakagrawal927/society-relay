"""Frozen synthetic challenge set; compare observable outcomes, keep every live attempt."""

import argparse
import ast
import hashlib
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "docs/evaluations/challenge-v1/cases.json"
DEST = CASES.parent
STOP = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "of",
    "for",
    "is",
    "are",
    "has",
    "have",
    "our",
    "my",
    "and",
    "to",
    "at",
    "it",
    "its",
    "this",
    "today",
    "here",
    "there",
    "no",
    "not",
}


def tokens(text):
    return set(re.findall(r"\w+", text.lower())) - STOP


def explicit_hazard(text):
    words = re.findall(r"\w+", text.lower())
    return any(
        w in {"smoke", "sparks", "sparking", "fire"}
        and not set(words[max(0, n - 3) : n]).intersection({"no", "not", "without"})
        for n, w in enumerate(words)
    )


def baseline(case, strategy):
    """Three deliberately small, inspectable non-LLM classifiers; no learned dictionaries."""
    hazards = [n for n, r in enumerate(case["reports"]) if explicit_hazard(r["text"])]
    groups = []
    for n, report in enumerate(case["reports"]):
        if n in hazards:
            continue
        target = None
        for group in groups:
            representative = case["reports"][group[0]]
            allowed = (
                report["scope"] == representative["scope"] == "shared"
                and report["area"] == representative["area"]
                and report["category"] == representative["category"]
            )
            a, b = tokens(report["text"]), tokens(representative["text"])
            overlap = len(a & b) / max(1, len(a | b))
            if allowed and (strategy == "metadata" or (strategy == "lexical" and overlap >= 0.30)):
                target = group
                break
        if target is None:
            groups.append([n])
        else:
            target.append(n)
    return {"groups": groups, "hazards": hazards}


def canonical(groups):
    return sorted(sorted(g) for g in groups)


def score(case, decision):
    return {
        "grouping_exact": canonical(decision["groups"]) == canonical(case["groups"]),
        "hazards_exact": sorted(decision["hazards"]) == sorted(case["hazards"]),
    }


class Client:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self.http = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def request(self, path, body=None):
        request = urllib.request.Request(
            self.url + "/api" + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "SocietyRelay-Acceptance/1.0"},
        )
        with self.http.open(request, timeout=60) as response:
            return json.load(response)

    def settle(self):
        # A scheduler tick can race the report upload. Finish only remaining work,
        # and never retry a failed model automatically or discard its record.
        for _ in range(2):
            state = self.request("/state")
            if state["runs"] and state["runs"][-1]["error"]:
                return state
            if not state["running"]:
                if all(i["status"] != "reported" for i in state["incidents"]):
                    return state
                self.request("/agent", {})
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                state = self.request("/state")
                if not state["running"]:
                    break
                time.sleep(2)
            else:
                raise TimeoutError("Agent did not settle within 180 seconds")
        return self.request("/state")


def run_case(case, url):
    client = Client(url)
    client.request("/session", {})
    identifiers = []
    for n, report in enumerate(case["reports"]):
        result = client.request("/reports", {**report, "request_id": f"challenge-{case['id']}-{n}"})
        identifiers.append(result["id"])
    state = client.settle()
    roots = {}
    hazards = []
    for n, ident in enumerate(identifiers):
        incident = next(i for i in state["incidents"] if i["id"] == ident)
        if incident["status"] == "needs_attention" and not incident["proposal"]:
            hazards.append(n)
        else:
            roots.setdefault(incident["merged_into"] or ident, []).append(n)
    decision = {"groups": list(roots.values()), "hazards": hazards}
    checks = score(case, decision)
    checks.update(
        run_completed=bool(state["runs"]) and all(not r["error"] for r in state["runs"]),
        humans_retain_authority=all(
            not i["confirmed"]
            and i["status"] not in {"scheduled", "resolved"}
            and (not i["proposal"] or not i["proposal"]["approved"])
            for i in state["incidents"]
        ),
        fixed_quotes=all(
            not i["proposal"] or i["proposal"]["quote"] in {900, 1200, 1800} for i in state["incidents"]
        ),
    )
    # Store observations, not model hidden reasoning, cookies, or credentials.
    return {
        "case": case["id"],
        "checks": checks,
        "passed": all(checks.values()),
        "decision": decision,
        "incidents": state["incidents"],
        "events": state["events"],
        "runs": [
            {k: r.get(k) for k in ["id", "provider", "model", "status", "error", "seconds", "calls"]}
            for r in state["runs"]
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--only-case", action="append", help="Focused recovery follow-up; preserve original benchmark")
    parser.add_argument(
        "--component", action="store_true", help="Eight Bedrock classification calls; no workflow actions"
    )
    parser.add_argument("--url", default="https://relay.sarthakagrawal.dev")
    args = parser.parse_args()
    cases = json.loads(CASES.read_text())["cases"]
    if args.only_case:
        cases = [c for c in cases if c["id"] in args.only_case]
        if not cases or len(cases) != len(set(args.only_case)):
            raise SystemExit("Unknown case selection")
    for case in cases:
        assert sorted([i for g in case["groups"] for i in g] + case["hazards"]) == list(
            range(len(case["reports"]))
        )
    report = {
        "case_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
        "at": datetime.now(UTC).isoformat(),
        "url": args.url,
        "baselines": {
            name: [
                {"case": c["id"], "decision": baseline(c, name), "checks": score(c, baseline(c, name))}
                for c in cases
            ]
            for name in ["separate", "metadata", "lexical"]
        },
        "live": [],
    }
    if args.component:
        import boto3
        from botocore.config import Config

        tree = ast.parse((ROOT / "relay/agent.py").read_text())
        prompt = next(
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant)
            and isinstance(n.value, str)
            and n.value.startswith("Classify maintenance reports.")
        )
        report["scope"] = "Isolated deployed evidence-specialist prompt on Bedrock; not full workflow runs"
        report["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
        report["model"] = "amazon.nova-pro-v1:0"
        client = boto3.client(
            "bedrock-runtime",
            region_name="us-east-1",
            config=Config(retries={"total_max_attempts": 1}, read_timeout=90),
        )
        destination = DEST / (datetime.now(UTC).strftime("component-%Y%m%dT%H%M%SZ") + ".json")
        destination.write_text(json.dumps(report, indent=2))
        for case in cases:
            started = time.monotonic()
            reports = [
                {"id": str(n), "description": r["text"], **{k: r[k] for k in ["area", "category", "scope"]}}
                for n, r in enumerate(case["reports"])
            ]
            try:
                response = client.converse(
                    modelId=report["model"],
                    system=[{"text": prompt}],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"text": json.dumps({"reports": reports, "human_separated_pairs": []})}
                            ],
                        }
                    ],
                    inferenceConfig={"maxTokens": 1500, "temperature": 0.1},
                )
                raw = json.loads("".join(c.get("text", "") for c in response["output"]["message"]["content"]))
                decision = {
                    "groups": [[int(n) for n in g] for g in raw["groups"]],
                    "hazards": [int(n) for n in raw["hazards"]],
                }
                checks = score(case, decision)
                result = {
                    "case": case["id"],
                    "decision": decision,
                    "checks": checks,
                    "passed": all(checks.values()),
                    "usage": response.get("usage"),
                    "request_id": response["ResponseMetadata"]["RequestId"],
                }
            except Exception as error:  # noqa: BLE001 -- preserve failed attempts, no provider response leakage
                result = {"case": case["id"], "passed": False, "error": type(error).__name__}
            result["wall_seconds"] = round(time.monotonic() - started, 2)
            report["live"].append(result)
            destination.write_text(json.dumps(report, indent=2))
            print(json.dumps(result), flush=True)
        print(str(destination), flush=True)
    elif args.live:
        destination = DEST / (datetime.now(UTC).strftime("live-%Y%m%dT%H%M%SZ") + ".json")
        destination.write_text(json.dumps(report, indent=2))
        for case in cases:
            started = time.monotonic()
            try:
                result = run_case(case, args.url)
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                result = {"case": case["id"], "passed": False, "error": type(error).__name__}
            result["wall_seconds"] = round(time.monotonic() - started, 2)
            report["live"].append(result)
            destination.write_text(json.dumps(report, indent=2))
            print(
                json.dumps({k: result.get(k) for k in ["case", "passed", "checks", "error", "wall_seconds"]}),
                flush=True,
            )
        print(str(destination), flush=True)
    else:
        destination = DEST / "baselines.json"
        destination.write_text(json.dumps(report, indent=2))
        for name, rows in report["baselines"].items():
            print(name, sum(all(r["checks"].values()) for r in rows), "/", len(rows))


if __name__ == "__main__":
    main()
