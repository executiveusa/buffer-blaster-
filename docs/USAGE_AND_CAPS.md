# Usage, spend ledger and caps (S4)

One append-only ledger. One row per provider call, written only by
`record_usage()`. `actual_cents` is recorded only when the provider's own
response reported a cost; estimates live in `estimated_cents` and the two are
never summed together.

## Surfaces

- REST: `GET /api/studio/usage?group_by=day|model|job|agent` (+ `&format=csv`).
  Any authenticated identity, including viewers (read-only).
- MCP: `get_usage_summary` (read scope) with optional `group_by`.
- Ledger table: `buffer_blaster.usage_events` (migration 019, append-only by
  trigger, RLS read for members, service-role writes).

## Caps (owner decision)

Caps are runtime settings, checked BEFORE any wallet reservation:

| Setting | Effect when exceeded |
|---|---|
| `USAGE_CAP_JOB_CENTS` | `job_cap_exceeded` |
| `USAGE_CAP_DAILY_CENTS` | `workspace_cap_exceeded` (window `daily`) |
| `USAGE_CAP_MONTHLY_CENTS` | `workspace_cap_exceeded` (window `monthly`) |

Unset or `0` = no cap. What counts: actual cents where the provider reported
them, else the recorded estimate - never both. A blocked run reserves nothing
and an agent's approval is restored.

## Model and reasoning controls

Resolution order: job override > workflow step > workspace > env default.
Workspace keys `MODEL_PROVIDER`, `MODEL_NAME`, `MODEL_REASONING_LEVEL`; step
overrides via `model_settings.set_step_config()`.

Configured reasoning parameter names: OpenRouter `reasoning`,
OpenAI-compatible `reasoning_effort`, Anthropic `thinking`. An unknown provider
with a requested reasoning level is rejected (`unknown_provider_reasoning_param`),
never guessed. Reasoning levels: none, minimal, low, medium, high, xhigh, max.

## Scope note

Agent spend still requires a human `approval_id` or runs under these caps;
agents never approve. See docs/AGENT_ACCESS.md.

## Caps r2: enforcement guarantees

- Write-time validation: `USAGE_CAP_*` settings accept non-negative whole
  cents only. An invalid value is rejected at write; an invalid stored value
  (legacy/bypassed data) FAILS CLOSED - paid execution blocks with
  `cap_config_invalid`, it never silently disables the cap.
- Atomic check+hold: the enforcement path is `check_and_hold()`, which moves
  the estimate into per-window held counters with atomic increments and
  rolls back on violation. Concurrent runs cannot jointly exceed a cap; a
  transient overshoot can conservatively reject a run that would have fit
  (retry-safe). `check_caps()` remains as an advisory pre-flight read only.
- Holds settle into spent via `record_usage()`; unused hold is released on
  every failure path (refund, reservation conflict, provider error).
- Unknown cost is rejected before execution: `estimate_required` on a hold
  without an estimate, `cost_unknown` on a row with neither estimated nor
  actual cents.
- LLM calls are ledgered the same way: upper-bound estimate held before the
  call, exactly one row after, with real token counts from the provider
  response. Estimates REQUIRE configured pricing: each active (provider,
  model) pair needs `LLM_PRICE_{PROVIDER}_{MODEL}_IN/OUT_CENTS_PER_MTOK` set
  from the vendor's current list price before enabling calls. A model without
  configured pricing is rejected BEFORE any provider call
  (`model_pricing_unconfigured`) - no invented "safe default" exists, because
  none is a verifiable upper bound across models, tiers and reasoning modes.
  Self-hosted Ollama records provider-known zero cost.
- Caps are an OWNER decision: the settings API rejects `USAGE_CAP_*` writes
  from operators and viewers (`403`); only the owner role can change them.
- Workspace deletion: `usage_events` references workspaces with
  `ON DELETE RESTRICT` - a workspace that has ledger rows cannot be deleted
  (append-only means no destructive cascade). Decommission by revoking access.

## Mirror durability (PostgREST)

Every row is mirrored to `buffer_blaster.usage_events`. The mirror response
status is CHECKED: a non-2xx or unreachable mirror puts the event on a durable
backlog, and while the backlog is non-empty `check_and_hold` fails closed
(`ledger_mirror_backlog`). `reconcile_mirror()` replays the backlog and
rebuilds the Redis cap totals from the mirror - this is also the recovery
path after a Redis reset (first hold after a reset reconciles inline before
admitting spend).

Host requirement (not verifiable from the repo, desk must confirm): run Redis
with AOF (`appendonly yes`, `appendfsync everysec`). Without AOF a Redis
restart can drop held/spent counters before the next mirror write.

## CSV export

`GET /api/studio/usage?format=csv` neutralizes spreadsheet formula injection:
cells starting with `= + - @` (or tab/CR) are prefixed with `'`.

