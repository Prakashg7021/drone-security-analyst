from datetime import date

from drone_security.database import get_frame, index_frames, repeated_vehicles, search_frames
from drone_security.simulation import generate_demo_frames


def test_frame_index_timestamp_location_and_search(db_path):
    index_frames(generate_demo_frames(date(2026, 1, 2))[:3], db_path)
    frame = get_frame("SIM-20260102-001", db_path)
    assert frame is not None
    assert frame["timestamp"] == "2026-01-02T00:02:00"
    assert frame["location"] == "main gate"
    assert frame["telemetry"]["zone"] == "main gate"
    assert len(search_frames(db_path, location="main gate")) == 2


def test_repeated_vehicle_detection(db_path):
    index_frames(generate_demo_frames(date(2026, 1, 2)), db_path)
    matches = repeated_vehicles(db_path)
    ford = next(item for item in matches if item["identity"] == "blue ford f150")
    assert ford["count"] == 5


def test_timestamp_range_search(db_path):
    index_frames(generate_demo_frames(date(2026, 1, 2)), db_path)
    matches = search_frames(
        db_path,
        start="2026-01-02T00:00:00",
        end="2026-01-02T01:30:00",
    )
    assert [frame["frame_id"] for frame in matches] == [
        "SIM-20260102-001",
        "SIM-20260102-002",
        "SIM-20260102-003",
    ]
