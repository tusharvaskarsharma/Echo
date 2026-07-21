-- Invitation-only Family Group membership.  A row in group_members is created
-- only by the authenticated recipient accepting a valid pending invitation.

DO $$
BEGIN
  CREATE TYPE public.group_invitation_status AS ENUM ('pending', 'accepted', 'declined', 'expired');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS public.group_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id UUID NOT NULL REFERENCES public.groups(id) ON DELETE CASCADE,
  inviter_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  invited_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status public.group_invitation_status NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  responded_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
  CHECK (inviter_id <> invited_user_id),
  CHECK (expires_at > created_at)
);

-- An expired invitation is marked before a new invite is inserted, so this
-- partial uniqueness rule prevents duplicate live invites without blocking a
-- legitimate resend after expiry or decline.
CREATE UNIQUE INDEX IF NOT EXISTS group_invitations_one_pending_per_user
  ON public.group_invitations(group_id, invited_user_id)
  WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_group_invitations_invited_status
  ON public.group_invitations(invited_user_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_group_invitations_group_status
  ON public.group_invitations(group_id, status, created_at DESC);

CREATE OR REPLACE FUNCTION public.enforce_group_invitation_transition()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF NEW.group_id <> OLD.group_id
       OR NEW.inviter_id <> OLD.inviter_id
       OR NEW.invited_user_id <> OLD.invited_user_id
       OR NEW.created_at <> OLD.created_at
       OR NEW.expires_at <> OLD.expires_at THEN
      RAISE EXCEPTION 'Invitation identity fields cannot be changed';
    END IF;
    IF OLD.status <> 'pending' THEN
      RAISE EXCEPTION 'Only pending invitations can be changed';
    END IF;
    IF NEW.status NOT IN ('accepted', 'declined', 'expired') THEN
      RAISE EXCEPTION 'Pending invitations must be accepted, declined, or expired';
    END IF;
    IF NEW.responded_at IS NULL THEN
      NEW.responded_at := now();
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_group_invitation_transition_before_write ON public.group_invitations;
CREATE TRIGGER enforce_group_invitation_transition_before_write
  BEFORE UPDATE ON public.group_invitations
  FOR EACH ROW EXECUTE FUNCTION public.enforce_group_invitation_transition();

ALTER TABLE public.group_invitations ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.group_invitations TO authenticated;

DROP POLICY IF EXISTS invitation_recipient_or_owner_can_view ON public.group_invitations;
CREATE POLICY invitation_recipient_or_owner_can_view ON public.group_invitations
  FOR SELECT TO authenticated USING (
    invited_user_id = (select auth.uid())
    OR EXISTS (
      SELECT 1 FROM public.groups g
      WHERE g.id = group_invitations.group_id AND g.owner_id = (select auth.uid())
    )
  );

DROP POLICY IF EXISTS group_owner_can_send_invitation ON public.group_invitations;
CREATE POLICY group_owner_can_send_invitation ON public.group_invitations
  FOR INSERT TO authenticated WITH CHECK (
    inviter_id = (select auth.uid())
    AND EXISTS (
      SELECT 1 FROM public.groups g
      WHERE g.id = group_invitations.group_id AND g.owner_id = (select auth.uid())
    )
  );

-- The owner may only create their own initial owner membership. A recipient
-- can become a member only after their invitation row is marked accepted.
DROP POLICY IF EXISTS invitation_acceptance_creates_membership ON public.group_members;
DROP POLICY IF EXISTS owners_can_add_members ON public.group_members;
CREATE POLICY invitation_acceptance_creates_membership ON public.group_members
  FOR INSERT TO authenticated WITH CHECK (
    (role = 'owner' AND user_id = (select auth.uid()) AND EXISTS (
      SELECT 1 FROM public.groups g
      WHERE g.id = group_members.group_id AND g.owner_id = (select auth.uid())
    ))
    OR (role = 'member' AND user_id = (select auth.uid()) AND EXISTS (
      SELECT 1 FROM public.group_invitations i
      WHERE i.group_id = group_members.group_id
        AND i.invited_user_id = (select auth.uid())
        AND i.status = 'accepted'
    ))
  );

DROP POLICY IF EXISTS recipient_can_respond_to_pending_invitation ON public.group_invitations;
CREATE POLICY recipient_can_respond_to_pending_invitation ON public.group_invitations
  FOR UPDATE TO authenticated
  USING (
    invited_user_id = (select auth.uid())
    AND status = 'pending' AND expires_at > now()
  )
  WITH CHECK (
    invited_user_id = (select auth.uid())
    AND status IN ('accepted', 'declined')
  );

DROP POLICY IF EXISTS group_owner_can_cancel_pending_invitation ON public.group_invitations;
CREATE POLICY group_owner_can_cancel_pending_invitation ON public.group_invitations
  FOR DELETE TO authenticated USING (
    status = 'pending'
    AND EXISTS (
      SELECT 1 FROM public.groups g
      WHERE g.id = group_invitations.group_id AND g.owner_id = (select auth.uid())
    )
  );

REVOKE EXECUTE ON FUNCTION public.enforce_group_invitation_transition() FROM PUBLIC, anon, authenticated;
