# Vision analysis (S6)

Bounded agent vision over stored footage. PAID provider call; every run is
estimated, held against S4 caps, and ledgered (kind `vision`).

- Sampling: 1 frame per 2 s, max 24 frames, 512 px long edge, JPEG
  (`VISION_MAX_SECONDS` default 600, `VISION_MAX_BYTES` default 250 MB;
  ffprobe/ffmpeg missing FAILS CLOSED, operator-visible).
- Model: `OPENROUTER_VISION_MODEL` + `OPENROUTER_API_KEY`. Reasoning level
  resolves from S4 settings (step `vision`, `{"reasoning": {"effort": ...}}`).
- Transcript context comes from the S7 captions cache only (never
  recomputed here).
- Pricing gate (pre-call, fail closed): BOTH
  `LLM_PRICE_OPENROUTER_{MODEL}_IN/OUT_CENTS_PER_MTOK` and
  `VISION_TOKENS_PER_FRAME_{MODEL}` must be configured from the vendor's
  live pricing/tokenization docs (record URL + retrieval date when set).
  No configured value, no call - there is no invented 'conservative'
  number.
- Estimate = frames x per-frame tokens + byte-bound text (S4 M1) + full
  max_tokens output, at configured list price. Settle: provider token
  counts priced at configured list (`priced_actual_cents`,
  `computed_from_provider_tokens`); `actual_cents` stays provider-reported
  only.
- Malformed model output: retried once, then fails; both calls are
  ledgered (they cost money) and the unused reservation settles back.
  Provider errors are NOT retried blindly (no double spend).
- Schema validated: scenes[{start,end,summary}],
  hook_candidates[{start,end,why}], product_visible[{start,end,confidence
  0..1}], quality_flags[str], suggested_cuts[{start,end,reason?}]; spans
  must lie inside the clip.
- Cached by content sha256 (`bb:vision:{sha256}`) AFTER workspace
  authorization; linked to the plan (`bb:vision:plan:{plan_id}`). Busy
  lock per asset sha, token-fenced release.
- MCP: `analyze_footage` (plan scope, write-gated), `get_footage_analysis`
  (read). REST: POST /api/studio/vision/analyze (execute role),
  GET /api/studio/vision/{asset_id}.
- Transport contract: a raise after send (timeout/disconnect) is treated
  as possibly-charged: the conservative reservation is persisted as a
  ledger row BEFORE the hold is released. `bb_unsent=True` on an exception
  is honored ONLY as our own `UnsentProven` exception, raised by our
  transport wrapper when the connection was never established
  (httpx.ConnectError); vendor/SDK exception flags are never proof and take
  the conservative path.
- Ledger-write failure FAILS CLOSED: the hold is kept (reservation stays in
  cap totals) and the run reports `usage_ledger_write_failed` with
  `hold_kept=true` AND the `hold_id`. OPERATOR RECONCILIATION REQUIRED:
  look up `hold_id` in the workspace holds hash, inspect the ACTUAL vendor
  charge for that call, record the actual cost row, then release the hold
  via release_hold - never blind cost forgiveness.
- Tests inject the transport; the suite makes NO actual paid calls.
