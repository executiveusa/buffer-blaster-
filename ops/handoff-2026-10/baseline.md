# Buffer Blaster handoff baseline — 2026-10-11

## Repository truth

- Repository: `executiveusa/buffer-blaster-`
- Baseline branch: `main`
- Baseline SHA: `91eb7cf6b1851c2c27df7c1c8956c10aa10d245d`
- Baseline working tree: clean
- Runtime used for verification:
  - Python 3.11.6
  - Node 20.9.0
  - npm 10.1.0
  - Rust stable 1.99.0 installed in the sandbox for the Rust check

The uploaded handoff named `executiveusa/buffer-blaster`; the installed GitHub repository is `executiveusa/buffer-blaster-`, so execution uses the installed repository name.

## Baseline results on main

### Backend

```text
244 passed, 1 warning
```

The warning is Starlette's TestClient/httpx deprecation notice.

### Frontend

```text
npm ci             PASS
npx tsc --noEmit   PASS
npm run lint       PASS with 1 warning
npm run build      PASS
```

Known lint warning:

```text
frontend/src/lib/studio-api.ts
@next/next/no-location-assign-relative-destination
```

The install also reports six high-severity npm audit findings. They are not introduced by the Step 1 patch and must be handled separately rather than hidden by this PR.

### Rust baseline

`cargo test` fails on main with three unresolved imports caused by the current rand/aes-gcm versions:

- `aes_gcm::aead::OsRng`
- `rand::rngs::OsRng`
- `rand::RngCore`

Exit code: `101`.

## Step 1 red tests

Two regression tests were added before the fixes:

```text
tests/studio/test_mcp_execute_reservation_parity.py
tests/auth/test_login_rate_limit_xff.py
```

Both fail on the old implementation:

1. MCP reserves `999` cents from plan metadata instead of the provider-backed estimate `375`.
2. Auth rate limiting accepts a caller-supplied `X-Forwarded-For` value instead of the ASGI peer address.

Result before implementation:

```text
2 failed
```

## Step 1 repaired branch verification

Branch:

`fix/handoff-step1-verified-core-fixes`

Changes:

- MCP uses `estimate_factory_generation_cost` before wallet reservation and passes the same provider into the executor.
- Auth rate limiting uses `request.client.host`; Uvicorn remains the only layer allowed to resolve trusted proxy headers.
- Rust entropy generation uses `getrandom::fill` instead of removed `OsRng` paths.
- Cargo.lock refreshed for the dependency change.

Verification:

```text
targeted regressions: 2 passed
backend full suite:   246 passed, 1 warning
frontend tsc:         PASS
frontend lint:        PASS with the pre-existing 1 warning
frontend build:       PASS
Rust unit/integration: 31 passed, 0 failed
Rust doc tests:        0 failed
```

Rust currently emits deprecation warnings for aes-gcm hybrid-array `from_slice`; those are outside this narrowly scoped Step 1 repair.

## Not executed

No provider generation, publishing, ad activation, wallet spend, or other consequential external action was run during this baseline/Step 1 slice.
