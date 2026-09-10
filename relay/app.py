"""Public synthetic demo; role switching is simulation, never production authentication."""

import asyncio
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import domain
from .limits import take
from .store import Conflict, Store

store = Store()
active = set()
workers = set()


@asynccontextmanager
async def lifespan(app):
    scheduler = asyncio.create_task(schedule_due()) if not os.getenv("RELAY_AWS") else None
    yield
    if scheduler:
        scheduler.cancel()
    for task in workers:
        task.cancel()


app = FastAPI(title="Society Relay", lifespan=lifespan)
static = Path(__file__).parent / "static"


@app.middleware("http")
async def guards(request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return Response("Cross-origin mutation rejected", status_code=403)
        if int(request.headers.get("content-length", "0")) > 16000:
            return Response("Request too large", status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


def workspace(request):
    token = request.cookies.get("relay_workspace", "")
    if not re.fullmatch(r"[a-f0-9]{48}", token):
        raise HTTPException(401, "Start your demo workspace first.")
    try:
        store.read(token)
    except KeyError:
        raise HTTPException(401, "Demo workspace not found.")
    return token


@app.exception_handler(ValueError)
async def invalid(request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(Conflict)
async def conflict(request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        {"detail": "Another action changed this incident. Refresh and retry."}, status_code=409
    )


@app.get("/")
def index():
    return FileResponse(static / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "product": "Society Relay", "mode": "synthetic demo"}


@app.post("/api/session")
def session(request: Request, response: Response):
    try:
        token = workspace(request)
    except HTTPException:
        take("new_workspaces", 100)
        token = secrets.token_hex(24)
        store.create(token, domain.new_workspace())
        if os.getenv("RELAY_AWS"):
            from .aws_jobs import register

            register(store, token)
    response.set_cookie(
        "relay_workspace",
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=86400 * 7,
    )
    return {"ready": True}


@app.get("/api/state")
def state(request: Request):
    token = workspace(request)
    result = store.read(token)[1]
    if os.getenv("RELAY_AWS"):
        from .aws_jobs import running

        result["running"] = running(store, token)
    else:
        result["running"] = token in active
    result["provider"] = os.getenv("RELAY_MODEL_PROVIDER", "ollama")
    result["public_demo"] = os.getenv("RELAY_PUBLIC_DEMO") == "1"
    result["durable_host"] = bool(os.getenv("RELAY_AWS"))
    return result


@app.post("/api/session/new")
def new_session(request: Request, response: Response):
    take("new_workspaces", 100)
    token = secrets.token_hex(24)
    store.create(token, domain.new_workspace())
    if os.getenv("RELAY_AWS"):
        from .aws_jobs import register

        register(store, token)
    response.set_cookie(
        "relay_workspace",
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=86400 * 7,
    )
    return {"ready": True}


class Report(BaseModel):
    text: str = Field(min_length=12, max_length=1200)
    unit: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9 -]+$")
    area: Literal["Tower A", "Tower B", "Clubhouse", "My apartment"] = "Tower A"
    category: Literal["water", "electricity", "general"] = "water"
    scope: Literal["shared", "private"] = "shared"
    request_id: str = Field(min_length=8, max_length=80)


@app.post("/api/reports")
def add_report(body: Report, request: Request):
    token = workspace(request)

    def change(state):
        if body.request_id in state["receipts"]:
            return domain.incident_of(state, state["receipts"][body.request_id])
        result = domain.report(state, body.text, body.unit, body.area, body.category, body.scope)
        state["receipts"][body.request_id] = result["id"]
        return result

    return store.mutate(token, change)


@app.post("/api/scenario")
def scenario(request: Request):
    token = workspace(request)

    def change(state):
        if state["incidents"]:
            raise ValueError("The example can only be loaded into an empty workspace.")
        for unit, text in [
            (
                "A-304",
                "No water from the taps in Tower A since this morning. The shared supply appears to be down.",
            ),
            (
                "A-502",
                "Tower A has no water supply on the fifth floor either. Please check the common water pump.",
            ),
        ]:
            domain.report(state, text, unit, "Tower A", "water")
        return {"loaded": True}

    return store.mutate(token, change)


class Action(BaseModel):
    action: Literal["approve", "delay", "reschedule", "replan", "complete", "confirm", "reopen", "separate"]
    role: Literal["resident", "committee", "vendor"]
    note: str = Field(default="", max_length=1000)
    unit: str = Field(default="A-304", max_length=20)
    proposal_id: str | None = None


@app.post("/api/incidents/{incident_id}/action")
def action(incident_id: str, body: Action, request: Request):
    return store.mutate(workspace(request), lambda s: domain.act(s, incident_id, **body.model_dump()))


class Availability(BaseModel):
    unit: str = Field(min_length=2, max_length=20)
    slots: list[Literal["morning", "midday", "afternoon", "evening"]] = Field(max_length=4)


class AccessResponse(BaseModel):
    negotiation_id: str = Field(max_length=80)
    unit: str = Field(min_length=2, max_length=20)
    answer: Literal["accepted", "declined", "withdrawn"]
    role: Literal["resident", "committee", "vendor"]


@app.post("/api/incidents/{incident_id}/access-response")
def access_response(incident_id: str, body: AccessResponse, request: Request):
    from .negotiation import respond

    return store.mutate(workspace(request), lambda s: respond(s, incident_id, **body.model_dump()))


@app.post("/api/availability")
def availability(body: Availability, request: Request):
    from .coordination import windows

    def change(state):
        state.setdefault("availability", {})[body.unit] = body.slots
        for incident in state["incidents"]:
            if body.unit in incident["reporters"] and incident["status"] == "awaiting_approval":
                incident["negotiation"] = None
                proposal = incident["proposal"]
                proposal["id"] = domain.uid("proposal")
                proposal["options"] = windows(state, incident)
                proposal["window"] = next((w for w in proposal["options"] if w["feasible"]), None)
                proposal["rationale"] = (
                    f"Availability changed. The revised shared window is {proposal['window']['label']}. The fixed quote is unchanged."
                    if proposal["window"]
                    else "Availability changed. No visit currently works for every reporting household. The quote is unchanged, but approval is blocked."
                )
                domain.event(
                    state,
                    incident,
                    "Visit replanned",
                    "Availability changed. The committee must review the current access window.",
                )
            elif body.unit in incident["reporters"] and incident["status"] in {"scheduled", "delayed"}:
                proposal = incident["proposal"]
                if not any(
                    w["id"] == proposal["window"]["id"] and w["feasible"] for w in windows(state, incident)
                ):
                    incident["status"] = "needs_attention"
                    incident["next_check"] = None
                    domain.event(
                        state,
                        incident,
                        "Authorized visit needs a new access decision",
                        "Availability changed. The old access agreement cannot be reused; the fixed quote remains unchanged.",
                    )
        return {"updated": True}

    return store.mutate(workspace(request), change)


@app.get("/api/incidents/{incident_id}/calendar")
def calendar(incident_id: str, request: Request):
    from .coordination import calendar_event

    incident = domain.incident_of(store.read(workspace(request))[1], incident_id)
    return Response(
        calendar_event(incident),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{incident_id}.ics"'},
    )


@app.get("/api/incidents/{incident_id}/work-order")
def work_order(incident_id: str, request: Request):
    incident = domain.incident_of(store.read(workspace(request))[1], incident_id)
    if not incident["proposal"] or not incident["proposal"]["approved"]:
        raise ValueError("Approve a quote before exporting its work order.")
    p = incident["proposal"]
    lines = [
        "SOCIETY RELAY — DEMONSTRATION WORK ORDER",
        "Synthetic data. No real booking or payment.",
        f"Reference: {incident['id']}",
        f"Location: {incident['area']}",
        f"Issue: {incident['description']}",
        f"Vendor: {p['vendor']}",
        f"Fixed quote: INR {p['quote']}",
        f"Visit: {p.get('visit_date', '')} {p.get('window', {}).get('label', '')} Asia/Kolkata",
        "Closure: every reporting household must confirm restoration.",
    ]
    return Response(
        "\n".join(lines),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{incident_id}-work-order.txt"'},
    )


async def execute(token, ids):
    try:
        from .agent import run_agent

        await asyncio.to_thread(run_agent, store, token, ids)
    finally:
        active.discard(token)


async def schedule_due():
    """Resume due work from persistent state, including after application restart."""
    while True:
        await asyncio.sleep(15)
        if os.getenv("RELAY_AUTO", "1") != "1":
            continue
        for token in store.workspace_ids():
            if token in active or len(active) >= 1:
                continue
            state = store.read(token)[1]
            # A provider failure must not create an automatic retry/spending storm.
            if state["runs"] and state["runs"][-1]["error"]:
                continue
            from .negotiation import needs_negotiation

            ids = [
                i["id"]
                for i in state["incidents"]
                if i["status"] in {"reported", "delayed"}
                or needs_negotiation(state, i)
                or (i["status"] == "scheduled" and i["next_check"] and i["next_check"] <= domain.now())
            ]
            if ids:
                active.add(token)
                task = asyncio.create_task(execute(token, ids))
                workers.add(task)
                task.add_done_callback(workers.discard)


@app.post("/api/agent")
async def agent(request: Request):
    token = workspace(request)
    if os.getenv("RELAY_AWS"):
        from .aws_jobs import dispatch

        return dispatch(store, token)
    if token in active:
        return {"started": False, "message": "Relay is already working on this workspace."}
    data = store.read(token)[1]
    from .negotiation import needs_negotiation

    ids = [
        i["id"]
        for i in data["incidents"]
        if i["status"] in {"reported", "delayed"}
        or needs_negotiation(data, i)
        or (i["status"] == "scheduled" and i["next_check"] and i["next_check"] <= domain.now())
    ]
    if not ids:
        return {"started": False, "message": "No agent work is due. Waiting for a human action."}
    if len(active) >= 1:
        raise HTTPException(429, "The demo agent is busy. Please try again shortly.")
    active.add(token)
    task = asyncio.create_task(execute(token, ids))
    workers.add(task)
    task.add_done_callback(workers.discard)
    return {"started": True}


app.mount("/static", StaticFiles(directory=static), name="static")
