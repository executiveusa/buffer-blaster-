# 01 Retrieve

## Job
Find the smallest set of candidate prompts that match the creative brief.

## Process
1. Read the brief's subject, audience, tone, platform, and target model family.
2. Search `library/compiled/search-catalog.json` (compact fields only). Example:
   `jq '.cards[] | select(.subcategory != null) | select((.title + " " + (.description // "") + " " + ((.tags // []) | join(" "))) | test("ugc|commercial"; "i")) | {id, title, subcategory, tags}' library/compiled/search-catalog.json`
3. Pull full prompts for shortlisted ids from `library/compiled/full-cards.json` only. Never load the whole catalog into model context.
4. Prefer cards whose `source.repo` and `source.path` are present; skip anything without verified provenance.

## Output
`output/shortlist.json` — 3-5 candidate card ids with title, source repo/path/hash, and why each matches the brief.
