# Feature specification

## Prototype behavior

| Area | Behavior |
|---|---|
| Telemetry | Simulated timestamp, coordinates, altitude, monitoring status, and zone per generated frame. |
| Frame descriptions | Twenty built-in scenarios with timestamps; sample descriptions are explicitly simulated. |
| Extraction | Transparent text rules identify people, vehicle color/type, activities, locations, and event categories. |
| Event history | SQLite stores frame ID, timestamp, description, extracted objects, activity, location, event type, telemetry JSON, and source. |
| Alerts | Midnight gate loitering, repeated vehicle, restricted-area activity, and configurable maximum altitude. Alerts store severity, time, location, reason, rule, and related frame. |
| Search | Search text/object, location, timestamp range, event type, repeated vehicle identities, and alert-associated frames. |
| Analyst | Python search functions are exposed as LangChain tools. LangGraph optionally generates a response from database-derived context. No-key mode uses deterministic database queries. |
| Dashboard | Metrics, timeline, telemetry, searchable frame table, alert table, chat, demo reset, and optional video upload. |

## Alert defaults

- Midnight is local time from 00:00 inclusive to 04:00 exclusive.
- Loitering requires two person descriptions at the main gate at the same hour at least 10 minutes apart.
- Repeated-vehicle alerts are attached to subsequent observations after the first appearance of the extracted identity.
- Restricted-area-related descriptions create critical alerts.
- Altitude greater than 60 m creates a high-severity telemetry alert.

These are demo rules, not validated operational thresholds.
