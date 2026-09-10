"""Injected provider faults and racing human actions; no cloud credentials or inference."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from strands.models.model import Model

from relay import agent, aws_jobs, domain
from relay.negotiation import request_window, respond
from relay.store import Store


class FaultAfterTool(Model):
    def __init__(self, incident_id):
        self.incident_id = incident_id
        self.config = {"params": {}}
        self.calls = 0

    def update_config(self, **config):
        self.config.update(config)

    def get_config(self):
        return self.config

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError
        yield  # pragma: no cover -- async generator contract

    async def stream(self, *args, **kwargs):
        self.calls += 1
        if self.calls > 2:
            raise TimeoutError("PRIVATE_PROVIDER_DIAGNOSTIC_SHOULD_NOT_BE_PUBLISHED")
        name = "inspect_workspace" if self.calls == 1 else "request_access_window"
        arguments = {} if self.calls == 1 else {
            "incident_id": self.incident_id, "slot_id": "afternoon", "rationale": "Injected test request."
        }
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {"toolUse": {"name": name, "toolUseId": f"fault-{self.calls}"}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}


def repair():
    state = domain.new_workspace()
    a = domain.report(state, "The shared pump is down.", "A-304", "Tower A", "water")
    b = domain.report(state, "The common water supply has stopped.", "A-502", "Tower A", "water")
    domain.merge(state, b["id"], a["id"])
    state["availability"]["A-502"] = ["evening"]
    domain.propose(state, a["id"], "waterworks", "Synthetic setup.")
    return state, a


def test_provider_failure_after_committed_tool_is_visible_and_redacted(tmp_path, monkeypatch):
    state, incident = repair()
    store = Store(tmp_path / "fault.db")
    store.create("fault", state)
    model = FaultAfterTool(incident["id"])
    monkeypatch.setattr(agent, "gateway_model", lambda: model)
    result = agent.run_agent(store, "fault", [incident["id"]], mode="gateway")
    saved = domain.incident_of(store.read("fault")[1], incident["id"])
    assert saved["negotiation"]["status"] == "waiting"
    assert len([e for e in store.read("fault")[1]["events"] if e["title"] == "A one-time access request"]) == 1
    assert not saved["proposal"]["approved"]
    assert result["status"] == "failed"
    assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in json.dumps(result)
    assert not aws_jobs.dispatch(store, "fault", automatic=True)["started"]
    first = saved["negotiation"]
    store.mutate("fault", lambda s: respond(s, incident["id"], first["id"], "A-502", "declined", "resident"))
    retry = agent.run_agent(store, "fault", [incident["id"]], mode="fixture")
    recovered = domain.incident_of(store.read("fault")[1], incident["id"])
    assert retry["status"] == "completed" and retry["provider"] == "fixture"
    assert recovered["negotiation"]["id"] != first["id"]
    assert recovered["negotiation"]["required"] == ["A-304"]
    assert recovered["proposal"]["quote"] == 1800


def test_racing_accept_and_decline_cannot_create_a_mixed_agreement(tmp_path):
    state, incident = repair()
    negotiation = request_window(state, incident["id"], "afternoon", "One synthetic exception.")
    store = Store(tmp_path / "race.db")
    store.create("race", state)
    barrier = Barrier(2)

    def answer(value):
        barrier.wait()
        try:
            store.mutate("race", lambda s: respond(s, incident["id"], negotiation["id"], "A-502", value, "resident"))
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(answer, ["accepted", "declined"])) == 1
    saved = domain.incident_of(store.read("race")[1], incident["id"])
    assert len(saved["negotiation"]["answers"]) == 1
    assert not saved["proposal"]["approved"]
    assert (saved["proposal"]["window"] is not None) == (saved["negotiation"]["status"] == "agreed")


def test_racing_confirmations_close_once_without_losing_a_household(tmp_path):
    state, incident = repair()
    n = request_window(state, incident["id"], "evening", "One visit.")
    respond(state, incident["id"], n["id"], "A-304", "accepted", "resident")
    domain.act(state, incident["id"], "approve", "committee", proposal_id=incident["proposal"]["id"])
    domain.act(state, incident["id"], "complete", "vendor", note="Synthetic pump repair completed for testing.")
    store = Store(tmp_path / "confirm.db")
    store.create("confirm", state)
    barrier = Barrier(2)

    def confirm(unit):
        barrier.wait()
        store.mutate("confirm", lambda s: domain.act(s, incident["id"], "confirm", "resident", unit=unit))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(confirm, ["A-304", "A-502"]))
    final = store.read("confirm")[1]
    saved = domain.incident_of(final, incident["id"])
    assert saved["status"] == "resolved" and sorted(saved["confirmed"]) == ["A-304", "A-502"]
    assert len([e for e in final["events"] if e["title"] == "Resolved, with confirmation"]) == 1


def test_stale_consent_cannot_be_reused_after_a_new_planning_round():
    state, incident = repair()
    old = request_window(state, incident["id"], "evening", "Old visit.")
    respond(state, incident["id"], old["id"], "A-304", "accepted", "resident")
    domain.act(state, incident["id"], "approve", "committee", proposal_id=incident["proposal"]["id"])
    domain.act(state, incident["id"], "delay", "vendor")
    domain.follow_up(state, incident["id"])
    domain.act(state, incident["id"], "replan", "committee")
    request_window(state, incident["id"], "evening", "New visit.")
    with pytest.raises(ValueError, match="changed"):
        respond(state, incident["id"], old["id"], "A-304", "accepted", "resident")
    assert incident["proposal"]["window"] is None
    assert not incident["proposal"]["approved"]
