<!--
  GRINIONS™ phase PR. Squash-merge only when every gate below is checked.
  See AGENTS.md and EMERALD_TABLETS.md for the full contract.
-->

## Objective

<!-- One sentence. What does this phase deliver? -->

**OpenSpec change:** `openspec/changes/<id>/` <!-- link -->
**Phase:** `phase/<n>-<slug>`
**Risk:** `low` | `medium` | `high` _(high requires explicit owner sign-off)_
**Bead epic:** `<bd-id>`

## Changes

<!-- What changed, by area. Reference files, not vibes. -->

## Acceptance criteria

<!-- Copied from the OpenSpec change. -->

## Verification (paste output, don't paraphrase)

- [ ] `rtk cargo test --manifest-path rust_core/stavarai_core/Cargo.toml` → green
- [ ] `rtk python -m pytest tests -q` → green (count: __)
- [ ] `cd frontend && rtk npm run lint` → clean
- [ ] `cd frontend && rtk npm run build` → 0 errors
- [ ] OpenSpec verify: `openspec validate <id>` → accepted
- [ ] Beads in this phase closed or explicitly deferred

## Security / migration impact

<!-- If this touches auth, RLS, schema, secrets, or payments: explain. -->

## Rollback

`ops/rollback/<phase-id>.json` attached.
- Baseline main SHA: `________`
- Tested rollback commands: yes / no
- Data-loss risk: none / low / high

## Scope discipline

- [ ] Changed files are inside the approved phase scope
- [ ] No unexpected dependency changes
- [ ] No public surface leaks an internal name (grep `frontend/src` + `content/blog` for `hermes|buffer.?blaster|stavarai`)

## Known limitations / follow-ups

<!-- New beads opened as a result of this work, deferred items, etc. -->
