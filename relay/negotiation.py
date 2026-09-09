"""Consent-bound access negotiation. A one-off yes never edits a household calendar."""

import hashlib
import json

from .coordination import windows


def context_key(state, incident):
    proposal = incident.get("proposal") or {}
    context = {
        "reporters": sorted(incident["reporters"]),
        "availability": {u: state.get("availability", {}).get(u) for u in incident["reporters"]},
        "blocked": sorted(state.get("blocked_slots", ["midday"])),
        "vendor_slots": sorted(state.get("vendor_slots", ["morning", "afternoon", "evening"])),
        "date": proposal.get("visit_date"),
        "vendor": proposal.get("vendor_id"),
        "quote": proposal.get("quote"),
    }
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def current(state, incident):
    negotiation = incident.get("negotiation")
    return negotiation if negotiation and negotiation["context"] == context_key(state, incident) else None


def consented_units(state, incident, slot_id):
    negotiation = current(state, incident)
    if not negotiation or negotiation.get("slot_id") != slot_id:
        return set()
    return {u for u, answer in negotiation.get("answers", {}).items() if answer == "accepted"}


def alternatives(state, incident):
    """Smallest number of exceptions first; never approach a household again after a no."""
    negotiation = current(state, incident)
    declined = set(negotiation.get("declined_units", [])) if negotiation else set()
    result = []
    for option in windows(state, incident, include_consent=False):
        missing = option["needs_coordination"]
        if not missing:
            continue
        result.append(
            {
                **option,
                "eligible": not bool(declined.intersection(missing)),
                "exceptions_needed": len(missing),
                "quote_change": 0,
                "reason": "A household already declined; Relay will not ask them again in this round."
                if declined.intersection(missing)
                else "Requires explicit one-time consent; general availability stays unchanged.",
            }
        )
    return sorted(result, key=lambda o: (not o["eligible"], o["exceptions_needed"], o["hour"]))


def needs_negotiation(state, incident):
    if incident["status"] != "awaiting_approval" or not incident.get("proposal"):
        return False
    if any(w["feasible"] for w in windows(state, incident)):
        return False
    negotiation = current(state, incident)
    return not negotiation or negotiation["status"] == "declined"


def request_window(state, incident_id, slot_id, rationale, actor="Relay"):
    from . import domain

    incident = domain.incident_of(state, incident_id)
    if (
        incident["status"] != "awaiting_approval"
        or not incident.get("proposal")
        or incident["proposal"]["approved"]
    ):
        raise ValueError("Access negotiation is only available before work is authorized.")
    if any(w["feasible"] for w in windows(state, incident)):
        raise ValueError("A shared window already exists; review the current proposal.")
    previous = current(state, incident)
    if previous and previous["status"] == "waiting":
        raise ValueError("Wait for the outstanding household response before proposing another window.")
    options = alternatives(state, incident)
    eligible = [o for o in options if o["eligible"]]
    if slot_id == "none":
        if eligible:
            raise ValueError("There are still consent-based alternatives to consider.")
        chosen = None
    else:
        chosen = next((o for o in eligible if o["id"] == slot_id), None)
        if not chosen:
            raise ValueError(
                "Choose an eligible window; quiet hours and household refusals cannot be overridden."
            )
    negotiation = {
        "id": domain.uid("access"),
        "context": context_key(state, incident),
        "status": "waiting" if chosen else "exhausted",
        "slot_id": slot_id,
        "label": chosen["label"] if chosen else None,
        "required": chosen["needs_coordination"] if chosen else [],
        "answers": {},
        "declined_units": previous.get("declined_units", []) if previous else [],
        "options": options,
        "rationale": rationale[:600],
        "visit_date": incident["proposal"]["visit_date"],
    }
    incident["negotiation"] = negotiation
    incident["proposal"]["id"] = domain.uid("proposal")
    domain.event(
        state,
        incident,
        "A one-time access request" if chosen else "No further consent-based plan",
        f"{chosen['label']} on {negotiation['visit_date']}: asking {', '.join(negotiation['required'])}. No booking or calendar change."
        if chosen
        else "Relay will not repeat a declined request. A human must revise the constraints.",
        actor,
    )
    return negotiation


def respond(state, incident_id, negotiation_id, unit, answer, role):
    from . import domain

    incident = domain.incident_of(state, incident_id)
    negotiation = current(state, incident)
    if role != "resident" or incident["status"] != "awaiting_approval":
        raise ValueError("Only a resident can answer an access request before authorization.")
    if not negotiation or negotiation["id"] != negotiation_id:
        raise ValueError("This access request changed. Review the current plan.")
    withdrawing = answer == "withdrawn" and negotiation["answers"].get(unit) == "accepted"
    if negotiation["status"] != "waiting" and not (negotiation["status"] == "agreed" and withdrawing):
        raise ValueError("This access request changed. Review the current plan.")
    if unit not in negotiation["required"] or (unit in negotiation["answers"] and not withdrawing):
        raise ValueError("This household has no unanswered request.")
    if answer not in {"accepted", "declined"} and not withdrawing:
        raise ValueError("Choose whether this one-time visit works for you.")
    negotiation["answers"][unit] = answer
    if answer in {"declined", "withdrawn"}:
        negotiation["declined_units"] = sorted(set(negotiation["declined_units"] + [unit]))
        negotiation["status"] = "declined"
        # A partial yes was conditional on this exact plan, not a transferable consent.
        negotiation["answers"] = {unit: "declined"}
    elif all(negotiation["answers"].get(u) == "accepted" for u in negotiation["required"]):
        negotiation["status"] = "agreed"
    proposal = incident["proposal"]
    proposal["id"] = domain.uid("proposal")
    proposal["options"] = windows(state, incident)
    proposal["window"] = next((w for w in proposal["options"] if w["feasible"]), None)
    if proposal["window"]:
        proposal["rationale"] = (
            f"A one-time access agreement makes {proposal['window']['label']} possible. The quote is unchanged. Committee approval is still required."
        )
    else:
        proposal["rationale"] = (
            "A shared access agreement is still needed. The quote is unchanged and approval remains blocked."
        )
    domain.event(
        state,
        incident,
        "One-time access accepted"
        if answer == "accepted"
        else "One-time access withdrawn"
        if withdrawing
        else "Resident declined the exception",
        f"{unit}: {negotiation['label']} on {negotiation['visit_date']}. "
        + (
            "General availability is unchanged."
            if answer == "accepted"
            else "Relay must find an alternative without asking this household again in this round."
        ),
        "Resident",
    )
    return negotiation
