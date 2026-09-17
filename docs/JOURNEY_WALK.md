# Journey Walk — A-to-Z UGC ad truth (operator path)

Proves the operator/agent journey (REST + CLI with an operator key) actually
produces a video, or names the exact stage that breaks. Created after the
2026-09-15 finding that the journey did not actually create videos.

**Scope of this slice:** the operator/agent path only. The public browser
journey is NOT repaired here: without an operator token or a paid Stripe
trial, planning, execution, and provisioning all fail closed with a truthful
401 (stage 10 proves it). Browser team bootstrap — how team members
authenticate and get a wallet from the Studio UI — is out of scope for this
slice and unresolved.

## The named break this slice repairs

Every path from brief to finished video funneled through one of two dead ends:

1. **Stripe-gated trial.** The browser trial routes activate only from a paid
   Stripe checkout session, and no free activation path existed, so no team
   member could reach generation through that route.
2. **Operator-token browser plan.** Without a trial session the Studio create
   page calls the operator API directly from the browser, but nothing issues
   an operator token to a team member, so planning itself failed closed.

Planning, approval gates, wallet economics, and the executor state machine
were individually sound (the test suite already covered them). What was
missing was a truthful, free-for-the-team path connecting them.

## The additive fix

`POST /api/studio/billing/internal-wallet` (operator-authenticated) provisions
an internal team wallet with no Stripe and no customer charge. The wallet
keeps package economics, so provider spend stays behind the same server-owned
budget ceiling and the human approval gate. It is **off by default** and only
runs when the server sets `INTERNAL_WALLET_PROVISIONING_ENABLED=true`.
Idempotent on `internal_ref`. CLI parity: `blaster wallet-provision <json>`.

Nothing here spends money: a wallet only bounds provider cost, and generation
still requires `approved=true` per request.

## Running the walk

```bash
python -m pytest tests/studio/test_journey_walk.py -q
python scripts/production/journey_walk.py   # exits 0 and prints JOURNEY_WALK_OK
```

The walk stages:

1. `01_health_public` — public health names the platform and approval gate.
2. `02_plan_free_operator_auth` — planning works with operator auth, no spend; 401 without auth.
3. `03_execute_requires_approval` — unapproved execute blocks; zero provider calls.
4. `04_execute_requires_wallet` — approved execute without a wallet names `wallet_not_found`; zero provider calls.
5. `05_internal_wallet_off_by_default` — provisioning refuses unless explicitly enabled; 401 without auth.
6. `06_internal_wallet_provisions` — enabled provisioning returns an active wallet; replay is idempotent.
7. `07_journey_finishes_video` — brief → plan → approve → execute finishes with a final asset; wallet balances decrement exactly.
8. `08_wallet_truth_after_spend` — post-run wallet read matches the allowance receipt; exhausted wallet blocks truthfully.
9. `09_cli_parity` — CLI status, plan, `wallet-provision`, and wallet readback all hit the same governed backend (provision asserts an active wallet with package economics; readback proves the same wallet).
10. `10_browser_path_truthfully_blocked` — unauthenticated browser calls to plan, execute, and provisioning all return 401; zero provider calls.

Stage `06b` proves idempotency conflict is truthful: replaying the same
`internal_ref` with a different offer or customer reference returns
`session_ref_conflict` instead of silently reusing the wallet under different
economics or ownership.

## Boundary honesty

Only the paid/external boundary is faked in the walk: media provider, asset
storage, ffmpeg ops, the Redis wallet store (in-memory with the reserve Lua
semantics mirrored), and the durable ledger. Routing, auth, approval gates,
wallet economics, idempotency, and the executor state machine run for real.
A real Fal render still requires the production provider env, an active
wallet, and explicit approval on every generation request.
