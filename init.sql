CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS submissions (
  id SERIAL PRIMARY KEY,
  telegram_handle TEXT NOT NULL,
  chat_id BIGINT,
  embedding vector(512),
  photo BYTEA,
  uploaded_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS upload_log (
  id SERIAL PRIMARY KEY,
  chat_id BIGINT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS consent_requests (
  id SERIAL PRIMARY KEY,
  match_key TEXT NOT NULL,
  user_a_chat_id BIGINT NOT NULL,
  user_a_handle TEXT NOT NULL,
  user_a_consent BOOLEAN DEFAULT NULL,
  user_b_chat_id BIGINT NOT NULL,
  user_b_handle TEXT NOT NULL,
  user_b_consent BOOLEAN DEFAULT NULL,
  created_at TIMESTAMP DEFAULT now()
);
