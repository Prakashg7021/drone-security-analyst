from datetime import date

from drone_security.agent import SecurityAnalystAgent
from drone_security.alerts import detect_alerts
from drone_security.database import index_frames
from drone_security.simulation import generate_demo_frames


def test_fallback_answers_from_index(db_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DRONE_DB_PATH", str(db_path))
    index_frames(generate_demo_frames(date.today()), db_path)
    detect_alerts(str(db_path))
    agent = SecurityAnalystAgent()
    answer = agent.ask("How many times did the blue Ford truck appear today?")
    assert "5 times" in answer
    assert date.today().strftime("SIM-%Y%m%d") in answer
    assert "deterministic SQLite fallback" in agent.mode


def test_fallback_does_not_invent_missing_events(db_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DRONE_DB_PATH", str(db_path))
    agent = SecurityAnalystAgent()
    assert "No matching events" in agent.ask("What happened at the moon base?")
