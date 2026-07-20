# Capability: production-readiness

> Durable spec. Proposed changes go in `openspec/changes/<id>/`. This file
> describes the steady-state contract, not the migration path.

## ADDED Requirements

### Requirement: The platform runs on a Linux VPS with the Rust core active

The FastAPI backend SHALL load the prebuilt `libstavarai_core.so` and report
`"core": "rust"` at `GET /api/health`. If the prebuilt lib is absent, the
backend SHALL fall back to the pure-Python implementation in
`api/services/native.py` and report `"core": "python"` honestly — never
silently impersonate the Rust backend.

#### Scenario: prebuilt lib present
- **WHEN** `rust_core/native/libstavarai_core.so` exists
- **THEN** `GET /api/health` returns `"core": "rust"`
- **AND** all `rust_core/stavarai_core/tests/*.rs` pass via `cargo test` on the VPS

#### Scenario: prebuilt lib absent
- **WHEN** the file is missing
- **THEN** `GET /api/health` returns `"core": "python"`
- **AND** all 46 pytest tests still pass

### Requirement: Per-client schema isolation is enforced end-to-end

Every client query SHALL scope to `schema_{sanitized_slug}`. The sanitizer
MUST produce a name matching `^schema_[a-z0-9_]+$` for any input. The anon
Supabase key SHALL return zero rows from any `schema_*` table. The service
role is the only role that can write.

#### Scenario: cross-client read attempt
- **GIVEN** two clients `schema_a` and `schema_b` with `content_units` rows
- **WHEN** a query scoped to `schema_a` runs
- **THEN** zero rows from `schema_b` are returned

#### Scenario: anon key access
- **WHEN** any `schema_*` SELECT runs with the anon key
- **THEN** the result set is empty

### Requirement: The pipeline runs end-to-end and never auto-publishes

A pipeline run SHALL enqueue a job (Rust queue when core=rust, Python queue
otherwise) and spawn a Hermes child orchestrator. Status updates SHALL stream
via Supabase realtime. The publisher SHALL only fire on explicit human
approval from the operator's dashboard.

#### Scenario: successful run
- **WHEN** `POST /api/admin/pipeline/{slug}/run` is called with a valid token
- **THEN** a job is enqueued in under 1ms
- **AND** on completion `schema_{slug}.approval_queues` is populated
- **AND** no post enters Buffer without an explicit Approve click

#### Scenario: failure
- **WHEN** a step fails
- **THEN** absurd retries 3×
- **AND** on final failure writes a bead and Telegrams the operator

### Requirement: All public surfaces are leak-free and accessible

The landing page, blog index, and blog post pages SHALL NOT contain any of
`stavarai`, `hermes`, `buffer.blaster`, `higgsfield` (case-insensitive). All
pages SHALL pass axe-core with zero critical violations, meet WCAG AA contrast,
have alt text on every image, labels on every input, and a skip-to-content
link.

#### Scenario: leak grep
- **WHEN** `grep -riE 'stavarai|hermes|buffer.?blaster|higgsfield' frontend/src content/blog` runs
- **THEN** the only matches are in admin or non-public paths
- **AND** the built `.next` output contains no internal names in public HTML

### Requirement: Rollback is proven before any phase merges

Every phase PR SHALL include `ops/rollback/<phase-id>.json` with baseline
SHA, affected services, tested rollback commands, and data-loss risk. A phase
without proven rollback does not merge.

#### Scenario: rollback contract present
- **WHEN** a phase PR opens
- **THEN** `ops/rollback/<phase-id>.json` exists and `tested: true`
