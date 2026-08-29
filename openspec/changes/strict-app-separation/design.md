# Design: Strict Application Separation

## Architecture
- **Buffer Blaster Core**: Owns campaigns, UGC, scoring, prompt compilation, media generation, human approval gates, dedicated Redis, and dedicated Supabase data scope.
- **Publishing Boundary**: Optional downstream integration. Default provider is `DisabledPublishingProvider`, returning `enabled: false, required_for_core: false`.
- **Preflight & Smoke**: Preflight verifies Buffer Blaster core credentials (`REDIS_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, `FAL_KEY`, etc.) without gating on downstream publishing.
