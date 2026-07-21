-- Rename the auto-generated foreign-key constraint left behind by the table rename.
-- Safe to rerun: an existing Emmy constraint is never overwritten.
DO $$
BEGIN
  IF to_regclass('public.emmy_profiles') IS NOT NULL
     AND EXISTS (
       SELECT 1
       FROM pg_constraint
       WHERE connamespace = 'public'::regnamespace
         AND conname = 'echo_profiles_user_id_fkey'
     )
     AND NOT EXISTS (
       SELECT 1
       FROM pg_constraint
       WHERE connamespace = 'public'::regnamespace
         AND conname = 'emmy_profiles_user_id_fkey'
     ) THEN
    ALTER TABLE public.emmy_profiles
      RENAME CONSTRAINT echo_profiles_user_id_fkey TO emmy_profiles_user_id_fkey;
  END IF;
END
$$;
