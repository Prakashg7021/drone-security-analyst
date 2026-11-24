# Limitations and future improvements

## Current limitations

- Sampled demo descriptions and telemetry are fabricated. Text extraction is not object detection, and the optional OpenCV sampler does not classify image pixels.
- Uploaded-video frames are saved as JPEGs under `data/extracted_frames`, but have unknown locations and unavailable drone telemetry. Frame descriptions explicitly state that vision analysis was not performed.
- Entity matching uses normalized text labels, not visual identity, license plates, or tracking. A shared vehicle label does not prove it is the same physical vehicle.
- Loitering and restricted-area rules are simple illustrative heuristics; the sample uses a fixed local clock and configured boundaries.
- SQLite is suitable for a local single-user prototype, not high-volume or concurrent fleet ingestion.
- LLM use is optional and requires a valid key, network connectivity, and a compatible API account. Model responses may paraphrase incorrectly despite grounding; check original frame rows.
- The Streamlit app is a prototype and has no authentication, authorization, audit trail, or deployment hardening.

## Possible next steps

- Add a real, authorized vision model with confidence thresholds and human review.
- Add GPS geofences, timezone-aware schedules, identity tracking, deduplication, and configurable rule management.
- Add ingestion validation, schema migrations, retention policy, user authentication, audit logs, and role-based alert acknowledgment.
- Add alert evaluation datasets, precision/recall measures, and operational rule tuning.
- Move to a server database and background ingestion for multi-drone workloads.
