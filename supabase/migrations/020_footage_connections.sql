-- 020_footage_connections.sql
-- S5: footage source connectors (Google Drive, OneDrive). Dropbox Chooser is
-- client-side and stores nothing. Token columns hold AES-256-GCM ciphertext
-- produced inside the API process (native core, MASTER_ENCRYPTION_KEY);
-- plaintext tokens never reach the database, the browser, or agent responses.
-- Writes and revokes are service-role only (API); members read status rows
-- for their own workspace through RLS.

CREATE TABLE IF NOT EXISTS buffer_blaster.footage_connections (
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  provider text NOT NULL CHECK (provider IN ('google','onedrive')),
  status text NOT NULL DEFAULT 'connected' CHECK (status IN ('connected','revoked')),
  token_ciphertext text,            -- AES-256-GCM ciphertext only, never plaintext
  refresh_ciphertext text,          -- AES-256-GCM ciphertext only, never plaintext
  scopes text[] NOT NULL DEFAULT '{}',
  expires_at timestamptz,
  connected_by text NOT NULL,       -- user:<uuid> | api-key
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, provider)
);

ALTER TABLE buffer_blaster.footage_connections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS footage_connections_read_members ON buffer_blaster.footage_connections;
CREATE POLICY footage_connections_read_members ON buffer_blaster.footage_connections
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IS NOT NULL);

GRANT SELECT ON buffer_blaster.footage_connections TO authenticated;
GRANT ALL PRIVILEGES ON buffer_blaster.footage_connections TO postgres, service_role;

COMMENT ON TABLE buffer_blaster.footage_connections IS 'S5 footage connector state per workspace. Dropbox Chooser stores nothing here.';
COMMENT ON COLUMN buffer_blaster.footage_connections.token_ciphertext IS 'AES-256-GCM ciphertext from the API core; plaintext tokens never leave the API process.';
COMMENT ON COLUMN buffer_blaster.footage_connections.refresh_ciphertext IS 'AES-256-GCM ciphertext from the API core; plaintext tokens never leave the API process.';
