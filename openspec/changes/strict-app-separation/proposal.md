# Change: Strict Application Separation

## Motivation
Buffer Blaster / Social Studio and downstream publishing engines (e.g. TryPost) are distinct, independent applications. Buffer Blaster must not depend on external publishing infrastructure to boot, pass preflight, report healthy, create campaigns, generate UGC prompts, render media, or enforce human review and approval gates.

## Scope
1. Refactor `api/services/publishing.py` into a provider-neutral optional interface with `DisabledPublishingProvider` as core default.
2. Clean `/api/studio/status` to report `publishing` status without requiring or hardcoding external publisher brand names.
3. Remove TryPost credentials (`TRYPOST_URL`, `TRYPOST_API_KEY`) from required core preflight checks and `.env.production.example`.
4. Update frontend client `studio-api.ts` and UI pages to treat publishing as an optional downstream integration.
5. Establish strict application boundaries in documentation (`docs/APP_BOUNDARIES.md`, `AGENTS.md`, `README.md`).
6. Update test suite to verify independent core operations.
