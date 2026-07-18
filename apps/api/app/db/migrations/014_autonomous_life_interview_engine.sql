-- 014_autonomous_life_interview_engine.sql
-- Voluntary, coverage-aware interview planning. Knowledge gaps represent
-- uncollected coverage only; they must never be treated as missing facts.

CREATE TABLE IF NOT EXISTS knowledge_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    domain_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    parent_domain_id UUID REFERENCES knowledge_domains(id) ON DELETE SET NULL,
    description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, domain_key)
);

CREATE TABLE IF NOT EXISTS coverage_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    knowledge_domain_id UUID NOT NULL REFERENCES knowledge_domains(id) ON DELETE CASCADE,
    coverage_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (coverage_score BETWEEN 0 AND 100),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    supporting_conversation_count INTEGER NOT NULL DEFAULT 0 CHECK (supporting_conversation_count >= 0),
    missing_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_interview_at TIMESTAMPTZ,
    priority_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (priority_score BETWEEN 0 AND 100),
    calculation_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, knowledge_domain_id)
);

CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    knowledge_domain_id UUID NOT NULL REFERENCES knowledge_domains(id) ON DELETE CASCADE,
    gap_type TEXT NOT NULL CHECK (gap_type IN ('low_coverage', 'low_confidence', 'contradiction', 'mentioned_person', 'timeline_ambiguity', 'follow_up', 'subject_requested')),
    description TEXT NOT NULL,
    priority_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (priority_score BETWEEN 0 AND 100),
    emotional_sensitivity TEXT NOT NULL DEFAULT 'normal' CHECK (emotional_sensitivity IN ('low', 'normal', 'high', 'do_not_prompt')),
    last_discussed_at TIMESTAMPTZ,
    next_eligible_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'planned', 'deferred', 'skipped', 'resolved', 'suppressed')),
    source_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interview_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_mode TEXT NOT NULL CHECK (plan_mode IN ('life_story', 'cognitive_discovery', 'verification', 'relationship_discovery', 'timeline_clarification')),
    status TEXT NOT NULL DEFAULT 'recommended' CHECK (status IN ('draft', 'recommended', 'scheduled', 'started', 'completed', 'skipped', 'expired', 'dismissed')),
    title TEXT NOT NULL,
    rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    priority_score NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (priority_score BETWEEN 0 AND 100),
    recommended_for TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    do_not_nudge_before TIMESTAMPTZ,
    emotional_readiness TEXT NOT NULL DEFAULT 'unknown' CHECK (emotional_readiness IN ('ready', 'unknown', 'gentle_only', 'defer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (expires_at IS NULL OR recommended_for IS NULL OR expires_at >= recommended_for)
);

CREATE TABLE IF NOT EXISTS follow_up_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_plan_id UUID NOT NULL REFERENCES interview_plans(id) ON DELETE CASCADE,
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    knowledge_gap_id UUID REFERENCES knowledge_gaps(id) ON DELETE SET NULL,
    strategy TEXT NOT NULL CHECK (strategy IN ('follow_up', 'reflection', 'clarification', 'deeper_why', 'memory_verification', 'relationship_discovery', 'timeline_clarification')),
    question_text TEXT NOT NULL,
    rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'offered', 'asked', 'answered', 'skipped', 'dismissed', 'expired')),
    asked_at TIMESTAMPTZ,
    answered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS verification_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    knowledge_domain_id UUID REFERENCES knowledge_domains(id) ON DELETE SET NULL,
    verification_type TEXT NOT NULL CHECK (verification_type IN ('memory_conflict', 'date_ambiguity', 'identity_ambiguity', 'trait_conflict', 'relationship_ambiguity')),
    source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    clarification_prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'planned', 'asked', 'resolved', 'deferred', 'dismissed')),
    resolution_summary TEXT,
    confidence_before NUMERIC(4,3) CHECK (confidence_before BETWEEN 0 AND 1),
    confidence_after NUMERIC(4,3) CHECK (confidence_after BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS relationship_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    relationship_type TEXT,
    relationship_strength NUMERIC(4,3) CHECK (relationship_strength BETWEEN 0 AND 1),
    confidence_score NUMERIC(4,3) NOT NULL DEFAULT 0 CHECK (confidence_score BETWEEN 0 AND 1),
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'merged', 'revoked')),
    first_mentioned_at TIMESTAMPTZ,
    last_mentioned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (mind_profile_id, normalized_name)
);

