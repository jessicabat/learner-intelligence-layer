CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE learners (
  learner_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMP DEFAULT NOW(),
  display_name TEXT DEFAULT 'Learner'
);

CREATE TABLE sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  learner_id UUID REFERENCES learners(learner_id),
  mode TEXT NOT NULL CHECK (mode IN ('repeat', 'roleplay')),
  scenario TEXT,
  started_at TIMESTAMP DEFAULT NOW(),
  ended_at TIMESTAMP,
  fluency_score FLOAT,
  grammar_score FLOAT,
  task_completed BOOLEAN,
  top_errors JSONB,
  recommended_next TEXT,
  improvement_delta JSONB
);

CREATE TABLE turns (
  turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(session_id),
  turn_number INT NOT NULL,
  transcript TEXT,
  target_sentence TEXT,
  grammar_errors JSONB,
  fluency_signals JSONB,
  intervention_type TEXT,
  tutor_response TEXT,
  accuracy_score FLOAT
);