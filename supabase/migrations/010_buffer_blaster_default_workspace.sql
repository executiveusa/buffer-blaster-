-- 010_buffer_blaster_default_workspace.sql
-- Deterministic single-operator workspace used by the production examples.
-- Additive/idempotent. Operators may create additional workspaces later, but
-- this row ensures a fresh deployment can write canonical state immediately.

INSERT INTO buffer_blaster.workspaces (id, slug, name)
VALUES (
  '00000000-0000-0000-0000-000000000001'::uuid,
  'default',
  'Social Studio'
)
ON CONFLICT (id) DO UPDATE SET
  slug = EXCLUDED.slug,
  name = EXCLUDED.name,
  updated_at = now();
