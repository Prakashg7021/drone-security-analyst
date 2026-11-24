"""Rule-based extraction from simulated frame descriptions."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


VEHICLES = (
    ("ford f150", "Ford F150", "truck"),
    ("ford f-150", "Ford F150", "truck"),
    ("pickup truck", "pickup truck", "truck"),
    ("blue truck", "blue truck", "truck"),
    ("truck", "truck", "truck"),
    ("red car", "red car", "car"),
    ("sedan", "sedan", "car"),
    ("car", "car", "car"),
    ("van", "van", "van"),
)
COLORS = ("blue", "red", "black", "white", "gray", "silver", "green", "yellow")
LOCATIONS = (
    ("main gate", "main gate"),
    ("warehouse", "warehouse"),
    ("garage", "garage"),
    ("east fence", "east fence"),
    ("loading bay", "loading bay"),
    ("restricted zone", "restricted zone"),
    ("perimeter", "perimeter"),
)


def extract_description(description: str) -> dict[str, Any]:
    """Extract entities and a location from text; this is not visual recognition."""
    text = description.casefold()
    objects: list[dict[str, str]] = []

    if re.search(r"\b(person|people|man|woman|individual|worker|pedestrian)\b", text):
        objects.append({"type": "person", "label": "person"})

    vehicle_match = next(
        ((phrase, label, kind) for phrase, label, kind in VEHICLES if phrase in text),
        None,
    )
    if vehicle_match:
        _, label, kind = vehicle_match
        color = next((color for color in COLORS if color in text), None)
        objects.append(
            {
                "type": "vehicle",
                "label": label,
                "kind": kind,
                "color": color or "unknown",
                "identity": f"{color or 'unknown'} {label.casefold()}",
            }
        )

    location = next(
        (name for phrase, name in LOCATIONS if phrase in text), "unknown"
    )
    if "restricted" in text and location == "unknown":
        location = "restricted zone"

    activity = "observation"
    activity_rules = (
        (r"\b(loiter|standing|stood|waiting|lingering)\b", "loitering"),
        (r"\b(entering|entered|inside|intrusion)\b", "entry"),
        (r"\b(leaving|exiting|exited)\b", "exit"),
        (r"\b(walking|walked|moving)\b", "movement"),
        (r"\b(driving|drives|driving into)\b", "vehicle_movement"),
        (r"\b(parked|parking)\b", "stationary_vehicle"),
    )
    for pattern, value in activity_rules:
        if re.search(pattern, text):
            activity = value
            break

    event_type = "person" if any(o["type"] == "person" for o in objects) else "other"
    if any(o["type"] == "vehicle" for o in objects):
        event_type = "vehicle"
    if "restricted" in text or "restricted zone" in location:
        event_type = "restricted_area"

    return {
        "objects": objects,
        "activity": activity,
        "location": location,
        "event_type": event_type,
    }


def normalize_timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.isoformat(timespec="seconds")
