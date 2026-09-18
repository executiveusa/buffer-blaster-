# 03 Benchmark

## Job
Score the adapted prompt against the reference slice before any paid generation call.

## Process
1. Build the benchmark slice from the compiled catalog: featured dataset cards (`featured: true`) plus cards in the same `subcategory` as the adaptation target.
2. Score structure and craft against `skills/scoring/SKILL.md` and the external bar in `docs/MAXFUSION_GAUNTLET.md` (hook, timing, continuity constraints, natural-speech rules from the UGC Ad Factory template).
3. Compare the adapted prompt side by side with at least 3 reference prompts from the slice. The question is not "is it good" but "does it carry the same load-bearing elements the proven prompts carry".
4. Record PASS/FAIL per element. A failed element loops back to `02_adapt`, not forward.

## Output
`output/benchmark.md` — score table, reference card ids used, and the PASS/FAIL verdict with reasons.
