# Prompt Library Run ICM

## Outcome
Turn a creative brief into one adapted, benchmark-scored, provenance-clean generation prompt ready for the UGC Ad Factory (or an ICM export), using only the verified upstream prompt libraries.

## Walk
1. `01_retrieve` — search the compiled catalog for candidate prompts matching the brief.
2. `02_adapt` — adapt one candidate to the brief with the Higgsfield skill structure; keep provenance attached.
3. `03_benchmark` — score the adapted prompt against the reference/benchmark slice before any paid call.
4. `04_gate` — human approval artifact. No paid generation without it.
5. `05_handoff` — package prompt, provenance, benchmark score, and approval into the consuming workflow.

## Rules
- Retrieve before writing from scratch. The libraries exist so agents stop inventing prompts.
- Use only cards with `license_verified: true`. Preserve source repo, path, and content hash on every adaptation.
- Never hand a failed benchmark or unapproved prompt to a paid generation call.
- Provider/model selection stays outside this ICM template.
- No publishing without explicit human approval.

## Where the libraries live
- Registries (what upstreams are allowed): `sources/youmind-openlab.json`, `sources/goku-openlab.json`, `sources/oside-media.json`
- Imported cards + manifests: `library/imported/<org>/`
- Compiled retrieval catalogs: `library/compiled/search-catalog.json` (compact) and `library/compiled/full-cards.json` (full prompts)
- Bolted-on prompt skill: `skills/higgsfield/` (OSideMedia, MIT)

## Refresh
Re-run ingestion after an upstream registry changes:
```
python3 scripts/youmind_ingest.py --registry sources/youmind-openlab.json --source-root <upstream-clones> --output-root library/imported/youmind
python3 scripts/youmind_ingest.py --registry sources/goku-openlab.json --source-root <upstream-clones> --output-root library/imported/goku-openlab
python3 scripts/youmind_ingest.py --registry sources/oside-media.json --source-root <upstream-clones> --output-root library/imported/oside-media
python3 scripts/build_creator_catalog.py --input library/imported --output library/compiled
```
