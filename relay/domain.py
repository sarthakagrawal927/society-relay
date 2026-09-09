"""Deterministic authority and lifecycle. Tools cannot bypass these rules."""

import uuid
from datetime import UTC, datetime


def now():
    return datetime.now(UTC).isoformat()


def uid(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def event(state, incident, title, detail, actor="Relay"):
    item = {
        "id": uid("evt"),
        "incident_id": incident["id"],
        "title": title,
        "detail": detail,
        "actor": actor,
        "at": now(),
    }
    state["events"].append(item)
    state["events"] = state["events"][-150:]
    incident["updated_at"] = item["at"]


def new_workspace():
    return {
        "society": "Gulmohar Heights",
        "demo": True,
        "incidents": [],
        "events": [],
        "receipts": {},
        "separate_pairs": [],
        "availability": {"A-304": ["morning", "afternoon"], "A-502": ["afternoon", "evening"]},
        "blocked_slots": ["midday"],
        "vendor_slots": ["morning", "afternoon", "evening"],
        "policy": {
            "approval_required": True,
            "currency": "INR",
            "max_quote": 5000,
            "closure": "All reporting households must confirm restoration.",
            "dispatch": "A committee member must approve a fixed quote before dispatch.",
            "emergency": "Hazards are escalated to a human; Relay does not diagnose or dispatch emergency services.",
        },
        "vendors": [
            {"id": "waterworks", "name": "ClearFlow Maintenance", "trade": "water", "quote": 1800},
            {"id": "electrical", "name": "Brightline Electrical", "trade": "electricity", "quote": 1200},
            {"id": "general", "name": "Neighbourhood Services", "trade": "general", "quote": 900},
        ],
        "runs": [],
    }


def incident_of(state, incident_id):
    for incident in state["incidents"]:
        if incident["id"] == incident_id:
            return incident
    raise ValueError("Incident not found in this workspace.")


def report(state, text, unit, area, category, scope="shared"):
    if len(state["incidents"]) >= 35:
        raise ValueError("Demo limit reached. Start a fresh workspace.")
    incident = {
        "id": uid("SR"),
        "title": text[:90],
        "description": text,
        "unit": unit,
        "area": area,
        "category": category,
        "scope": scope,
        "status": "reported",
        "reporters": [unit],
        "reports": [{"text": text, "unit": unit}],
        "confirmed": [],
        "created_at": now(),
        "updated_at": now(),
        "proposal": None,
        "vendor_note": "",
        "next_check": None,
        "merged_into": None,
    }
    state["incidents"].append(incident)
    event(state, incident, "Report received", f"{unit} reported an issue in {area}.", "Resident")
    return incident


def merge(state, source_id, target_id):
    source, target = incident_of(state, source_id), incident_of(state, target_id)
    if source_id == target_id:
        raise ValueError("An incident cannot be linked to itself.")
    if sorted([source_id, target_id]) in state.get("separate_pairs", []):
        raise ValueError("A human has marked these reports as separate problems.")
    if source["status"] != "reported" or target["status"] not in {"reported", "awaiting_approval"}:
        raise ValueError("Only open, undispatched reports can be linked.")
    if source["scope"] != "shared" or target["scope"] != "shared":
        raise ValueError("Private household reports cannot be merged.")
    if source["category"] != target["category"] or source["area"] != target["area"]:
        raise ValueError("Reports must concern the same category and shared area.")
    target["reporters"] = sorted(set(target["reporters"] + source["reporters"]))
    target["reports"] += source["reports"]
    target["negotiation"] = None
    source["status"], source["merged_into"] = "linked", target_id
    if target["proposal"]:
        from .coordination import windows

        target["proposal"]["id"] = uid("proposal")
        target["proposal"]["options"] = windows(state, target)
        target["proposal"]["window"] = next((w for w in target["proposal"]["options"] if w["feasible"]), None)
    event(
        state, target, "Related reports connected", f"{source['unit']}'s report is now part of this incident."
    )
    return target


def propose(state, incident_id, vendor_id, rationale):
    from .coordination import visit_date, windows

    incident = incident_of(state, incident_id)
    if incident["status"] != "reported":
        raise ValueError("This incident has already been assessed.")
    vendor = next((v for v in state["vendors"] if v["id"] == vendor_id), None)
    if not vendor or vendor["trade"] not in {incident["category"], "general"}:
        raise ValueError("Vendor must be approved for this category.")
    incident["proposal"] = {
        "id": uid("proposal"),
        "vendor": vendor["name"],
        "vendor_id": vendor_id,
        "quote": vendor["quote"],
        "rationale": rationale,
        "approved": False,
        "options": windows(state, incident),
        "window": next((w for w in windows(state, incident) if w["feasible"]), None),
        "visit_date": visit_date(),
    }
    incident["title"] = (
        {"water": "Water supply", "electricity": "Electrical maintenance", "general": "Maintenance"}[
            incident["category"]
        ]
        + " · "
        + incident["area"]
    )
    incident["status"] = "awaiting_approval"
    event(state, incident, "A decision is ready", f"{vendor['name']} · ₹{vendor['quote']}. {rationale}")
    return incident


def act(state, incident_id, action, role, note="", unit="A-304", proposal_id=None):
    incident = incident_of(state, incident_id)
    if action == "separate":
        if role != "committee" or incident["status"] != "linked":
            raise ValueError("Only the committee can separate a linked report.")
        target = incident_of(state, incident["merged_into"])
        if target["status"] not in {"reported", "awaiting_approval"}:
            raise ValueError("Review the authorized work before changing its scope.")
        for report_item in incident["reports"]:
            if report_item in target["reports"]:
                target["reports"].remove(report_item)
        target["reporters"] = sorted({r["unit"] for r in target["reports"]})
        state.setdefault("separate_pairs", []).append(sorted([incident["id"], target["id"]]))
        incident["status"], incident["merged_into"] = "reported", None
        target["status"], target["proposal"] = "reported", None
        target["negotiation"] = None
        event(
            state,
            target,
            "Reports separated by a human",
            "The previous proposal was withdrawn. Both problems need independent assessment.",
            "Committee",
        )
        event(
            state,
            incident,
            "Independent report restored",
            "Relay must not reconnect these reports automatically.",
            "Committee",
        )
    elif action == "approve":
        if role != "committee":
            raise ValueError("Only the committee can approve a quote.")
        proposal = incident["proposal"]
        if incident["status"] != "awaiting_approval" or not proposal or proposal_id != proposal["id"]:
            raise ValueError("The proposal changed. Review the current quote.")
        if proposal["quote"] > state["policy"]["max_quote"]:
            raise ValueError("Quote exceeds the society's approval ceiling.")
        from .coordination import windows

        if not proposal.get("window") or not any(
            w["id"] == proposal["window"]["id"] and w["feasible"] for w in windows(state, incident)
        ):
            raise ValueError(
                "Resident availability changed or no shared window exists. Replan the visit first."
            )
        proposal["approved"] = True
        incident["status"] = "scheduled"
        from .coordination import visit_deadline

        incident["next_check"] = visit_deadline(proposal)
        event(
            state,
            incident,
            "Work authorized",
            f"Committee approved ₹{proposal['quote']}; a demo work order was created.",
            "Committee",
        )
    elif action == "delay":
        if role != "vendor" or incident["status"] != "scheduled":
            raise ValueError("Only the assigned vendor can report a delay on scheduled work.")
        incident["status"] = "delayed"
        incident["vendor_note"] = note or "Technician is delayed. A new arrival time is needed."
        incident["next_check"] = now()
        event(state, incident, "Vendor reported a delay", incident["vendor_note"], "Vendor")
    elif action == "replan":
        proposal = incident["proposal"]
        if (
            role != "committee"
            or incident["status"] != "needs_attention"
            or not proposal
            or not proposal["approved"]
        ):
            raise ValueError("Only the committee can reopen access planning for previously authorized work.")
        from .coordination import revisit_date, windows

        proposal["visit_date"] = revisit_date(proposal["visit_date"])
        proposal["id"] = uid("proposal")
        proposal["approved"] = False
        incident["negotiation"] = None
        incident["confirmed"] = []
        incident["next_check"] = None
        proposal["options"] = windows(state, incident)
        proposal["window"] = next((w for w in proposal["options"] if w["feasible"]), None)
        proposal["rationale"] = (
            "A revised visit requires a fresh access decision and committee approval. The original fixed quote is unchanged."
        )
        incident["status"] = "awaiting_approval"
        event(
            state,
            incident,
            "Fresh visit planning opened",
            f"Considering {proposal['visit_date']}. Previous one-time consents do not carry forward. The fixed quote remains ₹{proposal['quote']}.",
            "Committee",
        )
    elif action == "reschedule":
        if role != "committee" or incident["status"] != "needs_attention":
            raise ValueError("A committee decision is required to reschedule.")
        proposal = incident["proposal"]
        if not proposal or not proposal["approved"]:
            raise ValueError("Only previously authorized work can be rescheduled.")
        from .coordination import revisit_date, visit_deadline, windows

        # Consent to a particular visit cannot be carried onto a revised visit.
        options = windows(state, incident, include_consent=False)
        window = next((w for w in options if w["feasible"]), None)
        if not window:
            raise ValueError("No shared window exists. Update resident availability first.")
        proposal.update(options=options, window=window, visit_date=revisit_date(proposal["visit_date"]))
        incident["negotiation"] = None
        incident["status"] = "scheduled"
        incident["confirmed"] = []
        incident["next_check"] = visit_deadline(proposal)
        event(
            state,
            incident,
            "Revised visit authorized",
            note or "Committee accepted a revised visit; original quote remains fixed.",
            "Committee",
        )
    elif action == "complete":
        if role != "vendor" or incident["status"] != "scheduled":
            raise ValueError("Only scheduled work can be marked complete by the vendor.")
        if len(note.strip()) < 12:
            raise ValueError("Describe the work completed before requesting verification.")
        incident["status"] = "verifying"
        incident["vendor_note"] = note
        incident["next_check"] = None
        event(state, incident, "Work reported complete", note, "Vendor")
        event(
            state,
            incident,
            "Waiting for residents",
            "The incident stays open until every reporting household confirms restoration.",
        )
    elif action == "confirm":
        if role != "resident" or unit not in incident["reporters"] or incident["status"] != "verifying":
            raise ValueError("Only a reporting household can verify completed work.")
        if unit not in incident["confirmed"]:
            incident["confirmed"].append(unit)
            event(
                state,
                incident,
                "Resident verified restoration",
                f"{unit} confirmed the issue is resolved.",
                "Resident",
            )
        if set(incident["reporters"]) <= set(incident["confirmed"]):
            incident["status"] = "resolved"
            event(
                state,
                incident,
                "Resolved, with confirmation",
                "Every reporting household has verified the outcome.",
            )
    elif action == "reopen":
        if role != "resident" or unit not in incident["reporters"] or incident["status"] != "verifying":
            raise ValueError("Only a reporting household can challenge pending verification.")
        incident["status"] = "needs_attention"
        incident["confirmed"] = []
        event(
            state,
            incident,
            "Restoration not confirmed",
            note or "A resident reports the problem persists. Committee follow-up required.",
            "Resident",
        )
    else:
        raise ValueError("Unknown action.")
    return incident


def follow_up(state, incident_id):
    incident = incident_of(state, incident_id)
    if incident["status"] not in {"delayed", "scheduled"}:
        raise ValueError("This incident does not need a vendor follow-up.")
    if not incident["next_check"] or incident["next_check"] > now():
        raise ValueError("Follow-up is not due.")
    incident["status"] = "needs_attention"
    incident["next_check"] = None
    event(
        state,
        incident,
        "Relay caught the missed milestone",
        "Choose a revised visit or arrange an alternative. No extra spending has been authorized.",
    )
    return incident
