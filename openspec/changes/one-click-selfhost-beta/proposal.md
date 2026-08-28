# Change: One-click self-hosted beta

## Objective

Make the existing production architecture reproducible on a clean Linux VPS without embedding third-party credentials in Git or weakening the Social Studio publishing approval gate.

## Scope

- production Docker image for FastAPI
- Docker Compose with Caddy TLS edge
- one-click Debian/Ubuntu installer
- private production env contract and preflight/smoke commands
- Vercel live-mode configuration helper
- Gemini zero-context production handoff
- additive Supabase indexes for the hot campaign/creative/approval/publish path

## Out of scope

- inventing or committing provider credentials
- auto-publishing social content
- vendoring/forking TryPost into this proprietary repository
- destructive database changes
- moving the Vercel frontend onto the VPS

## Acceptance

1. Existing API/frontend tests stay green.
2. Self-host packaging tests stay green.
3. Docker backend runs as a non-root user and is not directly bound to a public host port.
4. Caddy terminates HTTPS.
5. Install script generates app-owned secrets locally and never prints them.
6. Vercel helper writes only public live-mode frontend values.
7. Supabase migration is additive and scoped only to `buffer_blaster`.
8. `approved=false` remains fail-closed at the publishing boundary.
