-- 012_mind_model.sql
-- Consent-first cognitive model. This extends memories; it never replaces or
-- mutates the source memory record from which a cognitive observation was made.

CREATE TABLE IF NOT EXISTS mind_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
    model_status TEXT NOT NULL DEFAULT 'draft' CHECK (model_status IN ('draft', 'active', 'paused', 'revoked')),
    consent_version TEXT,
    consent_granted_at TIMESTAMPTZ,
    consent_revoked_at TIMESTAMPTZ,
    min_response_confidence NUMERIC(4,3) NOT NULL DEFAULT 0.700 CHECK (min_response_confidence BETWEEN 0 AND 1),
    summary TEXT,
    last_processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id),
    CHECK ((model_status <> 'active') OR consent_granted_at IS NOT NULL),
    CHECK (consent_revoked_at IS NULL OR model_status = 'revoked')
);

-- Every trait is a candidate until enough attributable evidence promotes it.
CREATE TABLE IF NOT EXISTS beliefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    proposition TEXT NOT NULL,
    domain TEXT,
    stance TEXT,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, proposition)
);

CREATE TABLE IF NOT EXISTS core_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    value_name TEXT NOT NULL,
    statement TEXT NOT NULL,
    priority_rank SMALLINT CHECK (priority_rank > 0),
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, value_name)
);

CREATE TABLE IF NOT EXISTS reasoning_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pattern_name TEXT NOT NULL,
    description TEXT NOT NULL,
    decision_contexts JSONB NOT NULL DEFAULT '[]'::jsonb,
    tradeoff_preferences JSONB NOT NULL DEFAULT '[]'::jsonb,
    moral_reasoning TEXT,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS decision_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pattern_name TEXT NOT NULL,
    situation_type TEXT,
    typical_approach TEXT NOT NULL,
    preferred_priorities JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_posture TEXT,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS emotional_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trigger_description TEXT NOT NULL,
    emotional_response TEXT NOT NULL,
    recovery_pattern TEXT,
    empathy_level TEXT,
    resilience_observation TEXT,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS communication_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('vocabulary', 'rhythm', 'storytelling', 'complexity', 'favorite_phrase', 'sarcasm', 'other')),
    description TEXT NOT NULL,
    examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS humor_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    humor_style TEXT NOT NULL,
    description TEXT NOT NULL,
    boundaries TEXT,
    examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS life_principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    principle TEXT NOT NULL,
    explanation TEXT NOT NULL,
    applicability JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'superseded', 'revoked')),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_observed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, principle)
);

-- A generic, auditable link avoids copying memory text into trait rows.
CREATE TABLE IF NOT EXISTS mind_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('belief', 'core_value', 'reasoning_pattern', 'decision_pattern', 'emotional_pattern', 'communication_pattern', 'humor_pattern', 'life_principle')),
    entity_id UUID NOT NULL,
    memory_id UUID REFERENCES memories(id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    supporting_excerpt TEXT NOT NULL,
    contribution NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (contribution BETWEEN 0 AND 1),
    observation_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (memory_id IS NOT NULL OR session_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS personality_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('belief', 'core_value', 'reasoning_pattern', 'decision_pattern', 'emotional_pattern', 'communication_pattern', 'humor_pattern', 'life_principle')),
    entity_id UUID NOT NULL,
    period_start DATE,
    period_end DATE,
    snapshot JSONB NOT NULL,
    change_summary TEXT NOT NULL,
    confidence_score NUMERIC(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start)
);

CREATE TABLE IF NOT EXISTS confidence_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    score NUMERIC(4,3) NOT NULL CHECK (score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    supporting_conversation_count INTEGER NOT NULL DEFAULT 0 CHECK (supporting_conversation_count >= 0),
    first_observed_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    calculation_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_mind_profiles_user_subject ON mind_profiles(user_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_beliefs_profile_status ON beliefs(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_core_values_profile_status ON core_values(mind_profile_id, status, priority_rank);
CREATE INDEX IF NOT EXISTS idx_reasoning_patterns_profile_status ON reasoning_patterns(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_decision_patterns_profile_status ON decision_patterns(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_emotional_patterns_profile_status ON emotional_patterns(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_communication_patterns_profile_status ON communication_patterns(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_humor_patterns_profile_status ON humor_patterns(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_life_principles_profile_status ON life_principles(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_mind_evidence_entity ON mind_evidence(mind_profile_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_mind_evidence_memory ON mind_evidence(memory_id) WHERE memory_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_personality_timeline_profile_entity ON personality_timeline(mind_profile_id, entity_type, entity_id, period_start);
CREATE INDEX IF NOT EXISTS idx_confidence_metrics_profile_entity ON confidence_metrics(mind_profile_id, entity_type, entity_id);

CREATE OR REPLACE FUNCTION public.enforce_mind_model_ownership()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF TG_TABLE_NAME = 'mind_profiles' AND NEW.subject_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.subjects WHERE id = NEW.subject_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Mind profile subject must be owned by the same user';
  END IF;

  IF TG_TABLE_NAME = 'mind_evidence' AND NEW.memory_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.memories WHERE id = NEW.memory_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Mind evidence memory must be owned by the same user';
  END IF;

  IF TG_TABLE_NAME = 'mind_evidence' AND NEW.session_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.sessions WHERE id = NEW.session_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Mind evidence session must be owned by the same user';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS enforce_mind_profile_ownership ON public.mind_profiles;
CREATE TRIGGER enforce_mind_profile_ownership BEFORE INSERT OR UPDATE ON public.mind_profiles
FOR EACH ROW EXECUTE FUNCTION public.enforce_mind_model_ownership();
DROP TRIGGER IF EXISTS enforce_mind_evidence_ownership ON public.mind_evidence;
CREATE TRIGGER enforce_mind_evidence_ownership BEFORE INSERT OR UPDATE ON public.mind_evidence
FOR EACH ROW EXECUTE FUNCTION public.enforce_mind_model_ownership();

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'mind_profiles', 'beliefs', 'core_values', 'reasoning_patterns',
    'decision_patterns', 'emotional_patterns', 'communication_patterns',
    'humor_patterns', 'life_principles', 'mind_evidence',
    'personality_timeline', 'confidence_metrics'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS set_updated_at ON public.%I', table_name);
    EXECUTE format('CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()', table_name);
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS mind_owner_isolation ON public.%I', table_name);
    EXECUTE format('CREATE POLICY mind_owner_isolation ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)', table_name);
  END LOOP;
END $$;

COMMENT ON TABLE mind_profiles IS 'Consent-gated root of a subject cognitive model. Family access is mediated by the authorised backend, never direct client-table access.';
COMMENT ON TABLE mind_evidence IS 'Immutable attribution from a Mind Model claim to an owned source memory or session.';
COMMENT ON TABLE confidence_metrics IS 'Versioned confidence inputs used to decide whether a trait may influence a generated response.';
