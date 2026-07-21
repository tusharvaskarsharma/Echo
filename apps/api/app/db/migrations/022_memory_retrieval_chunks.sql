-- Durable, story-preserving retrieval units.  Existing memories remain the
-- canonical source of truth; chunks are derived index records and may be
-- safely recreated whenever the indexing format changes.
ALTER TABLE public.sessions
  ADD COLUMN IF NOT EXISTS transcript TEXT,
  ADD COLUMN IF NOT EXISTS transcript_segments JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE public.memory_chunks
  ADD COLUMN IF NOT EXISTS chunk_index INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'Stories',
  ADD COLUMN IF NOT EXISTS keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS vector_id TEXT,
  ADD COLUMN IF NOT EXISTS embedding_model TEXT,
  ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER,
  ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_chunks_memory_chunk_index
  ON public.memory_chunks(memory_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_memory_chunks_user_category
  ON public.memory_chunks(user_id, category, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_chunks_content_fts
  ON public.memory_chunks USING GIN (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_memory_chunks_keywords
  ON public.memory_chunks USING GIN (keywords);
