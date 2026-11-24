"""Database-grounded analyst queries with an optional LangGraph/OpenAI answer step."""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Any, TypedDict

from drone_security.database import list_alerts, repeated_vehicles, search_frames

try:
    from langchain_core.tools import tool

    from drone_security.alerts import alert_frames
    @tool
    def search_indexed_frames(query: str, location: str = "") -> list[dict[str, Any]]:
        """Search indexed frame descriptions and optionally filter by location."""
        return search_frames(query=query or None, location=location or None)

    @tool
    def retrieve_historical_events(start: str = "", end: str = "") -> list[dict[str, Any]]:
        """Retrieve stored event frames, optionally within ISO timestamps."""
        return search_frames(start=start or None, end=end or None)

    @tool
    def check_repeated_vehicle_appearances() -> list[dict[str, Any]]:
        """Return vehicle identities with multiple stored frame appearances."""
        return repeated_vehicles()

    @tool
    def retrieve_security_alerts() -> list[dict[str, Any]]:
        """Return security alerts already stored in SQLite."""
        return list_alerts()

    @tool
    def retrieve_frame_for_alert(alert_id: int) -> dict[str, Any] | None:
        """Return the indexed frame and telemetry associated with an alert ID."""
        return alert_frames(alert_id)

    @tool
    def generate_event_summary() -> dict[str, Any]:
        """Summarize stored frames by event type and location."""
        frames = search_frames()
        return {
            "total_frames": len(frames),
            "event_types": _counts(frame["event_type"] for frame in frames),
            "locations": _counts(frame["location"] for frame in frames),
            "frame_ids": [frame["frame_id"] for frame in frames],
        }

    TOOLS = (
        search_indexed_frames,
        retrieve_historical_events,
        check_repeated_vehicle_appearances,
        retrieve_security_alerts,
        retrieve_frame_for_alert,
        generate_event_summary,
    )
except ImportError:
    TOOLS = ()


