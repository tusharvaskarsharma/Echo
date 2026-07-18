-- Publish owned memory changes for the authenticated MemoryGraph client.
-- RLS remains enabled; Realtime only delivers rows permitted by the caller's
-- existing memories policy.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime'
      AND schemaname = 'public'
      AND tablename = 'memories'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.memories;
  END IF;
END $$;
