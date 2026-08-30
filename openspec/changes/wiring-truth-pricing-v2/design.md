# Design — wiring-truth-pricing-v2

## Canonical planes

Social Studio owns the commercial production path. Legacy Creator `/v1/*` remains available as a bounded template/export surface, but it must not be presented as the canonical campaign/job ledger. Admin and Studio must consume real service state or explicitly show `not configured / no evidence yet`.

## UGC execution

The existing `UGCFactoryBrief -> build_ugc_factory_plan` contract remains the planning source. The execution coordinator adds no model IDs. It performs:

1. rebuild and validate the current factory plan;
2. enforce explicit paid-render approval;
3. estimate provider cost and ask the pricing guard for authorization;
4. submit clip 1 through the existing media provider;
5. poll only provider-owned Fal status/response URLs;
6. extract a downloadable video URL from a provider response;
7. download clip 1 without forwarding provider credentials to arbitrary hosts;
8. trim the tail and extract a clean final frame with ffmpeg;
9. submit clip 2 using the seed frame where the configured image-to-video endpoint supports it;
10. poll/download clip 2;
11. compare the seam using ffmpeg frame extraction and a dependency-light byte/image comparison helper;
12. stitch the clips to a final 9:16 MP4;
13. persist an execution receipt with plan version, approval, request IDs, model names, cost estimate, asset paths/URLs, QA state, and final state.

The live-provider executor is allowed to return a truthful partial state if a configured provider does not expose an expected field. It must never label a queued render as finished.

## Provider URL security

Fal credential-bearing GETs are allowed only when the URL origin matches `FAL_QUEUE_URL`. Media asset downloads use a separate unauthenticated client unless the asset is on the Fal queue origin. Redirects are not trusted to carry the Fal Authorization header to a new origin.

## Pricing guard

All paid generation goes through a server-side allowance decision.

Environment contract:

- `TRIAL_7_PRICE_CENTS` default `1900`
- `TRIAL_7_INCLUDED_AD_CREDITS` default `3`
- `TRIAL_7_PROVIDER_BUDGET_CENTS` default `400`
- `TRIAL_30_PRICE_CENTS` default `4900`
- `TRIAL_30_INCLUDED_AD_CREDITS` default `8`
- `TRIAL_30_PROVIDER_BUDGET_CENTS` default `1200`
- `STARTER_PRICE_CENTS` default `9900`
- `STARTER_PROVIDER_BUDGET_CENTS` default `3000`
- `PRO_PRICE_CENTS` default `19900`
- `PRO_PROVIDER_BUDGET_CENTS` default `6500`
- `MIN_CONTRIBUTION_MARGIN_BPS` default `6000` (60%)
- `UGC_FACTORY_CLIP_COST_CENTS` remains the conservative per-generation estimate.

For every package:

`provider_budget <= price * (1 - minimum_margin)`

A configuration that violates that inequality is not sellable and the checkout/pricing API returns a configuration error rather than authorizing spend.

The customer-facing unit is an **Ad Credit**, not a provider credit. One Ad Credit covers one standard finished-ad attempt only while its estimated provider cost is within the configured per-credit cost ceiling. Premium/expensive generations consume more credits or require a top-up before the provider call.

## Offer architecture — Proven / Better / New

### Proven
Use mechanics already common in the category:
- low-friction trial or free allowance;
- credits/usage pool;
- visible monthly output value;
- a clear most-popular tier;
- meaningful annual discount;
- cancel-anytime language;
- exact cost shown before render.

### Better
- paid trial rather than an unlimited free trial;
- trial money funds the first real production tests;
- no watermark on paid trial outputs;
- outcome unit is finished-ad attempts, not opaque raw provider credits;
- explicit provider-cost guard prevents negative unit economics;
- unused trial credits expire rather than becoming an open liability;
- a customer can upgrade without losing unused trial credits during the active period.

### New
- every generation carries a cost/approval/QA receipt;
- plan scripts and hypotheses stay attached to the generated asset;
- the system can tell the customer before render whether the request fits the included allowance or requires an upgrade/top-up.

## Checkout

Replace the old `founding-creator` checkout metadata with offer IDs:
- `trial-7`
- `trial-30`
- `starter-monthly`
- `pro-monthly`

Stripe Price IDs and Payment Links stay environment-only. Trial checkout is a one-time paid pass by default. Subscription auto-renew is only used for monthly plans. The UI must not call a paid trial “free.”

## Truthful UI

If canonical data is unavailable, show empty-state language such as `No campaigns yet`, `No completed renders yet`, `No performance evidence yet`, or `Integration configured but handshake not verified`. Never render invented production counts in live mode.

## Tests

Add tests for:
- pricing margin inequality and over-budget denial;
- paid-render allowance denial before provider submission;
- Fal URL origin restriction;
- UGC execution state transitions with provider/ffmpeg fixtures;
- voice/factory route parity;
- settings test semantics;
- clean migration filenames/order guard;
- frontend gauntlet rejecting hardcoded live metrics and stale Founding Creator checkout metadata;
- checkout 503 when Stripe config is absent.