def _counts(values: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def _summary() -> str:
    summary = _invoke_tool(
        "generate_event_summary",
        {},
        lambda: {
            "total_frames": len(search_frames()),
            "event_types": _counts(frame["event_type"] for frame in search_frames()),
        },
    )
    alerts = _invoke_tool("retrieve_security_alerts", {}, list_alerts)
    return (
        f"Indexed {summary['total_frames']} frames. Stored event types: "
        f"{summary['event_types'] or 'none'}. "
        f"Security alerts: {len(alerts)}. All figures come from the SQLite index."
    )


def _invoke_tool(name: str, arguments: dict[str, Any], fallback: Any) -> Any:
    selected = next((candidate for candidate in TOOLS if candidate.name == name), None)
    return selected.invoke(arguments) if selected else fallback()


def _answer_from_records(question: str) -> str:
    q = question.casefold()
    if not q.strip():
        return "Ask a question about indexed frames, activity, vehicles, or security alerts."

    if any(word in q for word in ("alert", "suspicious")):
        alerts = _invoke_tool("retrieve_security_alerts", {}, list_alerts)
        if "gate" in q:
            alerts = [alert for alert in alerts if alert["location"] == "main gate"]
        if not alerts:
            return "No security alerts are currently stored in the indexed records."
        return "Stored security alerts:\n" + "\n".join(
            f"- [{a['severity'].upper()}] {a['timestamp']} at {a['location']}: "
            f"{a['reason']} (frame {a['frame_id']})"
            for a in alerts
        )

    if "repeat" in q or "repeated" in q or "how many times" in q:
        repeats = _invoke_tool(
            "check_repeated_vehicle_appearances", {}, repeated_vehicles
        )
        match = re.search(r"\b(blue|red|black|white|gray|silver|green|yellow)\b", q)
        if match:
            repeats = [item for item in repeats if match.group(1) in item["identity"]]
        if any(term in q for term in ("truck", "ford", "pickup")):
            repeats = [
                item for item in repeats
                if any(token in item["identity"] for token in ("truck", "ford", "pickup"))
            ]
        if "today" in q:
            today = date.today().isoformat()
            todays_repeats = []
            for item in repeats:
                today_appearances = [
                    (frame_id, timestamp)
                    for frame_id, timestamp in zip(item["frame_ids"], item["timestamps"])
                    if timestamp[:10] == today
                ]
                if today_appearances:
                    todays_repeats.append(
                        {
                            **item,
                            "count": len(today_appearances),
                            "frame_ids": [frame_id for frame_id, _ in today_appearances],
                            "timestamps": [timestamp for _, timestamp in today_appearances],
                        }
                    )
            repeats = todays_repeats
        if not repeats:
            return "No repeated vehicle appearances matching that query are stored."
        return "Repeated vehicle appearances from indexed frames:\n" + "\n".join(
            f"- {item['identity']}: {item['count']} times; frames "
            f"{', '.join(item['frame_ids'])}."
            for item in repeats
        )

    if "midnight" in q or "around midnight" in q:
        history = _invoke_tool("retrieve_historical_events", {}, search_frames)
        frames = [
            f for f in history if f["timestamp"][11:13] in {"00", "01", "02", "03"}
        ]
    elif "main gate" in q or "gate" in q:
        frames = _invoke_tool(
            "search_indexed_frames",
            {"query": "", "location": "main gate"},
            lambda: search_frames(location="main gate"),
        )
    elif "truck" in q or "vehicle" in q or "car" in q:
        frames = [
            f for f in search_frames()
            if any(obj.get("type") == "vehicle" for obj in f["objects"])
            and ("truck" not in q or any(
                obj.get("type") == "vehicle" and obj.get("kind") == "truck"
                for obj in f["objects"]
            ))
        ]
    elif "today" in q or "summar" in q or "activity" in q:
        return _summary()
    else:
        frames = _invoke_tool(
            "search_indexed_frames",
            {"query": question, "location": ""},
            lambda: search_frames(query=question),
        )

    if not frames:
        return "No matching events are present in the SQLite index."
    if "how many" in q:
        return f"{len(frames)} matching frame(s) are in the SQLite index: " + ", ".join(
            frame["frame_id"] for frame in frames
        )
    return "Matching indexed events:\n" + "\n".join(
        f"- {frame['timestamp']} | {frame['location']} | {frame['description']} "
        f"(frame {frame['frame_id']})"
        for frame in frames
    )


class AgentState(TypedDict, total=False):
    question: str
    context: str
    answer: str
    mode: str


class SecurityAnalystAgent:
    """Use deterministic indexed answers by default; optional LLM only rephrases records."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.mode = "demo (deterministic SQLite fallback)"
        self._graph: Any = None
        if self.api_key:
            try:
                self._graph = self._build_graph()
                self.mode = f"LangGraph + OpenAI ({self.model})"
            except ImportError:
                self.mode = "demo (LangGraph/OpenAI packages unavailable; deterministic SQLite fallback)"

    @staticmethod
    def _build_graph() -> Any:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
        from langgraph.graph import END, START, StateGraph

        def retrieve(state: AgentState) -> AgentState:
            return {"context": _answer_from_records(state["question"])}

        def respond(state: AgentState) -> AgentState:
            response = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
            ).invoke(
                [
                    SystemMessage(
                        content=(
                            "Answer using only the supplied SQLite-derived context. "
                            "Do not infer missing events or claim events not in the records. "
                            "If context says no matches, state that plainly."
                        )
                    ),
                    HumanMessage(
                        content=f"Question: {state['question']}\nIndexed context:\n{state['context']}"
                    ),
                ]
            )
            return {"answer": str(response.content)}

        graph = StateGraph(AgentState)
        graph.add_node("retrieve", retrieve)
        graph.add_node("respond", respond)
        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "respond")
        graph.add_edge("respond", END)
        return graph.compile()

    def ask(self, question: str) -> str:
        if self._graph is None:
            return _answer_from_records(question)
        try:
            result = self._graph.invoke({"question": question})
            return result["answer"]
        except Exception as exc:
            return (
                "The configured LLM request failed; returning a deterministic answer "
                f"from SQLite instead ({type(exc).__name__}).\n"
                + _answer_from_records(question)
            )


def answer_question(question: str) -> str:
    return SecurityAnalystAgent().ask(question)