CREATE TABLE IF NOT EXISTS relationship_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_entity_id UUID NOT NULL REFERENCES relationship_entities(id) ON DELETE CASCADE,
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    memory_id UUID REFERENCES memories(id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    supporting_excerpt TEXT NOT NULL,
    shared_memory_summary TEXT,
    contribution NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (contribution BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (memory_id IS NOT NULL OR session_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS legacy_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mind_profile_id UUID NOT NULL REFERENCES mind_profiles(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    overall_score NUMERIC(5,2) NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    memory_completeness NUMERIC(5,2) NOT NULL CHECK (memory_completeness BETWEEN 0 AND 100),
    reasoning_completeness NUMERIC(5,2) NOT NULL CHECK (reasoning_completeness BETWEEN 0 AND 100),
    value_completeness NUMERIC(5,2) NOT NULL CHECK (value_completeness BETWEEN 0 AND 100),
    voice_completeness NUMERIC(5,2) NOT NULL CHECK (voice_completeness BETWEEN 0 AND 100),
    timeline_completeness NUMERIC(5,2) NOT NULL CHECK (timeline_completeness BETWEEN 0 AND 100),
    relationship_completeness NUMERIC(5,2) NOT NULL CHECK (relationship_completeness BETWEEN 0 AND 100),
    confidence_score NUMERIC(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    calculation_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_domains_profile_enabled ON knowledge_domains(mind_profile_id, is_enabled);
CREATE INDEX IF NOT EXISTS idx_coverage_scores_profile_priority ON coverage_scores(mind_profile_id, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_profile_status ON knowledge_gaps(mind_profile_id, status, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_interview_plans_profile_status ON interview_plans(mind_profile_id, status, recommended_for);
CREATE INDEX IF NOT EXISTS idx_follow_up_questions_plan_status ON follow_up_questions(interview_plan_id, status);
CREATE INDEX IF NOT EXISTS idx_verification_tasks_profile_status ON verification_tasks(mind_profile_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_relationship_entities_profile_status ON relationship_entities(mind_profile_id, status, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_relationship_evidence_entity ON relationship_evidence(relationship_entity_id, created_at);
CREATE INDEX IF NOT EXISTS idx_legacy_scores_profile_created ON legacy_scores(mind_profile_id, created_at DESC);

CREATE OR REPLACE FUNCTION public.enforce_autonomous_interview_ownership()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE profile_owner UUID;
BEGIN
  IF TG_TABLE_NAME = 'follow_up_questions' THEN
    SELECT user_id INTO profile_owner FROM public.interview_plans WHERE id = NEW.interview_plan_id;
  ELSIF TG_TABLE_NAME = 'relationship_evidence' THEN
    SELECT user_id INTO profile_owner FROM public.relationship_entities WHERE id = NEW.relationship_entity_id;
  ELSE
    SELECT user_id INTO profile_owner FROM public.mind_profiles WHERE id = NEW.mind_profile_id;
  END IF;

  IF profile_owner IS NULL OR profile_owner <> NEW.user_id THEN
    RAISE EXCEPTION 'Autonomous interview record must belong to the Mind Profile owner';
  END IF;

  IF TG_TABLE_NAME = 'coverage_scores' AND NOT EXISTS (
    SELECT 1 FROM public.knowledge_domains WHERE id = NEW.knowledge_domain_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Coverage score domain must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'knowledge_gaps' AND NOT EXISTS (
    SELECT 1 FROM public.knowledge_domains WHERE id = NEW.knowledge_domain_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Knowledge gap domain must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'follow_up_questions' AND NOT EXISTS (
    SELECT 1 FROM public.interview_plans WHERE id = NEW.interview_plan_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Follow-up question plan must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'verification_tasks' AND NEW.knowledge_domain_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.knowledge_domains WHERE id = NEW.knowledge_domain_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Verification task domain must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'relationship_evidence' AND NOT EXISTS (
    SELECT 1 FROM public.relationship_entities
    WHERE id = NEW.relationship_entity_id AND mind_profile_id = NEW.mind_profile_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Relationship evidence entity must belong to the same Mind Profile';
  END IF;

  IF TG_TABLE_NAME = 'relationship_evidence' AND NEW.memory_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.memories WHERE id = NEW.memory_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Relationship evidence memory must be owned by the same user';
  END IF;

  IF TG_TABLE_NAME = 'relationship_evidence' AND NEW.session_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.sessions WHERE id = NEW.session_id AND user_id = NEW.user_id
  ) THEN
    RAISE EXCEPTION 'Relationship evidence session must be owned by the same user';
  END IF;
  RETURN NEW;
END;
$$;

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'knowledge_domains', 'coverage_scores', 'knowledge_gaps', 'interview_plans',
    'follow_up_questions', 'verification_tasks', 'relationship_entities',
    'relationship_evidence', 'legacy_scores'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS enforce_autonomous_interview_ownership ON public.%I', table_name);
    EXECUTE format('CREATE TRIGGER enforce_autonomous_interview_ownership BEFORE INSERT OR UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.enforce_autonomous_interview_ownership()', table_name);
    EXECUTE format('DROP TRIGGER IF EXISTS set_updated_at ON public.%I', table_name);
    EXECUTE format('CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()', table_name);
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS autonomous_interview_owner_isolation ON public.%I', table_name);
    EXECUTE format('CREATE POLICY autonomous_interview_owner_isolation ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)', table_name);
  END LOOP;
END $$;

COMMENT ON TABLE knowledge_gaps IS 'Coverage gaps are interview opportunities, not assertions that an omitted event, person, or memory exists.';
COMMENT ON TABLE verification_tasks IS 'Conflicts remain attributable evidence until a voluntary clarification adds new evidence; source records are never overwritten.';
COMMENT ON TABLE legacy_scores IS 'Versioned Digital Mind Completion snapshots. A score represents collected coverage, not a measure of a person.';
