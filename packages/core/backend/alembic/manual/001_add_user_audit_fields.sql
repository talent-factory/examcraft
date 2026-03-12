-- Migration: add_user_audit_fields
-- Corresponding Alembic revision: d715210cb3a3
-- Date: 2026-03-12
-- Safe to run multiple times (IF NOT EXISTS)

ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_method VARCHAR(20);

-- Register this migration in Alembic's version table so that
-- `alembic upgrade head` knows the DB is already at this revision.
-- This creates the alembic_version table if it doesn't exist yet.
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Only insert if not already stamped
INSERT INTO alembic_version (version_num)
SELECT 'd715210cb3a3'  -- pragma: allowlist secret
WHERE NOT EXISTS (
    SELECT 1 FROM alembic_version WHERE version_num = 'd715210cb3a3'  -- pragma: allowlist secret
);
