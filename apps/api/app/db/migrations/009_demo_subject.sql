-- 009_demo_subject.sql
-- Inserts a demo subject for local development to avoid foreign key violations on sessions

INSERT INTO subjects (id, full_name, email, date_of_birth)
VALUES ('00000000-0000-0000-0000-000000000000', 'Demo Subject', 'demo@example.com', '1950-01-01')
ON CONFLICT (id) DO NOTHING;
