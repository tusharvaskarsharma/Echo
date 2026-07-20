-- The browser uses the Supabase publishable/anon client with an authenticated
-- user JWT.  PostgreSQL table grants are required in addition to RLS policies;
-- without these, PostgREST returns "permission denied for table profiles"
-- before evaluating auth.uid()-based ownership policies.
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.profiles TO authenticated;

-- Keep profile provisioning privileged for the auth.users trigger, but prevent
-- arbitrary callers from invoking it through the public RPC API.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, username, email)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data ->> 'full_name',
    NEW.raw_user_meta_data ->> 'username',
    NEW.email
  );
  RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
