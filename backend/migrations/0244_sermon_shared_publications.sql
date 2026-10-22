-- Shared sermon publications use the existing wall. Core sermon_journals and
-- personal_notes tables are established by the application's base schema.
-- Match bootstrap DDL so both existing Neon deployments and first-run startup
-- receive the same nullable foreign key and uniqueness invariant.
ALTER TABLE personal_notes ADD COLUMN IF NOT EXISTS
    source_sermon_id INTEGER REFERENCES sermon_journals(id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_note_source_sermon
    ON personal_notes(source_sermon_id);
