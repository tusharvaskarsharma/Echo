-- 008_finetune_jobs.sql
CREATE TABLE IF NOT EXISTS finetune_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    openai_job_id TEXT,
    openai_file_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued', -- queued, running, completed, failed
    cost_usd NUMERIC,
    duration_seconds INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_finetune_jobs_subject_id ON finetune_jobs(subject_id);

COMMENT ON TABLE finetune_jobs IS 'Tracks OpenAI fine-tuning jobs for synthesizing persona models.';
