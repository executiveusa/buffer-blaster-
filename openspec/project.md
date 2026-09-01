# OpenSpec — Buffer Blaster Project Context

## Project

**Buffer Blaster** is a standalone AI content/UGC operations application for
proof-first social and paid-media workflows. Repository:
`https://github.com/executiveusa/buffer-blaster-.git`.

Buffer Blaster is the canonical product name until an explicit rename is
approved.

## Source-of-truth precedence

`EMERALD_TABLETS.md` → `AGENTS.md` → accepted OpenSpec → ICM stage evidence →
implementation preference.

Do not use old Stavarai/Postatees handoffs as architecture instructions.

## Current operating model

- One operator-facing application: **Buffer Blaster**.
- No committed/default production password. Operator/API credentials are runtime
  configuration and self-host installs generate app-owned values when blank.
- Demo mode is local/seeded. Production must use `NEXT_PUBLIC_DEMO_MODE=false`
  and `NEXT_PUBLIC_PUBLIC_CONSOLE=false`.
- Frontend: Next.js under `frontend/`.
- Backend: FastAPI under `api/`.
- Canonical production ledger: Supabase schema `buffer_blaster`.
- Rust hot-path code is optional; the Python fallback shares the runtime contract.
- Publishing and paid-media mutation require explicit human approval.
- Provider/model identifiers remain environment-driven.

## Canonical deployment

- Backend/VPS: `scripts/selfhost/install.sh`
- Vercel frontend: `scripts/selfhost/configure-vercel.sh`
- Verification: `scripts/selfhost/preflight.sh` and `scripts/selfhost/smoke.sh`
- Secret contract: `docs/SECRETS.md`

Legacy deployment filenames may exist only as wrappers to these canonical paths.

## Current proof-first money loop

Implemented:

- experiment/variant/attribution ledger;
- Shopify signed webhook attribution;
- deterministic PASS / HOLD / ITERATE / KILL evaluation;
- Meta/TikTok campaign-container adapters and metric ingestion;
- hourly self-hosted worker;
- Hermes result contract.

Current provider limitation is explicit: Meta/TikTok are
`campaign_container_only` and `delivery_ready=false` until full provider
creative + ad-set/ad-group + ad creation and read-back proof are implemented.

Shopify paid-order revenue is attributed, but full/partial refund adjustments
must be implemented before net-ROAS claims.

## How to propose change

1. Inspect existing implementation and current tests first.
2. Create/update `openspec/changes/<change-id>/` with proposal, design, tasks and
   spec deltas where the change is material.
3. Obtain owner acceptance where required by governance.
4. Write the failing regression test first.
5. Implement the smallest bounded repair.
6. Record rollback evidence before destructive/deploy operations.
7. Open one PR and require repository CI plus independent review evidence before
   merge.
