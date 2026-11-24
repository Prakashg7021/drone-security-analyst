from datetime import date

from drone_security.alerts import detect_alerts
from drone_security.database import index_frames
from drone_security.simulation import generate_demo_frames


def test_midnight_loitering_alert(db_path):
    frames = generate_demo_frames(date(2026, 1, 2))[:2]
    index_frames(frames, db_path)
    alerts = detect_alerts(str(db_path))
    assert any(alert["rule"] == "midnight_gate_loitering" for alert in alerts)


def test_restricted_area_alert(db_path):
    frame = generate_demo_frames(date(2026, 1, 2))[12]
    index_frames([frame], db_path)
    alerts = detect_alerts(str(db_path))
    assert any(
        alert["severity"] == "critical" and alert["frame_id"] == frame["frame_id"]
        for alert in alerts
    )


def test_unusual_telemetry_alert(db_path):
    frame = generate_demo_frames(date(2026, 1, 2))[17]
    index_frames([frame], db_path)
    alerts = detect_alerts(str(db_path))
    assert any(alert["rule"] == "unusual_telemetry_altitude" for alert in alerts)
