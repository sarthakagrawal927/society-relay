from concurrent.futures import ThreadPoolExecutor

import pytest

from relay import domain as d
from relay.store import Store


@pytest.fixture
def state():
    s = d.new_workspace()
    d.report(s, "The shared water supply has stopped.", "A-304", "Tower A", "water")
    return s


def prepare(s):
    i = s["incidents"][0]
    d.propose(s, i["id"], "waterworks", "Approved water contractor.")
    return i


def approve(s, i):
    return d.act(s, i["id"], "approve", "committee", proposal_id=i["proposal"]["id"])


def test_vendor_completion_requires_every_reporting_household(state):
    i = state["incidents"][0]
    other = d.report(state, "No water in our apartment from the shared supply.", "A-502", "Tower A", "water")
    d.merge(state, other["id"], i["id"])
    prepare(state)
    approve(state, i)
    d.act(state, i["id"], "complete", "vendor", note="Reset the common pump and checked supply.")
    assert i["status"] == "verifying"
    d.act(state, i["id"], "confirm", "resident", unit="A-304")
    assert i["status"] == "verifying"
    d.act(state, i["id"], "confirm", "resident", unit="A-502")
    assert i["status"] == "resolved"


@pytest.mark.parametrize("role", ["resident", "vendor", "Relay"])
def test_agent_and_noncommittee_cannot_approve(state, role):
    i = prepare(state)
    with pytest.raises(ValueError, match="Only the committee"):
        d.act(state, i["id"], "approve", role, proposal_id=i["proposal"]["id"])
    assert i["status"] == "awaiting_approval"


def test_stale_approval_is_rejected(state):
    i = prepare(state)
    with pytest.raises(ValueError, match="proposal changed"):
        d.act(state, i["id"], "approve", "committee", proposal_id="old")


def test_unapproved_work_cannot_complete(state):
    i = prepare(state)
    with pytest.raises(ValueError):
        d.act(state, i["id"], "complete", "vendor", note="I say the repair is finished.")


def test_private_reports_never_merge(state):
    p = d.report(state, "No water in my private kitchen tap.", "A-502", "Tower A", "water", "private")
    with pytest.raises(ValueError, match="Private"):
        d.merge(state, p["id"], state["incidents"][0]["id"])


def test_reports_in_different_towers_never_merge(state):
    p = d.report(state, "Shared supply is unavailable.", "B-502", "Tower B", "water")
    with pytest.raises(ValueError, match="same category"):
        d.merge(state, p["id"], state["incidents"][0]["id"])


def test_delay_becomes_decision_without_increasing_spend(state):
    i = prepare(state)
    approve(state, i)
    quote = i["proposal"]["quote"]
    d.act(state, i["id"], "delay", "vendor", note="Technician is delayed.")
    d.follow_up(state, i["id"])
    assert i["status"] == "needs_attention"
    assert i["proposal"]["quote"] == quote
    d.act(state, i["id"], "reschedule", "committee")
    assert i["status"] == "scheduled"


def test_follow_up_cannot_run_before_due(state):
    i = prepare(state)
    approve(state, i)
    with pytest.raises(ValueError, match="not due"):
        d.follow_up(state, i["id"])


def test_false_completion_can_be_challenged(state):
    i = prepare(state)
    approve(state, i)
    d.act(state, i["id"], "complete", "vendor", note="The pump was reset and seems operational.")
    d.act(state, i["id"], "reopen", "resident", unit="A-304")
    assert i["status"] == "needs_attention"


def test_hazard_without_authorization_cannot_be_rescheduled(state):
    i = state["incidents"][0]
    i["status"] = "needs_attention"
    with pytest.raises(ValueError, match="previously authorized"):
        d.act(state, i["id"], "reschedule", "committee")


def test_rescheduling_respects_changed_household_availability(state):
    i = prepare(state)
    approve(state, i)
    d.act(state, i["id"], "delay", "vendor")
    d.follow_up(state, i["id"])
    state["availability"]["A-304"] = []
    with pytest.raises(ValueError, match="No shared window"):
        d.act(state, i["id"], "reschedule", "committee")
    assert i["status"] == "needs_attention"


def test_new_household_invalidates_old_proposal(state):
    i = prepare(state)
    original = i["proposal"]["id"]
    other = d.report(state, "Common water pump has stopped.", "A-502", "Tower A", "water")
    d.merge(state, other["id"], i["id"])
    assert i["proposal"]["window"]["id"] == "afternoon"
    with pytest.raises(ValueError, match="proposal changed"):
        d.act(state, i["id"], "approve", "committee", proposal_id=original)


def test_human_separation_withdraws_proposal_and_prevents_remerge(state):
    i = state["incidents"][0]
    other = d.report(state, "A separate irrigation tap is dripping.", "A-502", "Tower A", "water")
    d.merge(state, other["id"], i["id"])
    prepare(state)
    d.act(state, other["id"], "separate", "committee")
    assert i["proposal"] is None
    assert i["reporters"] == ["A-304"]
    assert other["status"] == "reported"
    with pytest.raises(ValueError, match="marked these reports as separate"):
        d.merge(state, i["id"], other["id"])


def test_unrelated_resident_cannot_verify(state):
    i = prepare(state)
    approve(state, i)
    d.act(state, i["id"], "complete", "vendor", note="The pump was reset and seems operational.")
    with pytest.raises(ValueError, match="reporting household"):
        d.act(state, i["id"], "confirm", "resident", unit="B-999")


def test_storage_isolation_and_restart(tmp_path, state):
    path = tmp_path / "relay.db"
    store = Store(path)
    store.create("a", state)
    store.create("b", d.new_workspace())
    recovered = Store(path)
    assert len(recovered.read("a")[1]["incidents"]) == 1
    assert recovered.read("b")[1]["incidents"] == []
    with pytest.raises(ValueError, match="not found"):
        recovered.mutate("b", lambda s: d.propose(s, state["incidents"][0]["id"], "waterworks", "No"))


def test_concurrent_approvals_create_one_work_order(tmp_path, state):
    i = prepare(state)
    store = Store(tmp_path / "relay.db")
    store.create("a", state)

    def attempt(_):
        try:
            store.mutate(
                "a", lambda s: d.act(s, i["id"], "approve", "committee", proposal_id=i["proposal"]["id"])
            )
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt, range(2))) == 1
    saved = store.read("a")[1]
    assert len([e for e in saved["events"] if e["title"] == "Work authorized"]) == 1
