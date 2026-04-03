# Learner Intelligence Layer — Mini MVP PRD

**Project:** Agentic Fluency Coach
**Version:** 1.0
**Status:** In progress
**Last updated:** April 2026

---

## Overview

This document describes the MVP for the **Learner Intelligence Layer**, a voice-based adaptive speaking coach built to demonstrate product, data science, and AI engineering thinking relevant to Speak's core product.

The goal of the MVP is to show that an AI tutor can do more than just respond to a learner. It should observe what the learner is doing, maintain a structured model of their progress, decide how to intervene based on that model, and produce a measurable outcome at the end of every session.

This is not a Speak clone. The focus is on the intelligence layer that sits on top of a conversation and makes tutoring decisions, which is the part Speak describes as its "learning engine" but does not publicly expose.

---

## Problem

Most AI language tutors respond fluently but do not actually track what the learner needs. Every session starts from zero. Errors get corrected once and then forgotten. There is no structure for deciding when to drill a weak point, when to push harder, or what to recommend next. This makes practice feel random instead of purposeful, which is one of the biggest reasons learners stop showing up.

The MVP directly addresses this gap by building a system that updates a learner profile after every speaking turn, uses that profile to drive tutor behavior, and produces a structured session report that could feed into a retention or personalization system.

---

## Target User

For the MVP, the target user is an adult English learner at the A2 to B1 level who wants to improve spoken fluency through scenario-based conversation practice. They are comfortable using a web app on desktop. They want feedback that feels relevant to their specific mistakes, not generic corrections.

---

## Goals

**Must have for MVP**

- User can speak into the app and get a transcription of their audio
- The app tracks grammar errors, hesitation signals, and task completion across a session
- The tutor changes its behavior based on the learner's current state
- The user sees a session report with scores and recommendations at the end
- All session data is stored in a PostgreSQL database
- The app is publicly accessible via a Streamlit Community Cloud link

**Nice to have (post-MVP)**

- Multiple session history with trend charts
- Pronunciation scoring using phoneme alignment
- User login and persistent learner profiles
- B2B admin dashboard showing aggregate learner analytics

**Out of scope for MVP**

- Mobile app
- Real-time streaming audio (WebSocket)
- Multi-language support beyond English
- Payment or subscription features

---

## Core Features

### Feature 1: Mode A — Repeat After Me

The app shows the user a target sentence. The user records themselves saying it. The system transcribes the recording and compares it to the target. The tutor gives corrective feedback and a score.

This mode is designed for accuracy and pronunciation practice. It maps to Speak's guided lesson experience where users practice specific sentence patterns.

**Acceptance criteria:**
- Target sentence is displayed clearly before recording starts
- Audio is transcribed within 5 seconds of submission
- Feedback includes: accuracy score (0 to 100), list of word-level differences, and a short friendly correction message
- User can move to the next sentence or try again

---

### Feature 2: Mode B — Open Roleplay

The app presents a scenario prompt such as "You are at a job interview. The interviewer just asked: tell me about yourself." The user speaks freely. The system transcribes and evaluates grammar, vocabulary, and naturalness.

This mode is designed to simulate the kind of unscripted conversation Speak focuses on with its Live Roleplays feature.

**Acceptance criteria:**
- At least 6 scenario prompts available at launch (job interview, café order, travel check-in, team standup, casual introduction, making a complaint)
- After each turn, the learner state model updates with error counts and fluency signals
- The tutor response adapts based on the current learner state
- User can complete a full conversation of 4 to 6 turns before seeing the session report

---

### Feature 3: Learner State Model

After every speaking turn, the system updates a structured learner profile. This is the core intelligence layer and the main differentiator of the project.

**Fields tracked per session:**

```python
LearnerState {
  session_id
  learner_id
  grammar_errors: { tense, article, preposition, subject_verb_agreement }
  vocabulary_flags: [list of missed or incorrect words]
  fluency_signals: {
    avg_turn_length_words,
    hesitation_rate,       # filler words per turn
    sentence_completion    # proportion of complete sentences
  }
  confidence_proxy: float  # 0 to 1, derived from turn length and hesitation rate
  task_completed: boolean
  recurring_errors: [errors seen 2 or more times this session]
  improvement_delta: { grammar, fluency }  # vs previous session if available
}
```

---

### Feature 4: Intervention Planner

After each turn, the intervention planner reads the current learner state and decides what type of tutor response to generate. The LLM prompt is shaped by the intervention type, not just the conversation history.

**Intervention rules:**

| Condition | Intervention |
|---|---|
| Same error type 3 or more times | Drill mode: repeat the correction with 3 variations |
| Very short answers or high hesitation | Simplify: offer a sentence starter |
| Task objective not completed by turn 4 | Redirect: steer back to the scenario goal |
| No errors, long answers, high confidence | Push: introduce harder vocabulary or a follow-up |
| Critical error mid-conversation | Defer: note it internally, revisit at end of session |
| No issues, normal flow | Continue: natural conversation continuation |

