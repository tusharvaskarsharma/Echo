-- Multi-tenant resources introduced for the SaaS application.  Every row is owned by auth.users.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE subjects ALTER COLUMN date_of_birth DROP NOT NULL;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE memories ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE emmy_profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE emmy_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE finetune_jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE legacy_contacts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE legacy_contacts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE conversation_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS memory_chunks (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE, content TEXT NOT NULL, embedding JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS uploads (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, storage_path TEXT NOT NULL UNIQUE, file_name TEXT NOT NULL, content_type TEXT, byte_size BIGINT NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS voice_profiles (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, name TEXT NOT NULL, provider_voice_id TEXT, settings JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS processing_jobs (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, job_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', payload JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS analytics_events (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, event_name TEXT NOT NULL, properties JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['profiles','subjects','sessions','memories','emmy_profiles','legacy_contacts','conversation_history','finetune_jobs','memory_chunks','uploads','voice_profiles','processing_jobs','analytics_events'] LOOP EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', 'set_updated_at',t); EXECUTE format('CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()',t); EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t); EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I',t); IF t='profiles' THEN EXECUTE format('CREATE POLICY tenant_isolation ON %I FOR ALL USING (auth.uid() = id) WITH CHECK (auth.uid() = id)',t); ELSE EXECUTE format('CREATE POLICY tenant_isolation ON %I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)',t); END IF; END LOOP; END $$;
CREATE INDEX IF NOT EXISTS idx_subjects_user_id ON subjects(user_id); CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id, created_at DESC); CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id, created_at DESC); CREATE INDEX IF NOT EXISTS idx_memory_chunks_user_id ON memory_chunks(user_id); CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id); CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversation_history(user_id, created_at DESC);
INSERT INTO storage.buckets (id, name, public) VALUES ('user-uploads','user-uploads',false) ON CONFLICT DO NOTHING;
DROP POLICY IF EXISTS user_uploads_isolation ON storage.objects;
CREATE POLICY user_uploads_isolation ON storage.objects FOR ALL USING (bucket_id='user-uploads' AND auth.uid()::text = (storage.foldername(name))[1]) WITH CHECK (bucket_id='user-uploads' AND auth.uid()::text = (storage.foldername(name))[1]);
