# Design Gauntlet — V1

## Bar

Named, fetchable, comparable reference: **Adpanel** (`https://www.adpanel.io/`) plus the owner-supplied screenshots of its landing page, Explore, My Ads, Moodboards, and Canvas at desktop/mobile-relevant proportions.

The comparison is deliberately against the real product, not a verbal style description.

## Pieces judged independently

1. **Public landing** — editorial type, whitespace, product proof, concise CTA hierarchy.
2. **Application shell** — narrow icon rail + secondary navigation + large calm work surface.
3. **UGC create flow** — product input → prompt → video as an obvious, low-cognitive-load progression.
4. **Library / review** — visual scanning, queue state, asset status, and one-click next action.
5. **Campaign / calendar** — the difference between “agent can prepare” and “human has approved” must be instantly legible.
6. **Agent command** — must feel native to the product rather than a chatbot pasted onto it.
7. **Mobile** — navigation and creation flow must remain usable without preserving desktop chrome.

## Harsh critic rubric

For each piece, the critic answers only:

- Which is easier to understand in five seconds: ours or Adpanel?
- Which has stronger hierarchy and less visual noise?
- Which makes the next action more obvious?
- Which better communicates system state?
- What is the single biggest remaining gap?

No praise is counted as evidence. A structural gate is implemented in `frontend/scripts/design-gauntlet.mjs`; it verifies the required page set, public codename safety, quiet-shell design signals, voice/approval boundaries, and pricing packaging. That gate is necessary but not sufficient for a visual win.

## Round 0 — baseline critique

The previous public UI was a dark “Creator Studio” workflow-discovery product, while the internal repo described a social content-operations platform. Against Adpanel it lost on product identity, app-shell clarity, UGC visual workflow, calendar visibility, and commercial packaging. Voice existed server-side only as a canned queued response. Social publishing was not represented as a replaceable kernel.

## Builder response

V1 changes the public/product system to a light editorial language influenced by the supplied Adpanel references without copying its brand or source. The app now has the two-rail shell, UGC create flow, asset library, moodboards, canvas, campaigns, calendar, analytics, settings, agent command, voice intent capture, and explicit approval state.

## Exit condition

Before merge: structural gauntlet + lint + build + Python tests must pass.

After deployment: capture our `/`, `/studio`, `/studio/create`, `/studio/library`, `/studio/canvas`, and `/pricing` pages at comparable desktop widths. Compare them side-by-side against the supplied Adpanel references. If a page loses on hierarchy/state/next-action clarity, fix the single biggest gap and repeat. Do not call visual parity or a blind win until that screenshot comparison has actually happened.
