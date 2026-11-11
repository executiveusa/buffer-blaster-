# Footage connectors (S5)

Google Drive, OneDrive and Dropbox footage import. Tokens are encrypted at
rest with the platform AES-256-GCM core (`MASTER_ENCRYPTION_KEY`) and never
appear in any response; Dropbox Chooser stores no token at all.

## Connect (human only)

1. `GET /api/studio/footage/connect/{provider}` (execute role) or MCP
   `connect_source` (plan scope) returns a consent URL (Google/OneDrive) or
   the Chooser app key (Dropbox). Agents only ever receive the URL.
2. A human completes consent; the provider redirects to
   `POST /api/studio/footage/callback/{provider}` with code + one-time state
   (10 min TTL, single-use, workspace-bound). Agents are 403 here.
3. Tokens are encrypted and stored per workspace
   (`footage_connections`, migration 020, RLS member read, service-role
   writes).

## Import

`POST /api/studio/footage/import` (execute role) or MCP `import_footage`
(plan): `{provider, filename, idempotency_key, file_id? , link?}`. Dropbox
imports use the Chooser link; Google/OneDrive use the picked file id.

Guards, in order: SSRF (https, allowlist, public IPs only, DNS-checked,
redirect hops re-validated, auth headers never forwarded), size cap
(`FOOTAGE_IMPORT_MAX_BYTES`, default 2 GB, enforced on Content-Length AND
mid-stream), magic-byte sniff (mp4/mov/webm/avi; markup bodies rejected),
ffprobe validation when available, sha256 provenance on the asset record
(source, remote file id, picked_by, hash). Idempotent by
(workspace, idempotency_key). Imports are zero-cost transfers: no usage rows.

## Disconnect

`DELETE /api/studio/footage/connections/{provider}` (human, execute role).
Google: upstream revoke + local delete. OneDrive: local delete (Graph has no
revoke endpoint). Dropbox: no-op, nothing is stored.

## Env

`GOOGLE_OAUTH_CLIENT_ID/SECRET`, `ONEDRIVE_CLIENT_ID/SECRET` (secrets),
`DROPBOX_APP_KEY` (public chooser key), `FOOTAGE_OAUTH_REDIRECT_BASE`,
`FOOTAGE_IMPORT_MAX_BYTES`, `FOOTAGE_IMPORT_ALLOWED_HOSTS`.

## r2: picker consent is enforced, not assumed

- Humans register picks via `POST /api/studio/footage/picked/{provider}`
  (human-only; agents 403). Google/OneDrive register the picker file_id;
  Dropbox registers the chooser link.
- `import_footage` refuses anything not registered in this workspace
  (`file_not_consented`) before any provider call.
- `list_footage` / `GET /{provider}/files` show only registered picks. There
  is no whole-drive listing for any role.
- OAuth: state binds provider + workspace + initiating actor (single-use);
  PKCE S256 on both Google and OneDrive (see FOOTAGE_VENDOR_VERIFICATION.md).
- ffprobe is REQUIRED on the host: imports fail closed with an
  operator-visible `ffprobe_unavailable` when the binary is missing.
- Downloads pin the connect to the DNS-validated IP with TLS SNI/Host on the
  real hostname (rebind defense); every redirect hop re-validates and re-pins.
- One in-flight import per idempotency key (`import_in_progress`), disk
  headroom checked (cap + 512 MB) before download.
- Mirror write/revoke failures are logged, surfaced (`mirror: backlogged`)
  and durably backlogged at `bb:footage:mirror_backlog` for replay.
