# POSTATEES_DEPLOY.md — Archived legacy runbook

Do **not** execute the former contents of this file. That deployment path is no
longer part of Buffer Blaster's production architecture.

The old runbook was retired by the full-stack wiring audit because it depended
on direct-IP HTTP traffic, a known operator password, obsolete Stavarai/Postatees
service names, manual secret discovery, and a separate database/deployment plane.
Those behaviors conflict with current security, canonical-state, and deployment
contracts.

## Current production path

Backend/VPS:

```bash
sudo bash scripts/selfhost/install.sh --domain api.example.com
```

Frontend/Vercel:

```bash
VERCEL_TOKEN=... scripts/selfhost/configure-vercel.sh --domain api.example.com
```

Then verify with:

```bash
bash scripts/selfhost/preflight.sh
bash scripts/selfhost/smoke.sh
```

See `README.md`, `docs/SECRETS.md`, and `docs/GEMINI_BETA_HANDOFF.md` for the
current contract. Legacy filenames under `scripts/` remain only as compatibility
entrypoints and delegate to the canonical self-host scripts.
