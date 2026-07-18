CREATE TABLE IF NOT EXISTS mind_model_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_memory_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    model JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mind_model_snapshots_profile_created ON mind_model_snapshots(mind_profile_id, created_at DESC);
ALTER TABLE mind_model_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS mind_snapshot_owner_isolation ON mind_model_snapshots;
CREATE POLICY mind_snapshot_owner_isolation ON mind_model_snapshots FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP TRIGGER IF EXISTS set_updated_at ON mind_model_snapshots;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON mind_model_snapshots FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
