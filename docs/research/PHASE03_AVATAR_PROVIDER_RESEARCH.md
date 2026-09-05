# Phase 03 — Avatar/provider research boundaries

This phase studies optional avatar/provider patterns without vendoring, installing, or claiming production support for them.

## Reviewed upstreams

| Upstream | Reviewed revision | License / boundary | Buffer Blaster decision |
| --- | --- | --- | --- |
| OmniAvatar | `1536bf31abaec74364fb7d5883470d5b23ffa7f8` | Apache-2.0 source | Pattern/reference only in Phase 03. No runtime installation. |
| EchoMimic | `c32b3a557003f84ead1483a2d2386035685d984d` | Apache-2.0 source | Pattern/reference only in Phase 03. No runtime installation. |
| LivePortrait | pinned in U0 provenance manifest | MIT source, but bundled InsightFace detection assets are not commercially clean for our use | Do not integrate commercially unless the detection dependency is replaced with a permitted alternative and separately verified. |
| HeyGem | pinned in U0 provenance manifest | Custom Silicon Intelligence Community License with commercial conditions | License-review-required. Do not integrate automatically. |

## Adopted patterns

Buffer Blaster adopts provider-neutral concepts only:

- capability discovery rather than browser-selected model IDs;
- hosted/local/hybrid deployment classification;
- health, latency, cost and commercial-use metadata;
- identity/consent requirements as routing inputs;
- sovereign preference for local/hybrid providers;
- server-owned cost ceilings and wallet authority;
- deterministic no-spend route receipts before any paid execution.

## Not adopted

- no upstream provider credentials;
- no upstream billing implementation;
- no hardcoded upstream model identifier;
- no bundled face/voice model or checkpoint;
- no restricted cloud code;
- no client-side spend authority;
- no claim that a studied project is installed or production-ready.

The existing Fal adapter remains the only built-in runtime provider entry in Phase 03. Additional entries are configuration-owned and must independently satisfy rights, commercial-use, capability, health and cost checks.
