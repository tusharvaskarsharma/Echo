-- Canonical, globally unique usernames. NULL remains allowed for accounts that
-- predate the username requirement; profile updates require a valid username.
UPDATE public.profiles
SET username = lower(btrim(username))
WHERE username IS NOT NULL;

CREATE OR REPLACE FUNCTION public.normalize_profile_username()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF NEW.username IS NOT NULL THEN
    NEW.username := lower(btrim(NEW.username));
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS normalize_profile_username_before_write ON public.profiles;
CREATE TRIGGER normalize_profile_username_before_write
  BEFORE INSERT OR UPDATE OF username ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.normalize_profile_username();

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_username_format_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_username_format_check
  CHECK (
    username IS NULL OR (
      username ~ '^[a-z0-9](?:[a-z0-9_]{1,18}[a-z0-9])?$'
      AND username !~ '__'
    )
  );

-- The existing unique constraint remains in place. This explicit partial index
-- documents and enforces the global lookup path for non-null usernames.
CREATE UNIQUE INDEX IF NOT EXISTS profiles_username_unique_idx
  ON public.profiles (username)
  WHERE username IS NOT NULL;

REVOKE EXECUTE ON FUNCTION public.normalize_profile_username() FROM PUBLIC, anon, authenticated;
