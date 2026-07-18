-- Retain the structured, evidence-only extraction alongside the existing
-- display fields. `search_document` is the exact text sent to embeddings.
ALTER TABLE public.memories
    ADD COLUMN IF NOT EXISTS search_document TEXT,
    ADD COLUMN IF NOT EXISTS semantic_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_memories_semantic_metadata
    ON public.memories USING GIN (semantic_metadata);
