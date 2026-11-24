# Drone Security Analyst Agent

A local, CPU-friendly prototype for a docked drone monitoring a fixed property. It creates simulated telemetry and text-described frames, extracts events with transparent Python rules, stores every frame in SQLite, evaluates alert rules, and answers historical questions from indexed records.

> **Important:** bundled observations are simulation fixtures. The entity and activity extraction is keyword/rule-based analysis of frame descriptions, **not computer vision or a VLM**. Uploaded video is sampled with OpenCV, but pixels are not classified and no objects are claimed from those images.

## Requirements and installation

- Python 3.10+ (developed with Python 3.11)
- No GPU required
- OpenAI key is optional; demo mode is fully offline.

From this directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set environment variables in the active shell when using OpenAI:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
```

The `.env` file is a template and is not automatically loaded by the application. The database defaults to `data/drone_security.db`; override it with `DRONE_DB_PATH`.

## Run

```powershell
streamlit run app.py
```

Choose **Load / reset simulated demo data** in the sidebar. It replaces the prototype database's current rows with 20 simulated frames, then runs the alert engine. Ask questions in the chat panel. Without a key the interface explicitly reports deterministic SQLite fallback mode.

Run tests:

```powershell
python -m pytest -q
```

## Implemented functionality

- 20 day-long example frames and per-frame simulated GPS, altitude, status, and zone.
- Rule-based extraction for people, colored vehicle types, activity, location, and event type.
- SQLite persistence, indexed time/location searches, and stable demo frame IDs.
- Alerts for midnight gate loitering, repeated vehicle appearances, restricted-area events, and altitude above a configurable threshold.
- LangGraph response workflow with optional LangChain `ChatOpenAI` response generation; deterministic database-grounded query mode works without network access or credentials.
- Streamlit metrics, event timeline/index, telemetry, alerts, search filters, and historical chat.
- Optional OpenCV upload sampling. Sampled JPEGs are saved to `data/extracted_frames` and metadata is indexed; images have unknown locations and unavailable telemetry, and are not classified.

## Sample output

Example records (timestamps use the current local date when demo data is loaded):

```text
SIM-YYYYMMDD-001 | 00:02 | main gate | Person standing near the main gate at midnight.
SIM-YYYYMMDD-002 | 00:18 | main gate | Person still standing near the main gate at midnight.
SIM-YYYYMMDD-003 | 01:10 | garage    | Blue Ford F150 parked near the garage.
```

Representative rule outputs:

```text
HIGH     midnight_gate_loitering       SIM-YYYYMMDD-002
MEDIUM   repeated_vehicle:blue ford f150  (subsequent appearances)
CRITICAL restricted_area_entry        SIM-YYYYMMDD-013
HIGH     unusual_telemetry_altitude   SIM-YYYYMMDD-018
```

Fallback query example:

```text
Q: How many times did the blue Ford truck appear today?
A: Repeated vehicle appearances from indexed frames:
   - blue ford f150: 4 times; frames SIM-YYYYMMDD-003, ...
```

The example answer is calculated from indexed rows, not generated from an external data source.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Feature specification](docs/FEATURE_SPEC.md)
- [Test documentation](docs/TESTING.md)
- [AI-assisted development notes](docs/AI_ASSISTED_DEVELOPMENT.md)
- [Limitations and future work](docs/LIMITATIONS.md)
