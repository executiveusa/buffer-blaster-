# Gates: Buffer Blaster production finish

A gate is complete only when its command exits 0 and prints the expected marker. Re-run completed gates before final release.

- [ ] G1: repository Python suite passes
  CHECK: python -m pytest tests -q && echo PYTHON_SUITE_OK
  EXPECT: PYTHON_SUITE_OK
  EVIDENCE: pending

- [ ] G2: frontend installs, lints, and builds
  CHECK: cd frontend && npm ci && npm run lint && npm run build && cd .. && echo FRONTEND_BUILD_OK
  EXPECT: FRONTEND_BUILD_OK
  EVIDENCE: pending

- [ ] G3: production compose resolves with the external self-hosted Supabase network
  CHECK: docker compose -f docker-compose.prod.yml config >/tmp/buffer-blaster-compose.yml && grep -q selfhost_supabase /tmp/buffer-blaster-compose.yml && echo COMPOSE_OK
  EXPECT: COMPOSE_OK
  EVIDENCE: pending

- [ ] G4: self-host preflight proves core and self-hosted Supabase route
  CHECK: bash scripts/selfhost/preflight.sh | tee /tmp/buffer-blaster-preflight.txt && grep -q 'SELF-HOSTED SUPABASE ROUTE READY' /tmp/buffer-blaster-preflight.txt && echo PREFLIGHT_OK
  EXPECT: PREFLIGHT_OK
  EVIDENCE: pending

- [ ] G5: production smoke suite passes
  CHECK: bash scripts/selfhost/smoke.sh && echo PROD_SMOKE_OK
  EXPECT: PROD_SMOKE_OK
  EVIDENCE: pending

- [ ] G6: public health identifies Buffer Blaster and canonical persistent Supabase ledger
  CHECK: python scripts/production/verify.py health
  EXPECT: PUBLIC_HEALTH_OK
  EVIDENCE: pending

- [ ] G7: Phase 5 provider report is sanitized and recommends a verified provider subset
  CHECK: python scripts/production/verify.py provider-report /tmp/buffer-blaster-phase5-provider-report.md
  EXPECT: PROVIDER_REPORT_OK
  EVIDENCE: pending

- [ ] G8: human approval remains mandatory for provider activation/spend and publishing
  CHECK: python -m pytest tests/studio/test_money_loop_providers.py tests/selfhost -q && echo APPROVAL_GATES_OK
  EXPECT: APPROVAL_GATES_OK
  EVIDENCE: pending

- [ ] G9: money-loop production worker is running and API can reach self-hosted PostgREST
  CHECK: python scripts/production/verify.py runtime
  EXPECT: RUNTIME_OK
  EVIDENCE: pending

- [ ] G10: public repository has no user-visible Stavarai/PostaTees identity
  CHECK: python scripts/production/verify.py identity
  EXPECT: IDENTITY_OK
  EVIDENCE: pending

- [ ] G11: final production PRD contains no unfinished tasks
  CHECK: python scripts/production/verify.py prd docs/PRODUCTION_FINISH_PRD.md
  EXPECT: PRD_COMPLETE_OK
  EVIDENCE: pending

- [ ] G12: final AdPanel comparison receipt records a binary independent-critic win on desktop and mobile
  CHECK: python scripts/production/verify.py gauntlet ops/final-gauntlet/adpanel-receipt.json
  EXPECT: FINAL_GAUNTLET_OK
  EVIDENCE: pending
