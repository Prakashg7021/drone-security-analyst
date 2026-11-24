# AI-assisted development

This prototype uses deterministic fixtures and hand-authored Python rules for extraction and alert decisions. Those rules are inspectable and testable and do not claim to be model predictions.

An optional LangGraph workflow uses LangChain's OpenAI chat integration only when `OPENAI_API_KEY` is configured. The workflow supplies a SQLite-derived answer context and directs the LLM not to introduce unrecorded events. API availability, model behavior, and network access are outside the offline demo path. The Python search functions are also exposed as LangChain tools for extension.

Before adapting this prototype for real monitoring, validate rules and thresholds with authorized, representative data; review privacy, safety, and operational requirements; and independently verify every alert.
