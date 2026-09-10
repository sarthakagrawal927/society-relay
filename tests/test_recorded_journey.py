"""Keep the published replay consistent with its observed acceptance evidence."""

import json
from pathlib import Path


def test_public_replay_matches_real_aws_evidence_and_its_claims():
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / "docs/difficult-repair-evidence.json").read_text())
    public = json.loads((root / "relay/static/repair-proof.json").read_text())
    assert public == evidence
    assert public["passed"] and public["stale_approval_rejected"]
    assert len(public["checkpoints"]) == 15
    assert len(public["runs"]) == 5
    assert all(r["provider"] == "bedrock" and r["model"] == "amazon.nova-pro-v1:0"
               and not r["error"] for r in public["runs"])
    checkpoints = public["checkpoints"]
    declined = checkpoints[4]["incident"]["negotiation"]["declined_units"]
    alternative = checkpoints[5]["incident"]["negotiation"]["required"]
    assert declined and alternative and set(declined).isdisjoint(alternative)
    assert checkpoints[9]["incident"]["proposal"]["window"] is None
    assert not checkpoints[9]["incident"]["proposal"]["approved"]
    assert checkpoints[9]["incident"]["proposal"]["visit_date"] > checkpoints[7]["incident"]["proposal"]["visit_date"]
    assert checkpoints[-2]["incident"]["status"] == "verifying"
    assert len(checkpoints[-2]["incident"]["confirmed"]) == 1
    assert checkpoints[-1]["incident"]["status"] == "resolved"
    assert len(checkpoints[-1]["incident"]["confirmed"]) == 2
    assert all(c["incident"]["proposal"]["quote"] == 1800 for c in checkpoints[1:])
    assert all(c["availability"] == checkpoints[2]["availability"] for c in checkpoints[2:])
