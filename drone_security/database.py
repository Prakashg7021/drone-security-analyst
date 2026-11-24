"""SQLite persistence and frame/event search helpers."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from drone_security.processing import extract_description, normalize_timestamp

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "drone_security.db"


def get_db_path() -> Path:
    configured = os.getenv("DRONE_DB_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_DB_PATH


@contextmanager
def connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_path: str | Path | None = None) -> None:
    with connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS frames (
                frame_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                description TEXT NOT NULL,
                objects_json TEXT NOT NULL,
                activity TEXT NOT NULL,
                location TEXT NOT NULL,
                event_type TEXT NOT NULL,
                telemetry_json TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'simulated'
            );
            CREATE INDEX IF NOT EXISTS idx_frames_timestamp ON frames(timestamp);
            CREATE INDEX IF NOT EXISTS idx_frames_location ON frames(location);
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id TEXT NOT NULL REFERENCES frames(frame_id) ON DELETE CASCADE,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                location TEXT NOT NULL,
                reason TEXT NOT NULL,
                rule TEXT NOT NULL,
                UNIQUE(frame_id, rule)
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
            """
        )


def index_frames(
    frames: list[dict[str, Any]], db_path: str | Path | None = None
) -> int:
    initialize_database(db_path)
    indexed = 0
    with connection(db_path) as conn:
        for frame in frames:
            frame_id = str(frame["frame_id"])
            timestamp = normalize_timestamp(frame["timestamp"])
            description = str(frame.get("description", ""))
            extracted = extract_description(description)
            telemetry = frame.get("telemetry") or {}
            telemetry.setdefault("timestamp", timestamp)
            telemetry.setdefault("zone", extracted["location"])
            telemetry.setdefault("status", "unknown")
            telemetry.setdefault("simulated", frame.get("source", "simulated") == "simulated")
            conn.execute(
                """
                INSERT INTO frames
                    (frame_id, timestamp, description, objects_json, activity,
                     location, event_type, telemetry_json, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(frame_id) DO UPDATE SET
                    timestamp=excluded.timestamp,
                    description=excluded.description,
                    objects_json=excluded.objects_json,
                    activity=excluded.activity,
                    location=excluded.location,
                    event_type=excluded.event_type,
                    telemetry_json=excluded.telemetry_json,
                    source=excluded.source
                """,
                (
                    frame_id,
                    timestamp,
                    description,
                    json.dumps(extracted["objects"]),
                    extracted["activity"],
                    extracted["location"],
                    extracted["event_type"],
                    json.dumps(telemetry),
                    str(frame.get("source", "simulated")),
                ),
            )
            indexed += 1
    return indexed


def _frame_dict(row: sqlite3.Row) -> dict[str, Any]:
    frame = dict(row)
    frame["objects"] = json.loads(frame.pop("objects_json"))
    frame["telemetry"] = json.loads(frame.pop("telemetry_json"))
    return frame


def search_frames(
    db_path: str | Path | None = None,
    *,
    query: str | None = None,
    location: str | None = None,
    start: str | None = None,
    end: str | None = None,
    event_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    clauses: list[str] = []
    params: list[Any] = []
    if query:
        clauses.append("(description LIKE ? COLLATE NOCASE OR objects_json LIKE ? COLLATE NOCASE)")
        params.extend([f"%{query}%", f"%{query}%"])
    if location:
        clauses.append("location LIKE ? COLLATE NOCASE")
        params.append(f"%{location}%")
    if start:
        clauses.append("timestamp >= ?")
        params.append(normalize_timestamp(start))
    if end:
        clauses.append("timestamp <= ?")
        params.append(normalize_timestamp(end))
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM frames{where} ORDER BY timestamp LIMIT ?",
            [*params, max(1, min(limit, 5000))],
        ).fetchall()
    return [_frame_dict(row) for row in rows]


def get_frame(frame_id: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    initialize_database(db_path)
    with connection(db_path) as conn:
        row = conn.execute("SELECT * FROM frames WHERE frame_id = ?", (frame_id,)).fetchone()
    return _frame_dict(row) if row else None


def repeated_vehicles(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    frames = search_frames(db_path, event_type="vehicle")
    appearances: dict[str, list[dict[str, Any]]] = {}
    for frame in frames:
        for obj in frame["objects"]:
            if obj.get("type") == "vehicle":
                appearances.setdefault(obj["identity"], []).append(frame)
    return [
        {
            "identity": identity,
            "count": len(items),
            "frame_ids": [item["frame_id"] for item in items],
            "timestamps": [item["timestamp"] for item in items],
        }
        for identity, items in sorted(appearances.items())
        if len(items) > 1
    ]


def list_alerts(
    db_path: str | Path | None = None, frame_id: str | None = None
) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with connection(db_path) as conn:
        if frame_id:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE frame_id = ? ORDER BY timestamp", (frame_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM alerts ORDER BY timestamp").fetchall()
    return [dict(row) for row in rows]


def save_alerts(alerts: list[dict[str, Any]], db_path: str | Path | None = None) -> None:
    initialize_database(db_path)
    with connection(db_path) as conn:
        for alert in alerts:
            conn.execute(
                """
                INSERT INTO alerts (frame_id, timestamp, severity, location, reason, rule)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(frame_id, rule) DO UPDATE SET
                    timestamp=excluded.timestamp, severity=excluded.severity,
                    location=excluded.location, reason=excluded.reason
                """,
                (
                    alert["frame_id"],
                    normalize_timestamp(alert["timestamp"]),
                    alert["severity"],
                    alert["location"],
                    alert["reason"],
                    alert["rule"],
                ),
            )


def counts(db_path: str | Path | None = None) -> dict[str, int]:
    initialize_database(db_path)
    with connection(db_path) as conn:
        frame_count = conn.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
        alert_rows = conn.execute(
            "SELECT severity, COUNT(*) AS n FROM alerts GROUP BY severity"
        ).fetchall()
    by_severity = {row["severity"]: row["n"] for row in alert_rows}
    return {
        "frames": frame_count,
        "alerts": sum(by_severity.values()),
        "critical": by_severity.get("critical", 0),
        "high": by_severity.get("high", 0),
        "medium": by_severity.get("medium", 0),
    }


def latest_telemetry(db_path: str | Path | None = None) -> dict[str, Any] | None:
    frames = search_frames(db_path, limit=5000)
    return frames[-1]["telemetry"] if frames else None


def reset_database(db_path: str | Path | None = None) -> None:
    initialize_database(db_path)
    with connection(db_path) as conn:
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM frames")