The planner outputs an intervention type. The LLM prompt uses that type to generate a response that fits the tutor's behavior for that intervention.

---

### Feature 5: Session Analytics Report

At the end of every session, the app generates a structured report and displays it in a clean dashboard view.

**Report contents:**

- Fluency score (0 to 100): based on avg turn length, sentence completion, hesitation rate
- Grammar score (0 to 100): based on error count per 100 words and recurring errors
- Task completion: yes or no
- Top 3 recurring error types with examples from the session
- Which intervention types fired and how many times
- Improvement delta vs previous session (if available)
- Recommended next practice: one sentence describing what to focus on

All session data is written to PostgreSQL at the end of each session.

---

## System Architecture

```
User (browser)
    |
    | audio input
    v
[Streamlit Frontend]
    |
    | audio file
    v
[faster-whisper (local ASR)]
    |
    | transcript
    v
[Learner State Updater]   <----->   [PostgreSQL: sessions, turns, learner profiles]
    |
    | updated state
    v
[Intervention Planner]
    |
    | intervention type + context
    v
[LLM (gpt-4o-mini)]
    |
    | tutor response + structured feedback JSON
    v
[Streamlit Frontend: display response + update UI]
    |
    | end of session
    v
[Session Report Generator]
    |
    v
[Analytics Dashboard (Plotly)]
```

---

## Tech Stack

### Frontend and Hosting

| Layer | Tool | Why |
|---|---|---|
| UI framework | Streamlit | Fast to build, easy to deploy, already familiar |
| Audio recording | `streamlit-mic-recorder` | Browser-native mic access inside Streamlit |
| Charts | Plotly (via `st.plotly_chart`) | Clean interactive charts for session reports |
| Hosting | Streamlit Community Cloud | Free, public URL, no server management needed |

### AI and ML

| Layer | Tool | Why |
|---|---|---|
| Speech-to-text | `faster-whisper` (local, `base` model) | Free, runs on CPU, fast enough for short recordings |
| LLM for feedback and tutor response | OpenAI `gpt-4o-mini` API | Cheap (~$0.15 per 1M input tokens), structured output support |
| Learner state extraction | Python functions + LLM-assisted parsing | Keeps it simple and interpretable |
| Intervention planner | Python rule-based logic | Transparent, easy to debug and explain |

### Data and Backend

| Layer | Tool | Why |
|---|---|---|
| Database | PostgreSQL (hosted on Supabase free tier) | Free, production-grade, SQL skills apply directly |
| ORM / query layer | `psycopg2` or `SQLAlchemy` | Standard Python PostgreSQL clients |
| Session state | Streamlit session state (in-memory) | No auth needed for MVP, keeps complexity low |
| Environment variables | `python-dotenv` + Streamlit secrets | Keeps API keys out of the repo |

### Dev Tools

| Layer | Tool |
|---|---|
| Version control | Git + GitHub (public repo) |
| Package management | `pip` + `requirements.txt` |
| Local development | VS Code + Python 3.11+ virtual environment |
| API testing | Simple Python scripts |

---

## Database Schema

### `learners`

| Column | Type | Notes |
|---|---|---|
| learner_id | UUID | Primary key |
| created_at | TIMESTAMP | Auto |
| display_name | TEXT | Optional, defaults to "Learner" |

### `sessions`

| Column | Type | Notes |
|---|---|---|
| session_id | UUID | Primary key |
| learner_id | UUID | FK to learners |
| mode | TEXT | "repeat" or "roleplay" |
| scenario | TEXT | Scenario name for Mode B |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | |
| fluency_score | FLOAT | 0 to 100 |
| grammar_score | FLOAT | 0 to 100 |
| task_completed | BOOLEAN | |
| top_errors | JSONB | List of top 3 error types |
| recommended_next | TEXT | One-sentence recommendation |
| improvement_delta | JSONB | Delta vs prior session |

### `turns`

| Column | Type | Notes |
|---|---|---|
| turn_id | UUID | Primary key |
| session_id | UUID | FK to sessions |
| turn_number | INT | Sequence within session |
| transcript | TEXT | ASR output |
| target_sentence | TEXT | Mode A only |
| grammar_errors | JSONB | Error type counts |
| fluency_signals | JSONB | Hesitation, length, completion |
| intervention_type | TEXT | Planner decision |
| tutor_response | TEXT | LLM output |
| accuracy_score | FLOAT | Mode A only |

---

## Cost Estimate

| Item | Cost |
|---|---|
| `faster-whisper` (local ASR) | Free |
| OpenAI `gpt-4o-mini` API | ~$0 to $5 total for development and testing |
| Supabase PostgreSQL (free tier) | Free up to 500MB storage |
| Streamlit Community Cloud | Free |
| GitHub | Free |
| **Total** | **$0 to $5** |

