# Phase 03 — Creator/avatar routing + cost control

- [ ] Inventory current Fal model routing, wallet reservation and UGC character/reference-image code.
- [ ] Study HeyGem, OmniAvatar, EchoMimic and LivePortrait as optional provider patterns; do not claim/install them unless runtime requirements are proven.
- [ ] Add/finish a provider capability registry: talking creator, image-to-video, text-to-video, lip-sync, local/self-hosted eligibility, estimated cost class, health state.
- [ ] Make routing server-owned and cost-aware; browser/agent may request capability but cannot raise wallet/budget ceilings.
- [ ] Keep provider/model selection configurable rather than hardcoded.
- [ ] Add a safe dry-run plan endpoint/tool that returns chosen capability/provider plus estimated cost before paid execution.
- [ ] Add tests for provider fallback, unavailable provider, insufficient budget, approval requirement and idempotent receipts.

Exit: agents can request a UGC capability and receive a governed costed plan without gaining spend authority.