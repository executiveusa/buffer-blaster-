-- 015_install_inquiries.sql
-- Durable public install-interest receipts. Backend service-role only.
CREATE TABLE IF NOT EXISTS buffer_blaster.install_inquiries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  email text NOT NULL CHECK (char_length(email) BETWEEN 3 AND 320),
  status text NOT NULL DEFAULT 'received' CHECK (status IN ('received','contacted','qualified','closed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS install_inquiries_workspace_created_idx
  ON buffer_blaster.install_inquiries (workspace_id, created_at DESC);
ALTER TABLE buffer_blaster.install_inquiries ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE buffer_blaster.install_inquiries IS 'Durable private install-interest receipts; service-role access only.';