---

## Risks and Open Questions

**ASR accuracy on noisy audio**
`faster-whisper` base model performs well on clean audio but can struggle with accented speech or background noise. Mitigation: document this as a known limitation and note that Whisper Large v3 or the OpenAI Whisper API would improve accuracy in production.

**Intervention planner quality**
Rule-based logic is interpretable but brittle. The planner may misfire if learner state signals are noisy. Mitigation: log every planner decision and manually review 20 to 30 sessions during testing to check whether interventions make sense.

**LLM response consistency**
`gpt-4o-mini` with structured output (`response_format=json`) is fairly reliable but can still produce unexpected formats. Mitigation: wrap all LLM calls in try/except blocks and define a fallback response format.

**Supabase free tier limits**
Supabase free tier allows 500MB of storage and 2 CPU cores. This is sufficient for a portfolio demo with low traffic but would need upgrading for real production use.

**No real user data**
The MVP will be validated using self-generated and friend-generated sessions, not real learner data. Mitigation: be transparent about this in the product memo. Frame it as a prototype that demonstrates the instrumentation and decision logic, not a study with statistically significant findings.

---

## Out of Scope Decisions

- No user authentication in MVP. Learner ID is generated per session and stored in Streamlit session state.
- No real-time streaming audio. Audio is recorded in full, then submitted.
- No pronunciation phoneme scoring (requires forced alignment tools like `montreal-forced-aligner`, which adds significant setup complexity).
- No mobile-responsive UI optimization for MVP.

---

## Success Criteria for MVP Completion

- [ ] Public Streamlit demo URL is live and accessible
- [ ] Mode A works end to end: record, transcribe, score, feedback
- [ ] Mode B works end to end: scenario prompt, full conversation, session report
- [ ] Learner state updates visibly between turns (shown in a sidebar or debug panel)
- [ ] At least one intervention type demonstrably changes tutor behavior
- [ ] Session report renders with scores, top errors, and recommendation
- [ ] All session and turn data writes correctly to PostgreSQL
- [ ] At least 20 test sessions logged with real audio
- [ ] Product memo written and linked from the GitHub README
- [ ] Loom walkthrough video recorded and linked

---

## 4-Week Roadmap

### Week 1: Foundation

Set up repo, virtual environment, and Supabase PostgreSQL instance. Define and migrate the full database schema. Build the basic Streamlit app: audio recorder, faster-whisper transcription, and Mode A transcript vs target comparison with a simple accuracy score. Write the LearnerState Python dataclass.

**Deliverable:** App transcribes audio and shows word-level diff between transcript and target sentence.

### Week 2: Intelligence Layer

Build the learner state updater that extracts grammar errors and fluency signals from each transcript using GPT-4o-mini with structured JSON output. Build the intervention planner as a set of Python functions that read LearnerState and return an intervention type. Wire the intervention type into the LLM prompt so tutor behavior visibly changes. Test with 10 manual sessions and review planner decisions.

**Deliverable:** Tutor behaves differently for a struggling learner vs a confident one.

### Week 3: Mode B and Analytics

Build Mode B: scenario selection, multi-turn conversation loop, task completion tracking. Build the session report generator and the analytics dashboard with Plotly charts. Write all session and turn data to PostgreSQL at end of session. Run 20 to 30 test sessions and collect real data. Add a simple "progress" view showing score trends across sessions.

**Deliverable:** Full two-mode app with session reports and PostgreSQL logging working correctly.

### Week 4: Polish and Packaging

Clean up the UI, fix any rough edges from testing, and confirm the public Streamlit link works reliably. Write the product memo (2 to 4 pages): problem, user, system design, KPI framework, failure modes, and next experiments. Record a 3 to 5 minute Loom walkthrough showing a full roleplay session and explaining one or two intervention decisions. Update resume with 2 to 3 targeted bullets framing the project for Speak.

**Deliverable:** Public demo + GitHub repo + product memo + Loom = complete outreach package.

---

## Appendix: KPI Framework

These are the metrics the system is designed to produce, mapped to the kind of outcomes Speak likely tracks internally.

**Session-level metrics (produced by the app)**

- Fluency score per session
- Grammar score per session
- Task completion rate
- Intervention trigger rate by type
- Accuracy score per sentence (Mode A)

**Cross-session metrics (enabled by PostgreSQL)**

- Fluency score trend over N sessions
- Grammar error reduction by category over time
- Improvement delta per session
- Most common recurring error types by learner
- Average sessions per week (habit and retention proxy)

**System quality metrics (for the product memo)**

- ASR word error rate on test recordings
- Proportion of intervention decisions judged correct on manual review
- LLM feedback correctness rate on a small labeled set
- Session report generation latency (target: under 3 seconds)
