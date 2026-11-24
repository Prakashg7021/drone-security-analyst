"""Streamlit dashboard for the Drone Security Analyst prototype."""

from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from drone_security.alerts import detect_alerts
from drone_security.agent import SecurityAnalystAgent
from drone_security.database import (
    counts,
    get_db_path,
    index_frames,
    latest_telemetry,
    list_alerts,
    reset_database,
    search_frames,
)
from drone_security.simulation import generate_demo_frames
from drone_security.video import extract_video_frames

st.set_page_config(page_title="Drone Security Analyst", page_icon="🚁", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #0b1220; color: #e5eaf2; }
    [data-testid="stMetric"] { background: #131e30; border: 1px solid #25334a;
        padding: 16px; border-radius: 12px; }
    [data-testid="stSidebar"] { background: #101a2a; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🚁 Drone Security Analyst")
st.caption("Docked-drone monitoring prototype · simulated text analysis, SQLite event memory")

db_path = get_db_path()
agent = SecurityAnalystAgent()
st.sidebar.subheader("Demo controls")
if st.sidebar.button("Load / reset simulated demo data", type="primary"):
    reset_database(db_path)
    index_frames(generate_demo_frames(date.today()), db_path)
    detect_alerts(str(db_path))
    st.session_state.messages = []
    st.sidebar.success("Loaded 20 simulated frames and evaluated alert rules.")

upload = st.sidebar.file_uploader("Optional video upload", type=["mp4", "mov", "avi", "mkv"])
interval = st.sidebar.number_input("Video sample interval (seconds)", min_value=1, max_value=60, value=5)
if upload and st.sidebar.button("Extract and index sampled frames"):
    temp_path: str | None = None
    try:
        suffix = Path(upload.name).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(upload.getvalue())
            temp_path = temp.name
        extracted = extract_video_frames(
            temp_path,
            float(interval),
            output_dir=db_path.parent / "extracted_frames",
        )
        indexed = index_frames(extracted, db_path)
        detect_alerts(str(db_path))
        st.sidebar.success(f"Indexed {indexed} sampled frames; no visual classification was performed.")
    except (RuntimeError, ValueError, OSError) as exc:
        st.sidebar.error(f"Video processing failed: {exc}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

metrics = counts(db_path)
cols = st.columns(5)
cols[0].metric("Frames processed", metrics["frames"])
cols[1].metric("Detected events", len(search_frames(db_path, event_type="person")) +
               len(search_frames(db_path, event_type="vehicle")) +
               len(search_frames(db_path, event_type="restricted_area")))
cols[2].metric("Security alerts", metrics["alerts"])
cols[3].metric("Critical / High", f"{metrics['critical']} / {metrics['high']}")
cols[4].metric("Medium", metrics["medium"])
st.caption(f"Agent mode: **{agent.mode}** · database: `{db_path}`")

frames = search_frames(db_path)
alerts = list_alerts(db_path)
left, right = st.columns([1.25, 1])
with left:
    st.subheader("Frame event timeline")
    if frames:
        timeline = pd.DataFrame(frames)
        timeline["timestamp"] = pd.to_datetime(timeline["timestamp"])
        timeline["event"] = timeline["event_type"] + " · " + timeline["location"]
        st.dataframe(
            timeline[["timestamp", "frame_id", "event", "activity", "description"]],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Load demo data or index video frames to populate the timeline.")
with right:
    st.subheader("Drone telemetry")
    telemetry = latest_telemetry(db_path)
    if telemetry:
        telemetry_table = pd.DataFrame(
            [
                {"Field": str(key), "Value": str(value)}
                for key, value in telemetry.items()
            ]
        )
        st.dataframe(telemetry_table, width="stretch", hide_index=True)
    else:
        st.info("No telemetry indexed yet.")

st.subheader("Searchable frame index")
c1, c2, c3 = st.columns([2, 1, 1])
text_filter = c1.text_input("Description / object")
location_filter = c2.selectbox("Location", ["All", "main gate", "warehouse", "garage",
                                               "east fence", "loading bay", "unknown"])
event_filter = c3.selectbox("Event type", ["All", "person", "vehicle", "restricted_area", "other"])
visible = search_frames(
    db_path,
    query=text_filter or None,
    location=None if location_filter == "All" else location_filter,
    event_type=None if event_filter == "All" else event_filter,
)
if visible:
    frame_table = pd.DataFrame(
        [
            {
                "Frame ID": f["frame_id"],
                "Timestamp": f["timestamp"],
                "Description": f["description"],
                "Objects": ", ".join(obj["label"] for obj in f["objects"]) or "none",
                "Activity": f["activity"],
                "Location": f["location"],
                "Telemetry": f["telemetry"],
            }
            for f in visible
        ]
    )
    st.dataframe(frame_table, width="stretch", hide_index=True)
else:
    st.info("No frames match the selected filters.")

st.subheader("Security alerts")
if alerts:
    st.dataframe(pd.DataFrame(alerts), width="stretch", hide_index=True)
else:
    st.info("No alerts are stored. Load the demo data to run the configurable rules.")

st.subheader("Ask the security analyst")
st.caption("Historical answers are grounded in stored SQLite records. LLM mode requires OPENAI_API_KEY.")
if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
prompt = st.chat_input("e.g. How many times did the blue Ford truck appear today?")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": agent.ask(prompt)})
    st.rerun()
