-- Foreign keys used for Emmy profile ownership checks need a covering index.
CREATE INDEX IF NOT EXISTS idx_emmy_profiles_user_id
  ON public.emmy_profiles (user_id);
