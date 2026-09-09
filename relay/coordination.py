"""Deterministic coordination: intersect private constraints, disclose only the decision."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

SLOTS = [
    {"id": "morning", "label": "10:00–11:00", "hour": 10},
    {"id": "midday", "label": "12:00–13:00", "hour": 12},
    {"id": "afternoon", "label": "15:00–16:00", "hour": 15},
    {"id": "evening", "label": "17:00–18:00", "hour": 17},
]


def windows(state, incident):
    """Rank feasible slots without leaking residents' private reasons."""
    household_constraints = state.get("availability", {})
    blocked = state.get("blocked_slots", ["midday"])
    vendor_slots = state.get("vendor_slots", ["morning", "afternoon", "evening"])
    options = []
    for slot in SLOTS:
        if slot["id"] in blocked or slot["id"] not in vendor_slots:
            continue
        attending = [
            u
            for u in incident["reporters"]
            if slot["id"] in household_constraints.get(u, ["morning", "afternoon", "evening"])
        ]
        missing = sorted(set(incident["reporters"]) - set(attending))
        options.append(
            {
                **slot,
                "households_available": len(attending),
                "households_total": len(incident["reporters"]),
                "needs_coordination": missing,
                "feasible": not missing,
            }
        )
    return sorted(options, key=lambda o: (not o["feasible"], len(o["needs_coordination"]), o["hour"]))


def calendar_event(incident):
    """A real standards-based downloadable visit, based on an approved proposal."""
    if not incident["proposal"] or not incident["proposal"]["approved"]:
        raise ValueError("Only an approved visit can be exported.")
    slot = incident["proposal"].get("window")
    if not slot:
        raise ValueError("A visit window must be agreed first.")
    # Store the chosen date when preparing the proposal; do not shift it on each download.
    date = incident["proposal"]["visit_date"].replace("-", "")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    start = f"{date}T{slot['hour']:02d}0000"
    end = f"{date}T{slot['hour'] + 1:02d}0000"

    def safe(text):
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\r", "")
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Society Relay//Community Visit//EN",
        "BEGIN:VEVENT",
        f"UID:{incident['id']}@society-relay",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=Asia/Kolkata:{start}",
        f"DTEND;TZID=Asia/Kolkata:{end}",
        "SUMMARY:" + safe("Demo maintenance visit: " + incident["area"]),
        "DESCRIPTION:"
        + safe(
            f"Synthetic demonstration. {incident['proposal']['vendor']}. Approved quote INR {incident['proposal']['quote']}. Residents verify restoration before closure."
        ),
        "LOCATION:" + safe(incident["area"]),
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def visit_date():
    return (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)).date().isoformat()


def visit_deadline(proposal):
    planned = datetime.fromisoformat(proposal["visit_date"]).replace(
        hour=proposal["window"]["hour"] + 1, tzinfo=ZoneInfo("Asia/Kolkata")
    )
    return planned.astimezone(UTC).isoformat()
