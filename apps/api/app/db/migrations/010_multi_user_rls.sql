-- 010_multi_user_rls.sql

-- Existing unowned demo rows are intentionally left in place but are invisible once
-- RLS is enabled.  Never delete customer data as part of a schema migration.

-- 2. Create the User Profiles Table
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    username TEXT UNIQUE,
    email TEXT,
    bio TEXT,
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    country TEXT,
    theme_preference TEXT DEFAULT 'system',
    notification_preferences JSONB DEFAULT '{"email": true, "push": false}'::jsonb,
    ai_preferences JSONB DEFAULT '{"model": "llama-3.3-70b-versatile", "creativity": 0.7}'::jsonb,
    voice_preferences JSONB DEFAULT '{"speed": 1.0, "pitch": 1.0}'::jsonb,
    privacy_settings JSONB DEFAULT '{"share_data": false}'::jsonb,
    subscription_plan TEXT DEFAULT 'free',
    api_usage_statistics JSONB DEFAULT '{"tokens": 0, "storage": 0}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Add user_id to all existing tables
-- subjects
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
-- sessions
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
-- memories
ALTER TABLE memories ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
-- echo_profiles
ALTER TABLE echo_profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- legacy_contacts already has user_id, just add foreign key if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'legacy_contacts_user_id_fkey'
    ) THEN
        ALTER TABLE legacy_contacts ADD CONSTRAINT legacy_contacts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- conversation_history already has user_id, just add foreign key if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'conversation_history_user_id_fkey'
    ) THEN
        ALTER TABLE conversation_history ADD CONSTRAINT conversation_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- finetune_jobs
ALTER TABLE finetune_jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- 4. Enable Row Level Security (RLS) on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE echo_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE legacy_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE finetune_jobs ENABLE ROW LEVEL SECURITY;

-- 5. Create RLS Policies

-- Profiles: Users can view and update their own profile
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
CREATE POLICY "Users can insert own profile" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Subjects
DROP POLICY IF EXISTS "Users can manage own subjects" ON subjects;
CREATE POLICY "Users can manage own subjects" ON subjects FOR ALL USING (auth.uid() = user_id);

-- Sessions
DROP POLICY IF EXISTS "Users can manage own sessions" ON sessions;
CREATE POLICY "Users can manage own sessions" ON sessions FOR ALL USING (auth.uid() = user_id);

-- Memories
DROP POLICY IF EXISTS "Users can manage own memories" ON memories;
CREATE POLICY "Users can manage own memories" ON memories FOR ALL USING (auth.uid() = user_id);

-- Echo Profiles
DROP POLICY IF EXISTS "Users can manage own echo profiles" ON echo_profiles;
CREATE POLICY "Users can manage own echo profiles" ON echo_profiles FOR ALL USING (auth.uid() = user_id);

-- Legacy Contacts
DROP POLICY IF EXISTS "Users can manage own legacy contacts" ON legacy_contacts;
CREATE POLICY "Users can manage own legacy contacts" ON legacy_contacts FOR ALL USING (auth.uid() = user_id);

-- Conversation History
DROP POLICY IF EXISTS "Users can manage own conversation history" ON conversation_history;
CREATE POLICY "Users can manage own conversation history" ON conversation_history FOR ALL USING (auth.uid() = user_id);

-- Finetune Jobs
DROP POLICY IF EXISTS "Users can manage own finetune jobs" ON finetune_jobs;
CREATE POLICY "Users can manage own finetune jobs" ON finetune_jobs FOR ALL USING (auth.uid() = user_id);

-- 6. Trigger to automatically create a profile when a new user signs up in auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, username, email)
  VALUES (new.id, new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'username', new.email);
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if trigger exists and drop it before creating to avoid errors on multiple runs
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
