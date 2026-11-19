-- User-owned social controls and a human moderation queue. No private body copy.
CREATE TABLE IF NOT EXISTS user_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blocker_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    blocked_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    identity_known BOOLEAN NOT NULL DEFAULT TRUE,
    source_key VARCHAR(400) NOT NULL,
    UNIQUE (blocker_email, source_key),
    CHECK (blocker_email <> blocked_email)
);
CREATE INDEX IF NOT EXISTS idx_user_blocks_target ON user_blocks(blocked_email);

CREATE TABLE IF NOT EXISTS social_reports (
    id UUID PRIMARY KEY,
    reporter_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    target_email VARCHAR(255) NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    resource_key VARCHAR(255) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN
        ('harassment','hate','sexual','violence','spam','child_safety','other')),
    status VARCHAR(32) NOT NULL DEFAULT 'review_pending'
        CHECK (status IN ('review_pending','under_review','closed')),
    reviewer_email VARCHAR(255),
    disposition VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    UNIQUE (reporter_email, resource_type, resource_key, category)
);
CREATE INDEX IF NOT EXISTS idx_social_reports_review ON social_reports(status, created_at);

-- Server-owned room capability; a client-supplied vd_ prefix is not authority.
CREATE TABLE IF NOT EXISTS direct_voice_rooms (
    id VARCHAR(64) PRIMARY KEY,
    user_low VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    user_high VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    CHECK (user_low < user_high)
);
CREATE INDEX IF NOT EXISTS idx_direct_voice_rooms_expiry ON direct_voice_rooms(expires_at);
