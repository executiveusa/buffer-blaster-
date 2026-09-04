# ICM Walk Test

Use this after structural changes and before calling the repository agent-readable.

## Cold-agent test
Give a fresh agent only the repository URL and this task:

> Find where you would change the public homepage copy, where you would add an API integration, how you would call Buffer Blaster through MCP and CLI, where production deployment truth lives, what actions require human approval, and where you would trace the origin/license of a UGC capability before implementing it. Do not modify anything.

The agent passes when it can answer after reading:
1. root `AGENTS.md`;
2. root `CONTEXT.md`;
3. at most one relevant area `CONTEXT.md` or linked reference per question.

## Required answers
- Public homepage: `frontend/`, guided by `frontend/CONTEXT.md` and `docs/POSITIONING.md`.
- API integration: `api/`, guided by `api/CONTEXT.md` and `docs/APP_BOUNDARIES.md`.
- MCP/CLI: `docs/AGENT_INTERFACES.md`, `api/routers/mcp.py`, `cli/blaster.py`.
- Production truth: `docs/PRODUCTION.md` and `GATES.production.md`.
- UGC capability provenance and implementation order: `docs/UGC_REFERENCE_MANIFEST.md` and `docs/UGC_EVOLUTION_PLAN.md`.
- Human gates: paid generation, publishing, ad activation, destructive operations, and contractual commitments.

## UGC provenance proof
For any proposed UGC/media feature, a cold agent must be able to answer without guessing:
1. Which upstream repo inspired the capability?
2. What immutable upstream commit is locked?
3. What exact upstream path was actually inspected, or is the reference README-level only?
4. Is adoption conceptual, an interface pattern, algorithmic, code reuse, or model reuse?
5. What code/model/data license applies?
6. What is prohibited or deliberately not copied?
7. Where will Buffer Blaster keep the canonical receipt, approval, cost, lineage, and artifact state?

If any answer is unknown, implementation is not authorized yet.

## Fail conditions
- Agent needs a repository-wide search to discover the normal task path.
- Router files contain long implementation payloads instead of pointers.
- The same operational fact has contradictory homes.
- A working folder lacks enough context to identify its inputs, job, outputs, and human check.
- A public/agent surface calls the product Social Studio instead of Buffer Blaster.
- An agent can discover a path that bypasses server-owned budget or approval controls.
- An agent copies or vendors UGC code/model assets without first resolving the pinned source path and applicable code/model/data license in `docs/UGC_REFERENCE_MANIFEST.md`.
- An agent treats an upstream `main` branch as a stable dependency instead of the locked revision.

## Interface proof
In production, separately verify:
- REST health/status;
- authenticated MCP initialize/tools list;
- CLI status and no-spend plan;
- unapproved paid execution fails;
- no secrets appear in output.

A readable repository and a working interface are separate proofs. Pass both.
