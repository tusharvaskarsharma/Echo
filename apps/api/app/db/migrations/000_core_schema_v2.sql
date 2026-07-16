-- 000_core_schema_v2.sql
-- This migration completely overhauls the ECHO database schema for production.
-- Run this in a fresh Supabase project or after dropping existing tables.

-- EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PROFILES (Syncs with auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger to automatically create a profile when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name)
  VALUES (new.id, new.email, new.raw_user_meta_data->>'full_name');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS trigger AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


-- 2. PERSONAS (The digital twins)
CREATE TABLE IF NOT EXISTS public.personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    date_of_birth DATE,
    biography TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ -- Soft delete
);
CREATE INDEX idx_personas_user_id ON public.personas(user_id);
CREATE TRIGGER update_personas_updated_at BEFORE UPDATE ON public.personas
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


-- 3. PERSONA VERSIONS (Fine-tuning iterations)
CREATE TABLE IF NOT EXISTS public.persona_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES public.personas(id) ON DELETE CASCADE,
    openai_model_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, training, completed, failed
    training_data_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_persona_versions_persona_id ON public.persona_versions(persona_id);
CREATE TRIGGER update_persona_versions_updated_at BEFORE UPDATE ON public.persona_versions
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


-- 4. VOICE PROFILES
CREATE TABLE IF NOT EXISTS public.voice_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL UNIQUE REFERENCES public.personas(id) ON DELETE CASCADE,
    elevenlabs_voice_id TEXT,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TRIGGER update_voice_profiles_updated_at BEFORE UPDATE ON public.voice_profiles
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


-- 5. SESSIONS (Interview sessions)
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES public.personas(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active', -- active, processing, completed
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_sessions_persona_id ON public.sessions(persona_id);


-- 6. MEMORIES
CREATE TABLE IF NOT EXISTS public.memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES public.personas(id) ON DELETE CASCADE,
    session_id UUID REFERENCES public.sessions(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    emotion_tags JSONB DEFAULT '[]'::jsonb,
    topics JSONB DEFAULT '[]'::jsonb,
    people_mentioned JSONB DEFAULT '[]'::jsonb,
    consent_level TEXT NOT NULL DEFAULT 'family', -- private, family, public
    confidence_score NUMERIC CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_memories_persona_id ON public.memories(persona_id);
CREATE INDEX idx_memories_session_id ON public.memories(session_id);


-- 7. MEMORY CHUNKS
CREATE TABLE IF NOT EXISTS public.memory_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_memory_chunks_memory_id ON public.memory_chunks(memory_id);


-- 8. CONVERSATIONS
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES public.personas(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_conversations_persona_id ON public.conversations(persona_id);
CREATE INDEX idx_conversations_user_id ON public.conversations(user_id);
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON public.conversations
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


-- 9. MESSAGES
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    memory_ids JSONB DEFAULT '[]'::jsonb, -- Array of memory UUIDs referenced
    latency_ms INTEGER,
    token_usage INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation_id ON public.messages(conversation_id);


-- 10. EMBEDDINGS METADATA
CREATE TABLE IF NOT EXISTS public.embeddings_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES public.personas(id) ON DELETE CASCADE,
    memory_chunk_id UUID NOT NULL REFERENCES public.memory_chunks(id) ON DELETE CASCADE,
    pinecone_vector_id TEXT NOT NULL,
    embedding_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(pinecone_vector_id)
);
CREATE INDEX idx_embeddings_persona_id ON public.embeddings_metadata(persona_id);


-- 11. UPLOADS
CREATE TABLE IF NOT EXISTS public.uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES public.personas(id) ON DELETE CASCADE,
    session_id UUID REFERENCES public.sessions(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL, -- Path in Supabase storage
    file_type TEXT NOT NULL, -- e.g., audio/webm
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 12. PROCESSING JOBS
CREATE TABLE IF NOT EXISTS public.processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type TEXT NOT NULL, -- e.g., 'transcribe', 'extract_memory', 'finetune'
    target_id UUID NOT NULL, -- references session, persona, etc.
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    result JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_jobs_target_id ON public.processing_jobs(target_id);
CREATE TRIGGER update_processing_jobs_updated_at BEFORE UPDATE ON public.processing_jobs
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


-- 13. AUDIT LOGS
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ROW LEVEL SECURITY (RLS) POLICIES

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- Profiles: users can only read/update their own profile
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Personas: owners can do everything. We can add legacy access control later via a legacy_contacts join table
CREATE POLICY "Users can manage own personas" ON public.personas FOR ALL USING (auth.uid() = user_id);

-- Sessions, Memories: accessed through persona ownership
CREATE POLICY "Users can view sessions of owned personas" ON public.sessions FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.personas WHERE personas.id = sessions.persona_id AND personas.user_id = auth.uid())
);
CREATE POLICY "Users can view memories of owned personas" ON public.memories FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.personas WHERE personas.id = memories.persona_id AND personas.user_id = auth.uid())
);

-- STORAGE BUCKETS (Needs to be run as superuser or via dashboard, provided here for completeness)
INSERT INTO storage.buckets (id, name, public) VALUES ('echo-media', 'echo-media', false) ON CONFLICT DO NOTHING;
