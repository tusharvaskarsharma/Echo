-- Structured, long-lived facts for an Emmy. These fields deliberately live
-- outside memories/Pinecone so identity questions never depend on RAG.
-- Every statement is safe when this migration is replayed by a rebuilt API.

CREATE TABLE IF NOT EXISTS public.identity_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT,
  preferred_name TEXT,
  date_of_birth DATE,
  gender TEXT,
  pronouns TEXT,
  occupation TEXT,
  education TEXT,
  nationality TEXT,
  religion TEXT,
  languages JSONB NOT NULL DEFAULT '[]'::jsonb,
  hometown TEXT,
  current_city TEXT,
  biography TEXT,
  spouse TEXT,
  children JSONB NOT NULL DEFAULT '[]'::jsonb,
  parents JSONB NOT NULL DEFAULT '[]'::jsonb,
  siblings JSONB NOT NULL DEFAULT '[]'::jsonb,
  grandchildren JSONB NOT NULL DEFAULT '[]'::jsonb,
  pets JSONB NOT NULL DEFAULT '[]'::jsonb,
  website TEXT,
  social_links JSONB NOT NULL DEFAULT '{}'::jsonb,
  email TEXT,
  values JSONB NOT NULL DEFAULT '[]'::jsonb,
  motto TEXT,
  favorite_quote TEXT,
  favorite_song TEXT,
  favorite_book TEXT,
  favorite_food TEXT,
  favorite_place TEXT,
  blood_group TEXT,
  allergies TEXT,
  medical_notes TEXT,
  privacy_settings JSONB NOT NULL DEFAULT '{"shared_fields": []}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT identity_profiles_languages_array CHECK (jsonb_typeof(languages) = 'array'),
  CONSTRAINT identity_profiles_children_array CHECK (jsonb_typeof(children) = 'array'),
  CONSTRAINT identity_profiles_parents_array CHECK (jsonb_typeof(parents) = 'array'),
  CONSTRAINT identity_profiles_siblings_array CHECK (jsonb_typeof(siblings) = 'array'),
  CONSTRAINT identity_profiles_grandchildren_array CHECK (jsonb_typeof(grandchildren) = 'array'),
  CONSTRAINT identity_profiles_pets_array CHECK (jsonb_typeof(pets) = 'array'),
  CONSTRAINT identity_profiles_values_array CHECK (jsonb_typeof(values) = 'array'),
  CONSTRAINT identity_profiles_social_links_object CHECK (jsonb_typeof(social_links) = 'object'),
  CONSTRAINT identity_profiles_privacy_settings_object CHECK (jsonb_typeof(privacy_settings) = 'object')
);

-- Additive columns keep an early manual version of this table upgradeable.
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS preferred_name TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS gender TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS pronouns TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS occupation TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS education TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS nationality TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS religion TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS languages JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS hometown TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS current_city TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS biography TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS spouse TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS children JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS parents JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS siblings JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS grandchildren JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS pets JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS website TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS social_links JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS values JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS motto TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS favorite_quote TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS favorite_song TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS favorite_book TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS favorite_food TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS favorite_place TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS blood_group TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS allergies TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS medical_notes TEXT;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS privacy_settings JSONB NOT NULL DEFAULT '{"shared_fields": []}'::jsonb;
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.identity_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_identity_profiles_updated_at ON public.identity_profiles(updated_at DESC);

ALTER TABLE public.identity_profiles ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON public.identity_profiles TO authenticated;

-- Owners can always read and edit their complete Life Profile.  Accepted
-- group access is exposed through the safe function below, which removes
-- fields the owner has not opted in to share before returning any data.
DROP POLICY IF EXISTS identity_profile_owner_isolation ON public.identity_profiles;
CREATE POLICY identity_profile_owner_isolation ON public.identity_profiles
  FOR ALL TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));

DROP TRIGGER IF EXISTS identity_profiles_set_updated_at ON public.identity_profiles;
CREATE TRIGGER identity_profiles_set_updated_at
  BEFORE UPDATE ON public.identity_profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Group members cannot SELECT the base row (which could include private
-- health/contact data).  They can call this function only for an owner whose
-- group has active memory sharing.  It returns the owner-selected fields.
CREATE OR REPLACE FUNCTION public.get_shared_identity_profile(target_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  profile_row public.identity_profiles%ROWTYPE;
  permitted BOOLEAN;
  shared_fields JSONB;
  result JSONB;
BEGIN
  SELECT * INTO profile_row FROM public.identity_profiles WHERE user_id = target_user_id;
  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  permitted := target_user_id = (select auth.uid()) OR EXISTS (
    SELECT 1
    FROM public.memory_permissions AS permissions
    JOIN public.group_members AS membership ON membership.group_id = permissions.group_id
    WHERE permissions.memory_owner_id = target_user_id
      AND membership.user_id = (select auth.uid())
  );
  IF NOT permitted THEN
    RAISE EXCEPTION 'You do not have access to this Life Profile' USING ERRCODE = '42501';
  END IF;

  IF target_user_id = (select auth.uid()) THEN
    RETURN to_jsonb(profile_row);
  END IF;

  shared_fields := COALESCE(profile_row.privacy_settings->'shared_fields', '[]'::jsonb);
  SELECT COALESCE(jsonb_object_agg(field_name, field_value), '{}'::jsonb)
    INTO result
  FROM jsonb_each(to_jsonb(profile_row)) AS fields(field_name, field_value)
  WHERE field_name IN ('user_id', 'created_at', 'updated_at')
     OR shared_fields ? field_name;
  RETURN result;
END;
$$;

REVOKE ALL ON FUNCTION public.get_shared_identity_profile(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_shared_identity_profile(UUID) TO authenticated;
