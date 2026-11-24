"""Configurable rule-based security alert generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from drone_security.database import (
    get_frame,
    initialize_database,
    list_alerts,
    save_alerts,
    search_frames,
)


@dataclass(frozen=True)
class AlertConfig:
    midnight_start_hour: int = 0
    midnight_end_hour: int = 4
    loitering_minutes: int = 10
    restricted_locations: tuple[str, ...] = ("restricted zone", "east fence")
    max_altitude_m: float = 60.0


def detect_alerts(
    db_path: str | None = None, config: AlertConfig = AlertConfig()
) -> list[dict[str, Any]]:
    frames = search_frames(db_path, limit=5000)
    candidates: list[dict[str, Any]] = []

    def add(frame: dict[str, Any], rule: str, severity: str, reason: str) -> None:
        candidates.append(
            {
                "frame_id": frame["frame_id"],
                "timestamp": frame["timestamp"],
                "severity": severity,
                "location": frame["location"],
                "reason": reason,
                "rule": rule,
            }
        )

    for frame in frames:
        timestamp = datetime.fromisoformat(frame["timestamp"])
        if frame["event_type"] == "restricted_area" or (
            frame["activity"] == "entry"
            and frame["location"] in config.restricted_locations
        ):
            add(
                frame,
                "restricted_area_entry",
                "critical",
                f"Activity entered or occurred in restricted area ({frame['location']}).",
            )

        altitude = frame["telemetry"].get("altitude_m")
        if isinstance(altitude, (int, float)) and altitude > config.max_altitude_m:
            add(
                frame,
                "unusual_telemetry_altitude",
                "high",
                f"Drone altitude {altitude:g} m exceeded configured limit "
                f"of {config.max_altitude_m:g} m.",
            )

        is_person = any(obj.get("type") == "person" for obj in frame["objects"])
        if (
            is_person
            and frame["location"] == "main gate"
            and config.midnight_start_hour <= timestamp.hour < config.midnight_end_hour
        ):
            for earlier in frames:
                if earlier["timestamp"] >= frame["timestamp"]:
                    break
                earlier_time = datetime.fromisoformat(earlier["timestamp"])
                if (
                    earlier["location"] == "main gate"
                    and any(obj.get("type") == "person" for obj in earlier["objects"])
                    and earlier_time.hour == timestamp.hour
                    and (timestamp - earlier_time).total_seconds()
                    >= config.loitering_minutes * 60
                ):
                    add(
                        frame,
                        "midnight_gate_loitering",
                        "high",
                        "Person observed near the main gate repeatedly during midnight "
                        f"hours for at least {config.loitering_minutes} minutes.",
                    )
                    break

    vehicle_groups: dict[str, list[dict[str, Any]]] = {}
    for frame in frames:
        for obj in frame["objects"]:
            if obj.get("type") == "vehicle":
                vehicle_groups.setdefault(obj["identity"], []).append(frame)
    for identity, appearances in vehicle_groups.items():
        if len(appearances) > 1:
            for frame in appearances[1:]:
                add(
                    frame,
                    f"repeated_vehicle:{identity}",
                    "medium",
                    f"Repeated appearance of {identity}; {len(appearances)} indexed "
                    "appearances observed.",
                )

    save_alerts(candidates, db_path)
    return list_alerts(db_path)


def alert_frames(alert_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    from drone_security.database import connection

    initialize_database(db_path)
    with connection(db_path) as conn:
        row = conn.execute(
            "SELECT frame_id FROM alerts WHERE alert_id = ?", (alert_id,)
        ).fetchone()
    return get_frame(row["frame_id"], db_path) if row else None
