-- Private Family Groups.  A memory owner may grant an entire memory map to
-- one or more groups; membership is always checked by the database and API.

-- Expand the legacy username rule to the canonical public identifier format.
ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_username_format_check;
ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_username_format_check
  CHECK (username IS NULL OR username ~ '^[a-z0-9_]{3,30}$');

CREATE TABLE IF NOT EXISTS public.groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK (char_length(btrim(name)) BETWEEN 1 AND 100),
  description TEXT CHECK (description IS NULL OR char_length(description) <= 1000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.group_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES public.groups(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.memory_permissions (
  memory_owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  group_id UUID NOT NULL REFERENCES public.groups(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (memory_owner_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_groups_owner_id ON public.groups(owner_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON public.group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON public.group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_permissions_owner_id ON public.memory_permissions(memory_owner_id);
CREATE INDEX IF NOT EXISTS idx_memory_permissions_group_id ON public.memory_permissions(group_id);

-- Stop a client (or accidental server bug) from attaching a different
-- person's archive to a group they do not own, or assigning a fake owner.
CREATE OR REPLACE FUNCTION public.enforce_group_member_role()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  expected_owner UUID;
BEGIN
  SELECT owner_id INTO expected_owner FROM public.groups WHERE id = NEW.group_id;
  IF expected_owner IS NULL THEN
    RAISE EXCEPTION 'Group does not exist';
  END IF;
  IF NEW.role = 'owner' AND NEW.user_id <> expected_owner THEN
    RAISE EXCEPTION 'Only the group owner may have the owner role';
  END IF;
  IF NEW.role = 'member' AND NEW.user_id = expected_owner THEN
    RAISE EXCEPTION 'The group owner must retain the owner role';
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.enforce_memory_permission_owner()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.groups WHERE id = NEW.group_id AND owner_id = NEW.memory_owner_id
  ) THEN
    RAISE EXCEPTION 'A group may only share its owner''s memories';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_group_member_role_before_write ON public.group_members;
CREATE TRIGGER enforce_group_member_role_before_write
  BEFORE INSERT OR UPDATE OF group_id, user_id, role ON public.group_members
  FOR EACH ROW EXECUTE FUNCTION public.enforce_group_member_role();
DROP TRIGGER IF EXISTS enforce_memory_permission_owner_before_write ON public.memory_permissions;
CREATE TRIGGER enforce_memory_permission_owner_before_write
  BEFORE INSERT OR UPDATE OF memory_owner_id, group_id ON public.memory_permissions
  FOR EACH ROW EXECUTE FUNCTION public.enforce_memory_permission_owner();

ALTER TABLE public.groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_permissions ENABLE ROW LEVEL SECURITY;

-- A policy that reads its own RLS-protected table recurses in PostgreSQL.
-- This narrow helper reads only the caller's own membership and is used solely
-- by the policies below.
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO authenticated;
-- Earlier development deployments used this helper in public. The private
-- version below replaces it, so remove the exposed duplicate if present.
DROP FUNCTION IF EXISTS public.current_user_is_group_member(UUID);
CREATE OR REPLACE FUNCTION private.current_user_is_group_member(target_group_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.group_members
    WHERE group_id = target_group_id AND user_id = (select auth.uid())
  );
$$;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.groups TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.group_members TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.memory_permissions TO authenticated;
GRANT SELECT ON public.memories TO authenticated;

DROP POLICY IF EXISTS group_members_can_view_groups ON public.groups;
CREATE POLICY group_members_can_view_groups ON public.groups
  FOR SELECT TO authenticated
  USING (owner_id = (select auth.uid()) OR (select private.current_user_is_group_member(id)));
DROP POLICY IF EXISTS users_can_create_owned_groups ON public.groups;
CREATE POLICY users_can_create_owned_groups ON public.groups
  FOR INSERT TO authenticated WITH CHECK (owner_id = (select auth.uid()));
DROP POLICY IF EXISTS owners_can_update_groups ON public.groups;
CREATE POLICY owners_can_update_groups ON public.groups
  FOR UPDATE TO authenticated USING (owner_id = (select auth.uid())) WITH CHECK (owner_id = (select auth.uid()));
DROP POLICY IF EXISTS owners_can_delete_groups ON public.groups;
CREATE POLICY owners_can_delete_groups ON public.groups
  FOR DELETE TO authenticated USING (owner_id = (select auth.uid()));

DROP POLICY IF EXISTS group_members_can_view_members ON public.group_members;
CREATE POLICY group_members_can_view_members ON public.group_members
  FOR SELECT TO authenticated USING ((select private.current_user_is_group_member(group_id)));
DROP POLICY IF EXISTS owners_can_add_members ON public.group_members;
CREATE POLICY owners_can_add_members ON public.group_members
  FOR INSERT TO authenticated WITH CHECK (
    EXISTS (SELECT 1 FROM public.groups g WHERE g.id = group_members.group_id AND g.owner_id = (select auth.uid()))
    OR (user_id = (select auth.uid()) AND role = 'owner' AND EXISTS (
      SELECT 1 FROM public.groups g WHERE g.id = group_members.group_id AND g.owner_id = (select auth.uid())
    ))
  );
DROP POLICY IF EXISTS owners_or_members_can_remove_members ON public.group_members;
CREATE POLICY owners_or_members_can_remove_members ON public.group_members
  FOR DELETE TO authenticated USING (
    (user_id = (select auth.uid()) AND role = 'member')
    OR EXISTS (SELECT 1 FROM public.groups g WHERE g.id = group_members.group_id AND g.owner_id = (select auth.uid()))
  );

DROP POLICY IF EXISTS group_members_can_view_memory_permissions ON public.memory_permissions;
CREATE POLICY group_members_can_view_memory_permissions ON public.memory_permissions
  FOR SELECT TO authenticated USING (
    memory_owner_id = (select auth.uid()) OR (select private.current_user_is_group_member(group_id))
  );
DROP POLICY IF EXISTS owners_can_manage_memory_permissions ON public.memory_permissions;
CREATE POLICY owners_can_manage_memory_permissions ON public.memory_permissions
  FOR ALL TO authenticated USING (memory_owner_id = (select auth.uid()))
  WITH CHECK (memory_owner_id = (select auth.uid()));

-- Existing policy keeps an owner's full control.  This additive SELECT policy
-- grants read-only access only when a valid group permission and membership
-- exist; it never permits update, insert, or delete of someone else's memory.
DROP POLICY IF EXISTS group_members_can_read_shared_memories ON public.memories;
CREATE POLICY group_members_can_read_shared_memories ON public.memories
  FOR SELECT TO authenticated USING (
    user_id = (select auth.uid()) OR EXISTS (
      SELECT 1
      FROM public.memory_permissions mp
      WHERE mp.memory_owner_id = memories.user_id AND (select private.current_user_is_group_member(mp.group_id))
    )
  );

REVOKE EXECUTE ON FUNCTION public.enforce_group_member_role() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.enforce_memory_permission_owner() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION private.current_user_is_group_member(UUID) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.current_user_is_group_member(UUID) TO authenticated;
