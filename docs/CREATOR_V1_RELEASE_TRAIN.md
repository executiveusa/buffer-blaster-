# Creator V1 Release Train

This bounded release train closes phases 9–14 without introducing database coupling.

- Phase 9: public creator identity and deployment config cleanup.
- Phase 10: deterministic verified-only corpus compiler with compact search and full-card outputs.
- Phase 11: hybrid retrieval ranking with media intent, weighted fields, quality, license gate, and duplicate suppression.
- Phase 12: deterministic Adapt API, creator input workspace, editable adapted prompt, and adapted ICM export.
- Phase 13: local-first saved adaptation library in browser storage; no Supabase mutation until the correct project identity is confirmed.
- Phase 14: selected-card API plus `skill.md` agent contract for discover → inspect → adapt → export.

Release rule: CI, dependency audit, lint, build, route smoke, review, Vercel preview, squash merge, and production verification must pass before completion.
