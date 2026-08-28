# PROVEN-BETTER-NEW CARD — Agentic Social Studio V1

Instinct: A small brand or agency wants one place that reliably turns a campaign idea into publishable social content without coordinating a pile of specialist tools.

Primary analog: Adpanel — audience match: DTC teams that need publishing, approvals, UGC ads, and lightweight social operations in one workspace.

## Proven — think about

- **Acquisition / first-run — Adpanel.** Its onboarding is plan → connect accounts → publish/automate, with time-to-value measured in minutes. V1 should preserve a visible connect/create/schedule path rather than forcing technical setup before the product feels useful. Source: https://www.adpanel.io/
- **Core loop — Adpanel.** Create UGC + review + publish in the same workspace is already a coherent behavior loop. The V1 information architecture keeps Create UGC, My Ads, Calendar and approvals adjacent instead of reinventing them as separate products. Source: https://www.adpanel.io/
- **Monetization — Adpanel / Creatify.** Adpanel proves low-friction $20/$50/$100 social bundles; Creatify proves $39/$99 for higher-value AI ad creation. A combined creation+operations product sits between those anchors. Sources: https://www.adpanel.io/ and https://creatify.ai/pricing
- **Distribution — Predis.** Create-to-autopost across many channels is already expected in the category; Predis sells one brand at $19 and four brands at $40 annually discounted, with posting and generation credits. Source: https://predis.ai/pricing/
- **Programmatic access — Buffer.** API access is now a baseline expectation even on lower-priced social plans. V1 should not pretend API/MCP is the entire differentiator; it is a distribution surface. Source: https://buffer.com/pricing
- **Publishing kernel — TryPost.** Open-source/self-hosted publishing with REST/MCP is already proven infrastructure. The proprietary product should not rebuild OAuth and scheduling network-by-network. Source: https://trypost.it/

## Better — think about

- Adpanel already combines UGC and publishing. Does the persistent **outcome command** reduce enough work that 9–10/10 of its current users would prefer “run this campaign” over navigating each tool manually? Atomic test: five real campaign briefs, measure time and edits from brief to approval-ready calendar.
- Predis already creates and schedules. Does **explicit approval + receipts + agent state** create materially more trust for teams/agencies than full autopost? Atomic test: compare acceptance rate and correction count with and without the visible approval queue.
- Creatify is deeper on ad generation. Can V1’s **provider-neutral render layer** beat lock-in by letting an operator keep the same workflow while models change? Atomic test: produce the same brief through two providers without modifying campaign or UI code.
- Buffer makes API access cheap. Does packaging **MCP + CLI + plugin + voice around the same contracts** make programmatic operation simpler enough to matter, or is it merely technical surface area? Atomic test: cold agent performs status → UGC prompt → account lookup → approved schedule from the plugin alone.
- Adjacent variant: the product can be sold as a **managed social operating system for agencies** rather than only creator SaaS. The Agency tier tests whether multi-brand operators value the coordination layer more than individual brands do.

## New — think about

- **Agent as primary interaction.** This is load-bearing only if manual UI remains complete. V1 quarantines it: the dashboard works without agent execution, and the command surface accelerates existing actions.
- **Voice control.** Novel but non-load-bearing. Browser/server voice resolves to explicit intents and cannot bypass approval. Atomic test: ten spoken intents, compare resolved action and approval flag to text equivalents.
- **Cross-provider UGC routing.** The abstraction is new product plumbing, not a customer promise. Atomic test: swap `FAL_*_MODEL` values and prove the same UGC brief/receipt contract survives.
- **Filesystem/ICM-compatible agent state.** Useful for operator continuity but invisible to end customers. Atomic test: a cold agent can locate campaign objective, pending gate and evidence within the routing contract without chat memory.
- **Pricing a UGC credit as up to 10 seconds.** This is intentionally testable rather than permanent. Atomic test: first 25 paid renders → actual provider cost distribution, retry rate, and gross margin by tier.

Graveyard: no specific failed product with the exact Adpanel-like UGC+publishing bundle was established in this V1 research sweep. The larger graveyard risk is feature-suite sprawl: mature social tools already cover publishing, AI assistants, analytics and APIs, so “more features” alone has no protected floor.

Anti-signal: the build should not use founder excitement or prior engineering work as evidence of market pull. The useful evidence is existing paid behavior across Adpanel, Predis, Creatify, Buffer and TryPost.

Sources: Adpanel https://www.adpanel.io/ · Predis https://predis.ai/pricing/ · Creatify https://creatify.ai/pricing · Buffer https://buffer.com/pricing · TryPost https://trypost.it/

Sharpest tensions: Adpanel already proves the combined workspace, so agent execution must save meaningful time rather than decorate it; Creatify/Predis create at far greater model/template depth, so V1 should win on orchestration rather than catalog size; API/MCP/voice must remain alternate controls over one product, not six separate products.

## V1 pricing hypothesis

- Creator — **$39/mo**: 1 brand, 5 social accounts, 3 UGC credits, campaign builder, approval/scheduling, library.
- Growth — **$119/mo**: 4 brands, 20 accounts, 12 UGC credits, agent planning, scoring, analytics, approvals.
- Agency — **$299/mo**: 12 brands, 60 accounts, 40 UGC credits, API/MCP/CLI, plugin, white-label exports, priority queue.

These are hypotheses, not validated willingness-to-pay. They deliberately anchor Creator to Creatify Starter, price Growth above Adpanel Scale because it adds autonomous campaign work and materially more UGC capacity, and reserve programmatic/agency packaging for the tier whose buyer can monetize it across clients.
