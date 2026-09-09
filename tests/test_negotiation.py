import copy

import pytest

from relay import domain as d
from relay.coordination import windows
from relay.negotiation import alternatives, needs_negotiation, request_window, respond


def case():
    state = d.new_workspace()
    a = d.report(state, "Common water supply stopped.", "A-304", "Tower A", "water")
    b = d.report(state, "Shared taps have no water.", "A-502", "Tower A", "water")
    d.merge(state, b["id"], a["id"])
    state["availability"]["A-502"] = ["evening"]
    d.propose(state, a["id"], "waterworks", "A shared visit is needed.")
    return state, a


def test_exception_requires_consent_and_does_not_edit_general_availability():
    state, i = case()
    before = copy.deepcopy(state["availability"])
    old_proposal = i["proposal"]["id"]
    n = request_window(state, i["id"], "afternoon", "Ask one household for an exception.")
    assert not needs_negotiation(state, i)  # Waiting is not an excuse to keep invoking models.
    with pytest.raises(ValueError):
        d.act(state, i["id"], "approve", "committee", proposal_id=i["proposal"]["id"])
    respond(state, i["id"], n["id"], "A-502", "accepted", "resident")
    assert state["availability"] == before
    assert i["proposal"]["window"]["id"] == "afternoon"
    assert i["proposal"]["quote"] == 1800
    assert i["proposal"]["approved"] is False
    with pytest.raises(ValueError, match="proposal changed"):
        d.act(state, i["id"], "approve", "committee", proposal_id=old_proposal)
    d.act(state, i["id"], "approve", "committee", proposal_id=i["proposal"]["id"])
    assert i["status"] == "scheduled"


def test_no_is_respected_and_recovery_asks_a_different_household():
    state, i = case()
    n = request_window(state, i["id"], "afternoon", "One exception.")
    respond(state, i["id"], n["id"], "A-502", "declined", "resident")
    assert needs_negotiation(state, i)
    assert [o["id"] for o in alternatives(state, i) if o["eligible"]] == ["evening"]
    for slot in ["morning", "afternoon", "midday"]:
        with pytest.raises(ValueError, match="eligible"):
            request_window(state, i["id"], slot, "Try again.")
    next_request = request_window(state, i["id"], "evening", "Ask A-304 instead.")
    assert next_request["required"] == ["A-304"]
    respond(state, i["id"], next_request["id"], "A-304", "accepted", "resident")
    assert i["proposal"]["window"]["id"] == "evening"
    assert any(e["title"] == "Resident declined the exception" for e in state["events"])


def test_exhaustion_stops_agent_work_without_overriding_anyone():
    state, i = case()
    for slot, unit in [("afternoon", "A-502"), ("evening", "A-304")]:
        n = request_window(state, i["id"], slot, "One exception.")
        respond(state, i["id"], n["id"], unit, "declined", "resident")
    n = request_window(state, i["id"], "none", "No eligible alternatives remain.")
    assert n["status"] == "exhausted"
    assert not needs_negotiation(state, i)
    assert not any(w["feasible"] for w in windows(state, i))


@pytest.mark.parametrize("change", ["availability", "date", "vendor_slots", "quote"])
def test_changed_context_invalidates_pending_or_accepted_consent(change):
    state, i = case()
    n = request_window(state, i["id"], "afternoon", "One exception.")
    accepted = copy.deepcopy(state)
    ai = d.incident_of(accepted, i["id"])
    respond(accepted, i["id"], n["id"], "A-502", "accepted", "resident")
    for s, incident in [(state, i), (accepted, ai)]:
        if change == "availability":
            s["availability"]["A-304"] = ["afternoon"]
        elif change == "date":
            incident["proposal"]["visit_date"] = "2030-01-01"
        elif change == "vendor_slots":
            s["vendor_slots"] = ["morning", "afternoon"]
        else:
            incident["proposal"]["quote"] += 1
    with pytest.raises(ValueError, match="changed"):
        respond(state, i["id"], n["id"], "A-502", "accepted", "resident")
    assert not any(w["feasible"] for w in windows(accepted, ai))
    with pytest.raises(ValueError):
        d.act(accepted, i["id"], "approve", "committee", proposal_id=ai["proposal"]["id"])


def test_wrong_role_household_and_duplicate_answer_are_rejected():
    state, i = case()
    n = request_window(state, i["id"], "afternoon", "One exception.")
    for unit, role in [("A-502", "committee"), ("A-304", "resident"), ("X-999", "resident")]:
        with pytest.raises(ValueError):
            respond(state, i["id"], n["id"], unit, "accepted", role)
    respond(state, i["id"], n["id"], "A-502", "accepted", "resident")
    with pytest.raises(ValueError):
        respond(state, i["id"], n["id"], "A-502", "accepted", "resident")


def test_one_visit_consent_cannot_authorize_a_revised_visit():
    state, i = case()
    n = request_window(state, i["id"], "afternoon", "One exception.")
    respond(state, i["id"], n["id"], "A-502", "accepted", "resident")
    d.act(state, i["id"], "approve", "committee", proposal_id=i["proposal"]["id"])
    d.act(state, i["id"], "delay", "vendor")
    d.follow_up(state, i["id"])
    with pytest.raises(ValueError, match="No shared window"):
        d.act(state, i["id"], "reschedule", "committee")


def test_withdrawing_consent_invalidates_even_the_prepared_approval():
    state, i = case()
    n = request_window(state, i["id"], "afternoon", "One exception.")
    respond(state, i["id"], n["id"], "A-502", "accepted", "resident")
    accepted_proposal = i["proposal"]["id"]
    respond(state, i["id"], n["id"], "A-502", "withdrawn", "resident")
    assert i["proposal"]["window"] is None
    with pytest.raises(ValueError):
        d.act(state, i["id"], "approve", "committee", proposal_id=accepted_proposal)
    assert state["availability"]["A-502"] == ["evening"]


def test_repair_followup_opens_fresh_consent_for_a_new_date_at_same_quote():
    state, i = case()
    n = request_window(state, i["id"], "afternoon", "One exception.")
    respond(state, i["id"], n["id"], "A-502", "accepted", "resident")
    old_date, old_request = i["proposal"]["visit_date"], n["id"]
    d.act(state, i["id"], "approve", "committee", proposal_id=i["proposal"]["id"])
    d.act(state, i["id"], "delay", "vendor")
    d.follow_up(state, i["id"])
    d.act(state, i["id"], "replan", "committee")
    assert i["proposal"]["visit_date"] > old_date
    assert i["proposal"]["quote"] == 1800
    assert i["proposal"]["window"] is None
    assert needs_negotiation(state, i)
    with pytest.raises(ValueError):
        respond(state, i["id"], old_request, "A-502", "accepted", "resident")
    new = request_window(state, i["id"], "evening", "New date, fresh consent.")
    respond(state, i["id"], new["id"], "A-304", "accepted", "resident")
    assert i["status"] == "awaiting_approval"
    assert not i["proposal"]["approved"]
