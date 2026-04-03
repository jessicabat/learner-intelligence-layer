# AGENTS.md — Learner Intelligence Layer

## What this project is
An adaptive speaking coach built in Streamlit. Users speak into the app,
their speech is transcribed with faster-whisper, and an intervention planner
decides how the AI tutor should respond based on a structured learner state
model. All session data is stored in PostgreSQL (Supabase).

## Stack
- Frontend: Streamlit (app.py is the entry point, run with `streamlit run app.py`)
- ASR: faster-whisper (local, base model)
- LLM: OpenAI gpt-4o-mini via the openai Python SDK, structured JSON output
- Database: PostgreSQL on Supabase (connection via psycopg2, credentials in .env)
- Charts: Plotly via st.plotly_chart

## File structure
- core/transcriber.py       — faster-whisper wrapper, returns transcript string
- core/learner_state.py     — LearnerState dataclass and update logic
- core/intervention_planner.py — rule-based planner, takes LearnerState, returns intervention type string
- core/llm_client.py        — gpt-4o-mini call wrapper, always returns structured JSON
- core/session_report.py    — computes scores and generates session report dict
- db/schema.sql             — PostgreSQL schema (learners, sessions, turns tables)
- db/queries.py             — all DB reads and writes, use psycopg2 with context managers
- data/scenarios.json       — scenario prompts for Mode B
- app.py                    — Streamlit UI, imports from core/ and db/

## Coding conventions
- Python 3.11+
- Type hints on all function signatures
- Docstrings on all public functions
- No function longer than 40 lines — split if needed
- All LLM calls go through core/llm_client.py, never inline
- All DB queries go through db/queries.py, never inline in app.py
- Environment variables loaded via python-dotenv, never hardcoded
- Wrap all LLM calls and DB writes in try/except, return a safe fallback

## Environment variables (see .env.example)
- OPENAI_API_KEY
- SUPABASE_DB_URL  (full PostgreSQL connection string)

## How to run locally
pip install -r requirements.txt
streamlit run app.py

## Done means
- No import errors on startup
- All functions have type hints and docstrings
- All DB writes use parameterized queries (no string formatting)
- The app runs without crashing on a clean install

## Do not
- Do not use SQLite — we use PostgreSQL only
- Do not add authentication logic — out of scope for MVP
- Do not use asyncio or WebSocket streaming — out of scope for MVP
- Do not add files outside the existing folder structure without asking