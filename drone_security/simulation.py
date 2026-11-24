"""Deterministic sample telemetry and frame descriptions."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

ZONES = ("main gate", "warehouse", "garage", "east fence", "loading bay")


def generate_demo_frames(day: date | None = None) -> list[dict[str, Any]]:
    """Create 20 plausible, clearly simulated observations for one calendar day."""
    day = day or date.today()
    scenarios = [
        ("00:02", "Person standing near the main gate at midnight.", "main gate", 22),
        ("00:18", "Person still standing near the main gate at midnight.", "main gate", 21),
        ("01:10", "Blue Ford F150 parked near the garage.", "garage", 23),
        ("02:05", "Blue Ford F150 seen again near the warehouse.", "warehouse", 24),
        ("05:42", "Routine perimeter sweep; no people or vehicles visible.", "perimeter", 30),
        ("07:15", "Person walking near the warehouse.", "warehouse", 27),
        ("08:00", "White van entering the property at the main gate.", "main gate", 32),
        ("08:26", "White van leaving by the main gate.", "main gate", 31),
        ("09:40", "Blue Ford F150 spotted at main gate.", "main gate", 28),
        ("10:05", "Person walking beside the loading bay.", "loading bay", 26),
        ("11:20", "Red car entering the property at the main gate.", "main gate", 29),
        ("12:04", "Red car parked near the warehouse.", "warehouse", 31),
        ("13:30", "Person entering the restricted zone near the east fence.", "east fence", 25),
        ("14:05", "Person leaving the restricted zone near the east fence.", "east fence", 24),
        ("16:12", "Blue Ford F150 appearing again near the garage.", "garage", 34),
        ("18:45", "Person walking near the main gate.", "main gate", 22),
        ("20:10", "Black sedan passing the east fence.", "east fence", 27),
        ("21:22", "Drone telemetry altitude unusually high during warehouse sweep.", "warehouse", 82),
        ("22:10", "Blue Ford F150 near the loading bay.", "loading bay", 30),
        ("23:35", "Routine final perimeter sweep; no people or vehicles visible.", "perimeter", 29),
    ]
    frames: list[dict[str, Any]] = []
    for number, (clock, description, zone, altitude) in enumerate(scenarios, start=1):
        observed_at = datetime.combine(day, time.fromisoformat(clock))
        frames.append(
            {
                "frame_id": f"SIM-{day:%Y%m%d}-{number:03d}",
                "timestamp": observed_at.isoformat(timespec="seconds"),
                "description": description,
                "telemetry": {
                    "timestamp": observed_at.isoformat(timespec="seconds"),
                    "latitude": round(37.4215 + number * 0.00007, 6),
                    "longitude": round(-122.084 + number * 0.00005, 6),
                    "altitude_m": altitude,
                    "status": "monitoring",
                    "zone": zone,
                    "simulated": True,
                },
                "source": "simulated",
            }
        )
    return frames
