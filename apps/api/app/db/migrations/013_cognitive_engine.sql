-- 013_cognitive_engine.sql
-- Cognitive Engine audit and policy layer. It stores an explainable evidence
-- ledger and response plan, never raw model chain-of-thought.

CREATE TABLE IF NOT EXISTS decision_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    policy_name TEXT NOT NULL,
    policy_kind TEXT NOT NULL CHECK (policy_kind IN ('risk_first', 'family_first', 'faith_first', 'logic_first', 'optimistic', 'cautious', 'traditional', 'pragmatic', 'custom')),
    description TEXT NOT NULL,
    applies_to JSONB NOT NULL DEFAULT '[]'::jsonb,
    priority_order JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, policy_name)
);

CREATE TABLE IF NOT EXISTS relationship_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    legacy_contact_id UUID REFERENCES legacy_contacts(id) ON DELETE SET NULL,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('self', 'child', 'grandchild', 'spouse', 'friend', 'sibling', 'parent', 'doctor', 'caregiver', 'public', 'other')),
    display_name TEXT,
    familiarity_level TEXT NOT NULL DEFAULT 'known' CHECK (familiarity_level IN ('intimate', 'known', 'formal', 'public')),
    communication_guidance JSONB NOT NULL DEFAULT '{}'::jsonb,
    disclosure_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS life_timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_id UUID REFERENCES memories(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT NOT NULL DEFAULT 'life_event',
    occurred_start DATE,
    occurred_end DATE,
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (occurred_end IS NULL OR occurred_start IS NULL OR occurred_end >= occurred_start)
);

CREATE TABLE IF NOT EXISTS cognitive_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversation_history(id) ON DELETE SET NULL,
    relationship_context_id UUID REFERENCES relationship_contexts(id) ON DELETE SET NULL,
    question_hash TEXT NOT NULL,
    intent TEXT NOT NULL CHECK (intent IN ('advice', 'memory_recall', 'opinion', 'emotional_support', 'storytelling', 'explanation', 'decision_making', 'life_lesson', 'unknown')),
    requested_time DATE,
    timeline_version_id UUID REFERENCES personality_timeline(id) ON DELETE SET NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('answered', 'uncertain', 'conflicted', 'blocked_by_consent', 'failed')),
    confidence_score NUMERIC(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    conflict_summary TEXT,
    answer_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(answer_plan) = 'object')
);

