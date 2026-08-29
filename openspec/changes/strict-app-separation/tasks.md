# Tasks: Strict Application Separation

- [x] Refactor `api/services/publishing.py` to provider-neutral `PublishingProvider` and `DisabledPublishingProvider`.
- [x] Update `api/routers/studio.py` and `api/routers/mcp.py` to return normalized `publishing` readiness.
- [x] Remove TryPost variables from required preflight checks in `scripts/selfhost/preflight.sh`.
- [x] Update `scripts/selfhost/smoke.sh` and installer scripts.
- [x] Update frontend `src/lib/studio-api.ts` and studio views.
- [x] Enforce governance in `docs/APP_BOUNDARIES.md`, `AGENTS.md`, `README.md`.
- [x] Update and verify test suite.
