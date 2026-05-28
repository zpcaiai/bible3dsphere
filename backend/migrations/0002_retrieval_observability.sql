CREATE TABLE IF NOT EXISTS retrieval_eval_runs (
    id bigserial PRIMARY KEY,
    run_key text NOT NULL UNIQUE,
    top_k integer NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    cases jsonb NOT NULL DEFAULT '[]'::jsonb,
    source_path text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_retrieval_eval_runs_created_at
    ON retrieval_eval_runs (created_at DESC);

CREATE TABLE IF NOT EXISTS artifact_manifests (
    id bigserial PRIMARY KEY,
    manifest_key text NOT NULL UNIQUE,
    generated_at timestamptz,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_path text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_manifests_created_at
    ON artifact_manifests (created_at DESC);
