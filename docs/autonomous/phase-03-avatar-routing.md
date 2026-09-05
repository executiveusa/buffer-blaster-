# Phase 03 — Creator/avatar routing + cost control

- [x] Inventory current Fal model routing, wallet reservation and UGC character/reference-image code.
- [x] Study HeyGem, OmniAvatar, EchoMimic and LivePortrait as optional provider patterns; do not claim/install them unless runtime requirements are proven.
- [x] Add/finish a provider capability registry: talking creator, image-to-video, text-to-video, lip-sync, local/self-hosted eligibility, estimated cost class, health state.
- [x] Make routing server-owned and cost-aware; browser/agent may request capability but cannot raise wallet/budget ceilings.
- [x] Keep provider/model selection configurable rather than hardcoded.
- [x] Add a safe dry-run plan endpoint/tool that returns chosen capability/provider plus estimated cost before paid execution.
- [x] Add tests for provider fallback, unavailable provider, insufficient budget, approval requirement and idempotent receipts.

Exit: agents can request a UGC capability and receive a governed costed plan without gaining spend authority.

Machine evidence is implemented on branch `autofinish/phase-03-avatar-routing`; merge remains contingent on the repository CI suites passing for the final branch head.
