import time
from types import SimpleNamespace

import pytest

from relay import aws_jobs, domain
from relay.store import Store


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path / "jobs.db")
    result.create(aws_jobs.REGISTRY, {"workspaces": [], "usage": {}, "runs": 0, "lease": None})
    result.create("test", domain.new_workspace())
    result.mutate(
        "test", lambda data: domain.report(data, "No water from the common pump", "A-304", "Tower A", "water")
    )
    return result


def test_atomic_job_claim_duplicate_delivery_and_release(store, monkeypatch):
    sent = []
    monkeypatch.setenv("RELAY_DISPATCH_FUNCTION", "test-dispatch")
    monkeypatch.setattr(
        aws_jobs.boto3, "client", lambda _: SimpleNamespace(invoke=lambda **kw: sent.append(kw))
    )
    assert aws_jobs.dispatch(store, "test")["started"]
    assert aws_jobs.running(store, "test")
    with pytest.raises(ValueError, match="busy"):
        aws_jobs.dispatch(store, "test")
    job = store.read(aws_jobs.REGISTRY)[1]["lease"]["job"]
    assert aws_jobs.claim_execution(store, job)
    assert not aws_jobs.claim_execution(store, job)
    aws_jobs.release(store, "wrong-owner")
    assert aws_jobs.running(store, "test")
    aws_jobs.release(store, job)
    assert not aws_jobs.running(store, "test")
    assert len(sent) == 1


def test_failed_enqueue_releases_lease_but_does_not_refund_limit(store, monkeypatch):
    monkeypatch.setenv("RELAY_DISPATCH_FUNCTION", "test-dispatch")

    def fail(**kw):
        raise RuntimeError("network failure")

    monkeypatch.setattr(aws_jobs.boto3, "client", lambda _: SimpleNamespace(invoke=fail))
    with pytest.raises(RuntimeError):
        aws_jobs.dispatch(store, "test")
    assert not aws_jobs.running(store, "test")
    assert store.read(aws_jobs.REGISTRY)[1]["runs"] == 1


def test_scheduler_does_not_retry_failed_provider(store):
    store.mutate("test", lambda data: data["runs"].append({"error": "provider failure"}))
    assert not aws_jobs.dispatch(store, "test", automatic=True)["started"]


def test_expired_job_cannot_start(store):
    store.mutate(
        aws_jobs.REGISTRY, lambda data: data.update(lease={"job": "old", "expires": time.time() - 1})
    )
    assert not aws_jobs.claim_execution(store, "old")


def test_usage_limit_survives_new_store_instance(store, monkeypatch):
    monkeypatch.setattr(aws_jobs, "Store", lambda: Store(store.path))
    aws_jobs.take_persistent("model", 1)
    with pytest.raises(ValueError, match="usage limit"):
        aws_jobs.take_persistent("model", 1)
