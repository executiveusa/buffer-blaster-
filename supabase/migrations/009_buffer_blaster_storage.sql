-- 009_buffer_blaster_storage.sql
-- Private generated-media bucket. Service-role writes and short-lived signed
-- URLs are used by the backend; no public storage policy is granted.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'buffer-blaster-assets',
  'buffer-blaster-assets',
  false,
  262144000,
  ARRAY['video/mp4','image/jpeg','image/png','image/webp']
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;
