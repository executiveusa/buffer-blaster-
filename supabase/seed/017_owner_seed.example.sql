-- Seed the first Buffer Blaster owner after migration 017.
-- 1. In Supabase Auth (GoTrue), invite/create the owner's user and copy their auth.users.id.
-- 2. Replace BOTH placeholders below, then apply with the service role:
--      psql "$DATABASE_URL" -f supabase/seed/017_owner_seed.example.sql
-- Never commit a real user id; this file is a template.
\set owner_user_id 'REPLACE_WITH_AUTH_USERS_UUID'
\set workspace_id 'REPLACE_WITH_BUFFER_BLASTER_WORKSPACE_ID'

INSERT INTO buffer_blaster.workspace_members (workspace_id, user_id, role)
VALUES (:'workspace_id', :'owner_user_id', 'owner')
ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = 'owner';
