-- Emmy rebrand.  Existing data stays in place: PostgreSQL table/column
-- renames preserve rows, indexes, constraints, RLS state, and foreign keys.
-- The catalog checks make this safe for both existing and fresh deployments.

DO $$
BEGIN
  IF to_regclass('public.echo_profiles') IS NOT NULL
     AND to_regclass('public.emmy_profiles') IS NULL THEN
    ALTER TABLE public.echo_profiles RENAME TO emmy_profiles;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.conversation_history') IS NOT NULL
     AND EXISTS (
       SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'conversation_history' AND column_name = 'echo_profile_id'
     )
     AND NOT EXISTS (
       SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = 'conversation_history' AND column_name = 'emmy_profile_id'
     ) THEN
    ALTER TABLE public.conversation_history RENAME COLUMN echo_profile_id TO emmy_profile_id;
  END IF;
END $$;

DO $$
DECLARE
  legacy_constraint TEXT;
BEGIN
  SELECT conname INTO legacy_constraint
  FROM pg_constraint
  WHERE conrelid = 'public.conversation_history'::regclass
    AND conname = 'conversation_history_echo_profile_id_fkey';
  IF legacy_constraint IS NOT NULL THEN
    ALTER TABLE public.conversation_history
      RENAME CONSTRAINT conversation_history_echo_profile_id_fkey TO conversation_history_emmy_profile_id_fkey;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.emmy_profiles') IS NOT NULL
     AND EXISTS (
       SELECT 1 FROM pg_policies
       WHERE schemaname = 'public' AND tablename = 'emmy_profiles'
         AND policyname = 'Users can manage own echo profiles'
     ) THEN
    ALTER POLICY "Users can manage own echo profiles" ON public.emmy_profiles
      RENAME TO "Users can manage own emmy profiles";
  END IF;
END $$;
