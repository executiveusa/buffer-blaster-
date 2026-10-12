# Buffer Blaster handoff baseline — 2026-10-11

## Repository truth

- Repository: `executiveusa/buffer-blaster-`
- Default branch: `main`
- Head observed before Step 1 implementation: `ab307f5f077a88d1e49609fec6c38868937c4b4a`
- Security prerequisite merged before Step 1 rebase: `91eb7cf6b1851c2c27df7c1c8956c10aa10d245d`
- The uploaded handoff referenced `executiveusa/buffer-blaster`; the connected canonical repository includes the trailing hyphen.

## Source inspection before Step 1

The three handoff fixes were not present on the observed main:

1. `api/routers/mcp.py::_execute_factory` still reserved from the factory commercial estimate instead of `estimate_factory_generation_cost`.
2. `api/deps.py::_client_ip` still trusted caller-supplied `X-Forwarded-For`.
3. Rust entropy paths still imported `OsRng` from the current rand/aes-gcm stack.

Also absent:
- `release_reservation`
- OpenRouter runtime wiring
- MiniMax runtime wiring

## CI evidence

The first Step 1 CI pass proved:
- API tests: pass
- PostgreSQL schema proof: pass
- Rust core workflow: pass
- frontend gate: blocked by pre-existing production dependency advisories

A narrow prerequisite PR upgraded only Next / eslint-config-next and the sharp / source-map-js overrides. Its lock-refresh job reported `npm audit --omit=dev --audit-level=high` with 0 production vulnerabilities, Frontend Verify passed, Test API and Frontend passed, and Codex review completed without a finding comment.

Step 1 was then rebased on that security prerequisite and must re-pass CI before merge.


## Final Step 1 hardening evidence

- Codex identified a mixed text/image pricing gap; the estimator now prices one text-video call plus the expected image-video calls before wallet reservation.
- Codex identified wildcard Uvicorn proxy trust; the Docker runtime now requires explicit `FORWARDED_ALLOW_IPS`, defaults to loopback only, and preflight rejects `*`.
- Auth tests now exercise Uvicorn `ProxyHeadersMiddleware` for trusted and untrusted peers.
- Cargo.lock was regenerated from scratch by CI after replacing direct rand usage with getrandom.
- Regenerated lockfile contains no `rand` or `chacha20` package entries and the temporary lock-refresh workflow removed itself.
- The lock-refresh workflow executed `cargo test --locked` before committing the new lockfile.
