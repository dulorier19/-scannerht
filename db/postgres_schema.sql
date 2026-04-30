CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    intro_seen BOOLEAN NOT NULL DEFAULT FALSE,
    language TEXT,
    market TEXT,
    trading_style TEXT,
    coins JSONB NOT NULL DEFAULT '[]'::jsonb,
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    active_message_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_users_language ON users (language);
CREATE INDEX IF NOT EXISTS idx_users_market ON users (market);