## S4 r4: estimate bounds, priced actuals, hold ids, reconcile (reviewer M1-M3)

- **Proven input-token bound (M1).** Estimates use
  `estimate_input_tokens()` = UTF-8 byte length + 64 tokens of framing
  overhead. Both tokenizer families in use satisfy tokens <= bytes (byte-level
  BPE: every token consumes at least one byte; SentencePiece/unigram: every
  token consumes at least one character, and characters <= bytes in UTF-8).
  The removed `ceil(chars/4)` was not a bound: CJK (~1 token per 3-byte
  character), emoji (4 bytes, 1-3 tokens) and dense code undercounted 3-4x.
  The byte bound over-reserves for CJK; the difference is refunded at settle.
- **Priced actuals, labeled separately (M1).** When a provider reports token
  counts but no cost, `priced_actual_cents` is computed from those tokens at
  the CONFIGURED vendor list price and recorded with
  `cost_provenance='computed_from_provider_tokens'`. It is a separate column
  (migration 021); `actual_cents` stays provider-reported only and is never
  falsified. Cap settle order: provider actual -> priced actual -> the full
  reservation (unknown cost never settles below the proven bound).
- **Idempotent holds (M2).** Every hold carries a unique `hold_id` recorded
  in the workspace holds hash. `release_hold()` is one atomic Lua script:
  the decrement executes only while the hold record exists, so double or
  concurrent releases are no-ops and cannot loosen a cap.
- **Provable reconcile (M3).** `reconcile_mirror()` reads the durable mirror
  with paginated `Range` requests under `Prefer: count=exact` and asserts the
  fetched row count equals the Content-Range total (`mirror_count_mismatch`
  or `mirror_count_unknown` fail closed). During the rebuild a short-lived
  lock quiesces new holds (`check_and_hold` returns
  `ledger_rebuild_in_progress`, retry-safe); active holds are recomputed from
  the holds hash and survive the rebuild (`holds_preserved` in the result).
- Release gate: apply and re-apply migrations 016-021 in an isolated PostgreSQL
  database and check 019 append-only + RESTRICT, 020 RLS and 021 priced-actual
  constraints. This public source change does not prove live migration application.
- **Rebuild fencing and TTL renewal (M3, revision 5).** The rebuild lock is
  now 15s-TTL, token-fenced and renewed per fetched page: a slow multi-page
  rebuild that outlives one TTL renews instead of expiring mid-rewrite, and a
  stale worker that lost its token aborts before the totals rewrite
  (`rebuild_lock_lost`) instead of clobbering a live ledger. During a rebuild,
  `record_usage` settles through a guarded Lua increment that refuses while
  the lock is held (wait up to 30s); on expiry of the wait it FAILS CLOSED by
  deferring the settle to a per-workspace pending list, and the rebuild
  drains that list exactly once inside the lock, skipping any event the
  mirror read already covered (mirror is the source of truth; no double
  count). `release_hold` during a rebuild is conservative: the hold stays
  rather than loosening a cap. Crash mid-rebuild recovers on the next hold or
  reconcile via lock TTL expiry + inline rebuild. Qualified by
  tests/studio/test_usage_ledger_r5.py (6 tests: >TTL renewal, lost-token
  abort, defer+drain exactly-once with negative control, guarded mutation
  refusal, crash recovery, concurrent settle during a real rebuild).
- **Atomic rebuild commit (M3, revision 6).** Revision 5's renew-then-rewrite
  was still check-then-act: the lock could lapse between the final renewal
  and the pipeline commit. Revision 6 commits the whole rebuild (delete
  totals, every folded increment, pending-drain clear, reconciled flag) in
  ONE Lua script gated on the fencing token, and renews BEFORE each page
  fetch. A single page fetch that outlives one TTL loses the token and the
  guarded commit aborts (totals untouched) instead of clobbering a live
  ledger. Qualified by tests/studio/test_usage_ledger_r6.py (single slow
  page > TTL with a concurrent rebuild lands exactly once; token stolen in
  the check->commit gap aborts atomically with totals and flag untouched;
  negative control proves the unguarded script would have committed).
- **Deferred-settle and deferred-release queues (M3, revision 7).** The
  rebuild commit LTRIMs exactly the captured prefix of both the
  pending-settle list and the new pending-release queue: an event or
  release landing between the read and the atomic commit SURVIVES for the
  next reconcile (a DEL silently lost it = cap undercount; negative control
  in r7 tests). `release_hold` during a rebuild now QUEUES the hold id in
  the same Lua step that observes the lock (no caller retry needed; the
  queue is durable and every reconcile drains it with idempotent HDEL
  before recomputing held sums), and `check_and_hold` triggers an inline
  reconcile when the release queue is non-empty, so deferred releases are
  drained promptly. Qualified by tests/studio/test_usage_ledger_r7.py.
