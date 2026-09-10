"""Exercise one synthetic difficult repair against the public app; record observable outcomes only."""

import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default="docs/difficult-repair-evidence.json")
    args = parser.parse_args()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    proof = {"url": args.url, "verified_at": datetime.now(UTC).isoformat(),
             "synthetic": True, "checkpoints": []}

    def request(path, body=None):
        req = urllib.request.Request(args.url + "/api" + path,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "SocietyRelay-Acceptance/1.0"})
        with client.open(req, timeout=60) as response:
            return json.load(response)

    def snapshot(label):
        state = request("/state")
        incident = next((i for i in state["incidents"] if i["status"] != "linked"), None)
        proof["checkpoints"].append({"label": label, "incident": incident,
                                     "availability": state["availability"], "events": state["events"]})
        # Omit model prose and session identifiers; retain auditable tool names/arguments/outcomes.
        proof["runs"] = [{k: run.get(k) for k in ["id", "provider", "model", "seconds", "status", "error", "calls"]}
                         for run in state["runs"]]
        Path(args.output).write_text(json.dumps(proof, indent=2))
        print(label, incident["status"] if incident else "empty", flush=True)
        return state, incident

    def agent():
        before = request("/state")
        if not before["running"]:
            request("/agent", {})
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            state = request("/state")
            if not state["running"] and len(state["runs"]) > len(before["runs"]):
                run = state["runs"][-1]
                assert not run["error"], run["error"]
                assert run["provider"] == "bedrock" and run["model"] == "amazon.nova-pro-v1:0"
                return
            time.sleep(2)
        raise RuntimeError("The agent did not finish within three minutes.")

    def action(i, name, role, **extra):
        return request(f"/incidents/{i['id']}/action", {"action": name, "role": role,
                       "proposal_id": (i.get("proposal") or {}).get("id"), **extra})

    def consent(i, answer):
        n = i["negotiation"]
        assert n["status"] == "waiting" and len(n["required"]) == 1
        request(f"/incidents/{i['id']}/access-response", {"negotiation_id": n["id"],
                "unit": n["required"][0], "role": "resident", "answer": answer})
        return n["required"][0]

    request("/session", {})
    request("/scenario", {})
    snapshot("Two original reports")
    agent()
    _, i = snapshot("AI connected the shared fault and proposed a fixed quote")
    assert len(i["reporters"]) == 2 and i["proposal"]["quote"] == 1800
    old_proposal = i["proposal"]["id"]
    request("/availability", {"unit": "A-502", "slots": ["evening"]})
    state, i = snapshot("The shared window disappeared")
    original_availability = state["availability"]
    assert i["proposal"]["window"] is None
    try:
        request(f"/incidents/{i['id']}/action", {"action": "approve", "role": "committee",
                "proposal_id": old_proposal})
    except urllib.error.HTTPError as error:
        assert error.code == 409
        proof["stale_approval_rejected"] = True
    else:
        raise AssertionError("Stale proposal approval succeeded")
    agent()
    _, i = snapshot("AI requested a one-time access exception")
    declined = consent(i, "declined")
    snapshot("A resident said no")
    agent()
    _, i = snapshot("AI found an alternative involving a different household")
    assert declined not in i["negotiation"]["required"]
    consent(i, "accepted")
    state, i = snapshot("One-visit consent granted without editing the calendar")
    assert state["availability"] == original_availability
    action(i, "approve", "committee")
    _, i = snapshot("Committee authorized the exact proposal")
    old_date = i["proposal"]["visit_date"]
    action(i, "delay", "vendor", note="Synthetic missed visit: technician cannot reach Tower A today.")
    agent()
    _, i = snapshot("Sentinel surfaced the missed-visit decision")
    assert i["status"] == "needs_attention"
    action(i, "replan", "committee")
    _, i = snapshot("A new date invalidated the previous one-time agreement")
    assert i["proposal"]["visit_date"] > old_date and not i["proposal"]["window"]
    assert not i["proposal"]["approved"]
    agent()
    _, i = snapshot("AI requested fresh consent for the revised date")
    consent(i, "accepted")
    _, i = snapshot("Fresh consent recorded")
    action(i, "approve", "committee")
    action(i, "complete", "vendor", note="Synthetic repair: common pump restarted and pressure checked. Residents must verify supply.")
    _, i = snapshot("Vendor completion left the repair open")
    assert i["status"] == "verifying"
    action(i, "confirm", "resident", unit=i["reporters"][0])
    _, i = snapshot("One household confirmed; the repair remained open")
    assert i["status"] == "verifying" and len(i["confirmed"]) == 1
    action(i, "confirm", "resident", unit=i["reporters"][1])
    state, i = snapshot("Both households confirmed; the repair closed")
    assert i["status"] == "resolved" and i["proposal"]["quote"] == 1800
    assert state["availability"] == original_availability
    proof["passed"] = True
    Path(args.output).write_text(json.dumps(proof, indent=2))
    print("PASS: real AWS refusal, fresh consent, delay recovery and two-household closure", flush=True)


if __name__ == "__main__":
    main()