CREATE TABLE IF NOT EXISTS cognitive_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognitive_run_id UUID NOT NULL REFERENCES cognitive_runs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL CHECK (source_type IN ('memory', 'belief', 'core_value', 'reasoning_pattern', 'decision_pattern', 'emotional_pattern', 'communication_pattern', 'humor_pattern', 'life_principle', 'decision_policy', 'relationship_context', 'timeline_event', 'timeline_snapshot')),
    source_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('fact', 'value', 'belief', 'reasoning', 'relationship', 'temporal', 'conflict', 'style')),
    relevance_score NUMERIC(4,3) NOT NULL CHECK (relevance_score BETWEEN 0 AND 1),
    consent_eligible BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decision_policies_profile_status ON decision_policies(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_relationship_contexts_profile_type ON relationship_contexts(mind_profile_id, relationship_type, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_relationship_contexts_default ON relationship_contexts(mind_profile_id) WHERE is_default AND is_active;
CREATE INDEX IF NOT EXISTS idx_life_timeline_events_profile_time ON life_timeline_events(mind_profile_id, occurred_start, occurred_end);
CREATE INDEX IF NOT EXISTS idx_cognitive_runs_profile_created ON cognitive_runs(mind_profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cognitive_runs_conversation ON cognitive_runs(conversation_id) WHERE conversation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cognitive_evidence_run ON cognitive_evidence(cognitive_run_id, role, relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_cognitive_evidence_source ON cognitive_evidence(source_type, source_id);

CREATE OR REPLACE FUNCTION public.enforce_cognitive_engine_ownership()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE profile_owner UUID;
DECLARE profile_subject UUID;
BEGIN
  IF TG_TABLE_NAME = 'cognitive_evidence' THEN
    SELECT mp.user_id, mp.subject_id INTO profile_owner, profile_subject
    FROM public.cognitive_runs cr
    JOIN public.mind_profiles mp ON mp.id = cr.mind_profile_id
    WHERE cr.id = NEW.cognitive_run_id;
  ELSE
    SELECT user_id, subject_id INTO profile_owner, profile_subject FROM public.mind_profiles WHERE id = NEW.mind_profile_id;
  END IF;
  IF profile_owner IS NULL OR profile_owner <> NEW.user_id THEN
    RAISE EXCEPTION 'Cognitive Engine record must belong to its Mind Profile owner';
  END IF;

  IF TG_TABLE_NAME = 'relationship_contexts' AND NEW.legacy_contact_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.legacy_contacts WHERE id = NEW.legacy_contact_id AND subject_id = profile_subject
  ) THEN
    RAISE EXCEPTION 'Relationship context contact does not belong to the Mind Profile subject';
  END IF;

  IF TG_TABLE_NAME = 'cognitive_runs' AND NEW.relationship_context_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.relationship_contexts
    WHERE id = NEW.relationship_context_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Cognitive run relationship context must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'cognitive_runs' AND NEW.timeline_version_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.personality_timeline
    WHERE id = NEW.timeline_version_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Cognitive run timeline version must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'life_timeline_events' AND NEW.memory_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.memories WHERE id = NEW.memory_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Timeline event memory must be owned by the same user';
  END IF;

  IF TG_TABLE_NAME = 'cognitive_evidence' AND NOT EXISTS (
    SELECT 1 FROM public.cognitive_runs WHERE id = NEW.cognitive_run_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Cognitive evidence must belong to the same user as its run';
  END IF;

  IF TG_TABLE_NAME = 'cognitive_evidence' AND NEW.source_type = 'memory' AND NOT EXISTS (
    SELECT 1 FROM public.memories WHERE id = NEW.source_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Cognitive memory evidence must be owned by the same user';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_decision_policy_ownership ON public.decision_policies;
CREATE TRIGGER enforce_decision_policy_ownership BEFORE INSERT OR UPDATE ON public.decision_policies
FOR EACH ROW EXECUTE FUNCTION public.enforce_cognitive_engine_ownership();
DROP TRIGGER IF EXISTS enforce_relationship_context_ownership ON public.relationship_contexts;
CREATE TRIGGER enforce_relationship_context_ownership BEFORE INSERT OR UPDATE ON public.relationship_contexts
FOR EACH ROW EXECUTE FUNCTION public.enforce_cognitive_engine_ownership();
DROP TRIGGER IF EXISTS enforce_life_timeline_event_ownership ON public.life_timeline_events;
CREATE TRIGGER enforce_life_timeline_event_ownership BEFORE INSERT OR UPDATE ON public.life_timeline_events
FOR EACH ROW EXECUTE FUNCTION public.enforce_cognitive_engine_ownership();
DROP TRIGGER IF EXISTS enforce_cognitive_run_ownership ON public.cognitive_runs;
CREATE TRIGGER enforce_cognitive_run_ownership BEFORE INSERT OR UPDATE ON public.cognitive_runs
FOR EACH ROW EXECUTE FUNCTION public.enforce_cognitive_engine_ownership();
DROP TRIGGER IF EXISTS enforce_cognitive_evidence_ownership ON public.cognitive_evidence;
CREATE TRIGGER enforce_cognitive_evidence_ownership BEFORE INSERT OR UPDATE ON public.cognitive_evidence
FOR EACH ROW EXECUTE FUNCTION public.enforce_cognitive_engine_ownership();

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'decision_policies', 'relationship_contexts', 'life_timeline_events',
    'cognitive_runs', 'cognitive_evidence'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS set_updated_at ON public.%I', table_name);
    EXECUTE format('CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()', table_name);
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS cognitive_owner_isolation ON public.%I', table_name);
    EXECUTE format('CREATE POLICY cognitive_owner_isolation ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)', table_name);
  END LOOP;
END $$;

COMMENT ON TABLE cognitive_runs IS 'Auditable answer planning outcome. answer_plan contains a bounded response outline and citations, never hidden chain-of-thought.';
COMMENT ON TABLE cognitive_evidence IS 'The consent-filtered evidence ledger used by a Cognitive Engine run.';
