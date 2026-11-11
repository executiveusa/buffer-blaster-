# Agent access: tokens, approvals, refunds

Buffer Blaster is usable by AI agents over MCP (`POST /api/mcp`, or stdio via
`python -m cli.mcp_stdio`), REST (`/api/studio/*`, `/api/agent/*`), a Claude
Code plugin (`plugins/claude/`) and a ChatGPT Action (`plugins/chatgpt/`).

## Identities

| Identity | How | Can plan | Can spend / publish | Can approve |
|---|---|---|---|---|
| Human operator | `BLASTER_API_KEY` or console session | yes | yes, with `approved: true` | yes |
| Agent | scoped `bba_…` token | with `plan` | only with a human-issued `approval_id` | **never** |

Agent tokens are default-deny. They are rejected on wallet creation, billing
activation, the money loop, settings/admin, and token management.

## Scopes

`read` (status, jobs, wallets, approvals, usage summary via `get_usage_summary`), `plan` (no-spend planning and
estimates), `render` (request/use render approvals), `publish` (request/use
publish approvals). `tools/list` only shows tools the token can call.

## Token lifecycle (human only)

```
POST   /api/agent/tokens          {"name": "claude-code", "scopes": ["read","plan","render"], "ttl_days": 30}
GET    /api/agent/tokens          list (never shows secrets)
DELETE /api/agent/tokens/{id}     revoke (effective immediately)
```
The plaintext token is returned once. Only its SHA-256 is stored (Redis);
Supabase keeps metadata only (migration 016).

## Render flow for agents

1. `whoami` → confirm scopes.
2. `estimate_ugc_ad_factory` → exact server price, no spend.
3. `request_render_approval` (brief + `wallet_id`) → `approval_id`, status `pending`.
   The cost ceiling is set by the server, not the agent.
4. A human approves: `POST /api/agent/approvals/{id}/decision {"decision":"approved"}`.
5. `execute_ugc_ad_factory` with the identical brief, same wallet, new
   `idempotency_key`, and `approval_id`.

Approvals are bound to a hash of the exact brief + wallet, expire after 24 h,
and are consumed once. A changed brief returns `approval_payload_mismatch`
without consuming the approval. If preflight blocks the run before any
reservation (e.g. storage not configured), the approval is restored.

Publishing is the same with `request_publish_approval` and `schedule_social_drop`.

## Refunds

Whenever no final ad is stored and returned, the reservation is refunded in
full (credits and provider budget) exactly once per `(wallet_id,
idempotency_key)`. The response carries `refunded: true` and a `release`
object with `provider_cost_incurred_cents` (clips the provider completed),
recorded separately so platform loss is visible. A reused idempotency key
returns `idempotency_key_already_used` and never runs twice.

## Error codes agents should handle

`human_approval_required`, `approval_not_granted`, `approval_already_used`,
`approval_payload_mismatch`, `approval_expired`, `estimate_exceeds_approved_cost`,
`scope_required`, `idempotency_key_already_used`, `wallet_not_found`,
`provider_budget_exceeded`, `ad_credits_exhausted`, `media_provider_not_configured`,
`asset_storage_not_configured`, `ffmpeg_not_available`.

## Rate limiting behind proxies

Set `TRUSTED_PROXY_IPS` to the Next.js server / Caddy address as seen by the
API. Only then is `X-Forwarded-For` used, and only its right-most untrusted hop.

## MCP tool index

Every tool, its scope, and what it does. `tools/list` shows only what the token can call.

| Tool | Scope | What it does |
|---|---|---|
| `get_pricing` | read | Return configured package economics and the standard generation cost ceiling |
| `get_creative_job` | read | Get one canonical creative-job receipt by id |
| `get_usage_wallet` | read | Get the remaining generation allowance, provider-cost budget, state and expiration for a server-owned wallet |
| `get_repurpose_plan` | read | Read one canonical repurpose-plan receipt from the creative-job ledger |
| `get_shopify_product_context` | read | Read one Shopify product-context receipt inside the configured workspace |
| `get_approval` | read | Read one approval and its status (pending, approved, rejected, consumed) |
| `list_approvals` | read | List approvals in this workspace, optionally by status |
| `create_identity` | plan | Save a character, product or location as a named set of reference photos (no training) |
| `list_identities` | read | List saved characters, products and locations with consistency readiness |
| `compile_shot_prompt` | plan | Build a shot prompt from an Identity Block (static look only) and a Motion Block (camera/action only) |
| `preflight_shot` | plan | List every reason a paid video call would be wasted (no approved hero frame, scene over 15 s, unsupported duration/ratio, model without image input, prompt split violations, take limit) before any spend |
| `list_recipes` | read | List UGC ad recipes (testimonial, unboxing, product hero, problem/solution, before/after, try-on) |
| `get_usage_summary` | read | Read the append-only spend ledger grouped by day, model, job or agent; estimated and actual cents are never mixed |
| `transcribe_footage` | plan | Transcribe one stored asset (self-hosted faster-whisper, zero fee): cues <=2 lines/<=42 chars, SRT+VTT. Cached by sha256; bounded duration/size/concurrency |
| `burn_captions` | plan | Burn cached captions into a NEW asset (brand style, 9:16 lower-third safe); original never modified |
| `get_captions` | read | Read the cached transcript/cues/SRT/VTT for an asset; not_transcribed until transcribe_footage ran |
| `connect_source` | plan | Get a footage-source consent URL (Google Drive / OneDrive) or the Dropbox Chooser app key. Returns the consent URL only; a human completes OAuth and tokens stay encrypted server-side |
| `list_footage` | read | Connection status and only the files a human picker-consented in this workspace. No whole-drive browse; never returns token material |
| `import_footage` | plan | Import one picked footage file into the asset store (SSRF allowlist, 2 GB cap, MIME sniff, sha256 provenance); zero-cost transfer, writes no usage rows |
| `analyze_footage` | plan | Bounded agent vision on one stored asset (1 frame/2s, max 24 frames 512px): scenes, hooks, product visibility, quality flags, suggested cuts. PAID: configured vendor pricing + per-frame tokens required, S4 cap hold pre-call, cached by sha256. |
| `get_footage_analysis` | read | Cached vision analysis for an asset; `not_analyzed` until analyze_footage runs. No recompute. |
