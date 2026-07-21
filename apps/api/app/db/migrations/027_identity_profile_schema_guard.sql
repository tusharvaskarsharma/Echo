-- Compatibility guard for deployments created before identity_profiles had a
-- standalone id.  user_id remains the owner key; id is an immutable profile id.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.identity_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  full_name TEXT,
  preferred_name TEXT,
  occupation TEXT,
  languages JSONB NOT NULL DEFAULT '[]'::jsonb,
  privacy_settings JSONB NOT NULL DEFAULT '{"shared_fields": []}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS id UUID;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS preferred_name TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS occupation TEXT;
UPDATE public.identity_profiles SET id = gen_random_uuid() WHERE id IS NULL;
ALTER TABLE public.identity_profiles ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE public.identity_profiles ALTER COLUMN id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS identity_profiles_id_unique ON public.identity_profiles(id);

ALTER TABLE public.identity_profiles ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON public.identity_profiles TO authenticated;
DROP POLICY IF EXISTS identity_profile_owner_isolation ON public.identity_profiles;
CREATE POLICY identity_profile_owner_isolation ON public.identity_profiles
  FOR ALL TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));
