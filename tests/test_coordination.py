import pytest

from relay import domain as d
from relay.coordination import calendar_event, windows


def shared_case():
    state = d.new_workspace()
    a = d.report(state, "Shared water supply is unavailable.", "A-304", "Tower A", "water")
    b = d.report(state, "The common water supply is down here too.", "A-502", "Tower A", "water")
    d.merge(state, b["id"], a["id"])
    return state, a


def test_coordination_finds_common_window_without_overriding_quiet_hours():
    state, incident = shared_case()
    options = windows(state, incident)
    assert options[0]["id"] == "afternoon"
    assert options[0]["feasible"]
    assert all(o["id"] != "midday" for o in options)


def test_no_shared_window_blocks_approval():
    state, incident = shared_case()
    state["availability"]["A-502"] = ["evening"]
    d.propose(state, incident["id"], "waterworks", "Inspection requires both households.")
    assert incident["proposal"]["window"] is None
    with pytest.raises(ValueError, match="no shared window"):
        d.act(state, incident["id"], "approve", "committee", proposal_id=incident["proposal"]["id"])


def test_availability_change_is_rechecked_at_commit_time():
    state, incident = shared_case()
    d.propose(state, incident["id"], "waterworks", "Shared visit.")
    proposal_id = incident["proposal"]["id"]
    state["availability"]["A-502"] = ["evening"]
    with pytest.raises(ValueError, match="availability changed"):
        d.act(state, incident["id"], "approve", "committee", proposal_id=proposal_id)


def test_calendar_is_anchored_to_approved_visit_and_cannot_be_injected():
    state, incident = shared_case()
    d.propose(state, incident["id"], "waterworks", "Shared visit.")
    with pytest.raises(ValueError, match="approved"):
        calendar_event(incident)
    d.act(state, incident["id"], "approve", "committee", proposal_id=incident["proposal"]["id"])
    incident["area"] = "Tower A\r\nATTENDEE:attacker@example.com"
    text = calendar_event(incident)
    assert "DTSTART;TZID=Asia/Kolkata:" in text
    assert "T150000" in text
    assert "\r\nATTENDEE:" not in text
    assert text == calendar_event(incident)


def test_visit_deadline_matches_local_end_time():
    from relay.coordination import visit_deadline

    assert visit_deadline({"visit_date": "2026-09-10", "window": {"hour": 15}}) == "2026-09-10T10:30:00+00:00"
