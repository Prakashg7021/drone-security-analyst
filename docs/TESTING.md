# Test documentation

Run the automated suite from the project root:

```powershell
python -m pytest -q
```

Tests verify rule-based object extraction; SQLite frame indexing and timestamp/location retrieval; repeated vehicle grouping; midnight loitering and restricted-area alerts; telemetry alerting; and fallback answers based on stored rows, including a no-match response.

Temporary SQLite databases are created by fixtures, so tests do not alter the runtime database.

For a manual smoke test, launch Streamlit, load the demo rows, check the frame and alert tables, and ask about the repeated blue Ford truck and events around midnight. Confirm the application labels its agent as deterministic fallback when `OPENAI_API_KEY` is unset.
