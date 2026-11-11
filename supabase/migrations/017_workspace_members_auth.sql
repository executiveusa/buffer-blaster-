-- 017_workspace_members_auth.sql (live application requires a separate verified migration step)
-- Per-user human identities via Supabase Auth, replacing the shared DEMO_PASSWORD session.
-- Roles: owner (everything), approver (decide approvals, manage agent tokens), operator (plan/run with approved=true), viewer (read).

CREATE TABLE IF NOT EXISTS buffer_blaster.workspace_members (
  workspace_id uuid NOT NULL REFERENCES buffer_blaster.workspaces(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('owner','approver','operator','viewer')),
  invited_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, user_id)
);
CREATE INDEX IF NOT EXISTS workspace_members_user_idx ON buffer_blaster.workspace_members (user_id);

-- Every workspace keeps at least one owner.
CREATE OR REPLACE FUNCTION buffer_blaster.keep_one_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- The guard fires on owner DELETE, owner demotion, and on moving an
  -- owner's membership to another workspace (role unchanged): all three
  -- remove an owner from OLD.workspace_id.
  IF (TG_OP = 'DELETE' AND OLD.role = 'owner')
     OR (TG_OP = 'UPDATE' AND OLD.role = 'owner'
         AND (NEW.role <> 'owner' OR NEW.workspace_id <> OLD.workspace_id)) THEN
    -- Workspace deletion cascades member rows; the guard must not block that.
    IF NOT EXISTS (SELECT 1 FROM buffer_blaster.workspaces WHERE id = OLD.workspace_id) THEN
      RETURN COALESCE(NEW, OLD);
    END IF;
    -- Serialize owner-removal decisions per workspace. Without this, two
    -- concurrent transactions can each see the *other* owner still present
    -- (snapshot isolation) and both commit, leaving zero owners.
    PERFORM pg_advisory_xact_lock(hashtext(OLD.workspace_id::text));
    IF NOT EXISTS (SELECT 1 FROM buffer_blaster.workspace_members
                   WHERE workspace_id = OLD.workspace_id AND role = 'owner' AND user_id <> OLD.user_id) THEN
      RAISE EXCEPTION 'workspace must keep at least one owner';
    END IF;
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
DROP TRIGGER IF EXISTS workspace_members_keep_owner ON buffer_blaster.workspace_members;
CREATE TRIGGER workspace_members_keep_owner BEFORE UPDATE OR DELETE ON buffer_blaster.workspace_members
  FOR EACH ROW EXECUTE FUNCTION buffer_blaster.keep_one_owner();

-- Membership helper for RLS (SECURITY DEFINER avoids recursive policy checks).
CREATE OR REPLACE FUNCTION buffer_blaster.member_role(ws uuid) RETURNS text
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path = buffer_blaster, pg_temp AS $$
  SELECT role FROM buffer_blaster.workspace_members WHERE workspace_id = ws AND user_id = auth.uid()
$$;
REVOKE ALL ON FUNCTION buffer_blaster.member_role(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION buffer_blaster.member_role(uuid) TO authenticated, service_role;

ALTER TABLE buffer_blaster.workspace_members ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS members_read_own_workspace ON buffer_blaster.workspace_members;
CREATE POLICY members_read_own_workspace ON buffer_blaster.workspace_members
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IS NOT NULL);

-- Humans read audit rows for their workspace; all writes stay service-role (API).
DROP POLICY IF EXISTS approvals_read_members ON buffer_blaster.agent_approvals;
CREATE POLICY approvals_read_members ON buffer_blaster.agent_approvals
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IS NOT NULL);
DROP POLICY IF EXISTS tokens_read_approvers ON buffer_blaster.agent_tokens;
CREATE POLICY tokens_read_approvers ON buffer_blaster.agent_tokens
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IN ('owner','approver'));
DROP POLICY IF EXISTS releases_read_members ON buffer_blaster.wallet_reservation_releases;
CREATE POLICY releases_read_members ON buffer_blaster.wallet_reservation_releases
  FOR SELECT TO authenticated USING (buffer_blaster.member_role(workspace_id) IS NOT NULL);

GRANT USAGE ON SCHEMA buffer_blaster TO authenticated, service_role;
GRANT SELECT ON buffer_blaster.workspace_members, buffer_blaster.agent_approvals,
  buffer_blaster.agent_tokens, buffer_blaster.wallet_reservation_releases TO authenticated;
GRANT ALL PRIVILEGES ON buffer_blaster.workspace_members TO postgres, service_role;
