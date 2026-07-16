-- Add audio_url to sessions
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS audio_url TEXT;

-- Add time_period to memories
ALTER TABLE memories ADD COLUMN IF NOT EXISTS time_period TEXT;
