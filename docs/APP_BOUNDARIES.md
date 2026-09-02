# Application Boundaries

## Buffer Blaster vs. downstream services

Buffer Blaster is a standalone, proprietary creative-operations and UGC production system. **Studio** is the human workspace inside Buffer Blaster; it is not a separate product identity.

External stores, ad networks, schedulers, and publishing platforms remain separate systems connected through optional adapters.

### Buffer Blaster owns
- campaign and creative planning;
- brand/product context and creative inputs;
- angles, hooks, scripts, and UGC production plans;
- image/video rendering through configured media providers;
- media library and asset state;
- creative evaluation and experiment records;
- human review and approval enforcement;
- server-owned generation allowances and provider-cost budgets;
- commerce/performance attribution records when integrations are configured;
- Studio, REST, MCP, CLI, and voice interfaces;
- dedicated Redis state;
- dedicated Supabase schema/data scope;
- dedicated secrets and deployment lifecycle.

### Downstream systems own
- their source code and runtimes;
- their databases and persistence;
- their OAuth/API credentials;
- social/store/ad-account connections;
- platform-specific delivery and scheduling infrastructure;
- their independent deployment lifecycle.

Examples include Shopify, Meta Ads, TikTok Ads, Buffer, and any alternate publisher selected later.

### Architectural invariants
1. **No code merging:** external application source trees are not vendored into Buffer Blaster.
2. **No shared authority:** provider credentials remain server-side and scoped to the integration that needs them.
3. **Optional downstream boundary:** Buffer Blaster remains useful when an external publisher or paid-media provider is absent.
4. **Independent core readiness:** research, planning, UGC production, review, ledger persistence, and approval controls must work independently of downstream publishing.
5. **Fail-closed approval:** unapproved content cannot publish, and unapproved paid generation/ad activation cannot spend.
6. **Provider truth:** an adapter being implemented does not mean an external account is live-verified. Live status requires real account authentication and readback proof.
7. **One creative system:** UI, REST, MCP, CLI, and voice call the same canonical backend rather than maintaining separate business logic.
