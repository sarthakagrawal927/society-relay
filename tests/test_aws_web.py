import json
from types import SimpleNamespace

from relay import app as module
from relay import aws_jobs
from relay.aws_web import handler
from relay.store import Store


def test_lambda_url_session_scenario_and_async_dispatch(tmp_path, monkeypatch):
    store = Store(tmp_path / "lambda.db")
    store.create(aws_jobs.REGISTRY, {"workspaces": [], "usage": {}, "runs": 0, "lease": None})
    monkeypatch.setattr(module, "store", store)
    monkeypatch.setattr(aws_jobs, "Store", lambda: Store(store.path))
    monkeypatch.setenv("RELAY_AWS", "1")
    monkeypatch.setenv("RELAY_PUBLIC_DEMO", "1")
    monkeypatch.setenv("RELAY_DISPATCH_FUNCTION", "test-dispatch")
    sent = []
    monkeypatch.setattr(
        aws_jobs.boto3, "client", lambda _: SimpleNamespace(invoke=lambda **kw: sent.append(kw))
    )

    def request(path, method="GET", cookies=None):
        return handler(
            {
                "version": "2.0",
                "rawPath": path,
                "rawQueryString": "",
                "headers": {"host": "demo.lambda-url.us-east-1.on.aws", "x-forwarded-proto": "https"},
                "requestContext": {"http": {"method": method, "path": path, "sourceIp": "127.0.0.1"}},
                "cookies": cookies or [],
                "isBase64Encoded": False,
            },
            SimpleNamespace(),
        )

    assert request("/api/state")["statusCode"] == 401
    session = request("/api/session", "POST")
    assert session["statusCode"] == 200
    assert "Secure" in session["cookies"][0]
    cookies = [session["cookies"][0].split(";")[0]]
    assert request("/api/scenario", "POST", cookies)["statusCode"] == 200
    assert json.loads(request("/api/agent", "POST", cookies)["body"])["started"]
    assert len(sent) == 1
    state = json.loads(request("/api/state", cookies=cookies)["body"])
    assert state["running"] and len(state["incidents"]) == 2
    assert not module.workers
    assert request("/static/app.js")["statusCode"] == 200
