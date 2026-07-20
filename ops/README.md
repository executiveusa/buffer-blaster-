# ops/ — GRINIONS operational artifacts

Zero-context handoff artifacts. Every phase must populate its subdirectory
before squash-merge.

```
ops/
├── reports/     # per-phase JSON report (agent/model, tokens, retries, PR rounds)
├── receipts/    # post-merge verification receipts (smoke checks, deploy IDs)
└── rollback/    # <phase-id>.json with baseline SHA + tested rollback commands
```

A phase is **not complete** until all three exist for its phase-id.

See `EMERALD_TABLETS.md` Tier 4 and `docs/HANDOFF.md` for the contract.
