# BROWSER_AGENT_HANDOFF.md — Archived

This document described an obsolete Postatees/Stavarai deployment and **must not
be executed**. It previously contained direct-IP HTTP wiring, a known operator
password, filesystem secret discovery, an obsolete database namespace, and a
second deployment topology.

## Canonical Buffer Blaster deployment

Use only these current sources:

1. `EMERALD_TABLETS.md` — highest-priority governance.
2. `README.md` — current product/runtime shape.
3. `docs/SECRETS.md` — current secret contract.
4. `docs/GEMINI_BETA_HANDOFF.md` — current beta bring-up/proof sequence.
5. `scripts/selfhost/install.sh` — canonical backend/VPS installer.
6. `scripts/selfhost/configure-vercel.sh` — canonical Vercel live-mode setup.
7. `scripts/selfhost/preflight.sh` and `scripts/selfhost/smoke.sh` — verification.

## Non-negotiable replacements for the old runbook

- Product identity is **Buffer Blaster** until the owner renames it.
- Production Vercel uses `NEXT_PUBLIC_DEMO_MODE=false` and
  `NEXT_PUBLIC_PUBLIC_CONSOLE=false`.
- Browser-to-API traffic uses HTTPS; do not wire an HTTPS frontend to a plain
  HTTP VPS address.
- No committed/default production password exists. The self-host installer
  generates operator credentials locally when blank.
- Do not scan unrelated filesystem locations for service-role keys or other
  credentials.
- Canonical production state is the `buffer_blaster` schema/migration chain.
- Do not create a second Postatees/Stavarai service, schema, or deployment plane.

Historical details were intentionally removed because agent-readable stale
instructions are an active wiring/security hazard.
