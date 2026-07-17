-- Remove provider-specific names from persisted persona-job metadata.
-- The current Groq persona architecture is retrieval based, so these columns
-- are reserved for a future provider rather than an OpenAI webhook/job ID.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'finetune_jobs' AND column_name = 'openai_job_id'
    ) THEN
        ALTER TABLE public.finetune_jobs RENAME COLUMN openai_job_id TO provider_job_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'finetune_jobs' AND column_name = 'openai_file_id'
    ) THEN
        ALTER TABLE public.finetune_jobs RENAME COLUMN openai_file_id TO provider_file_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'persona_versions' AND column_name = 'openai_model_id'
    ) THEN
        ALTER TABLE public.persona_versions RENAME COLUMN openai_model_id TO provider_model_id;
    END IF;
END $$;
