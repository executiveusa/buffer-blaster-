# Phase 06 — Auth, onboarding, budget and security hardening

- [ ] Verify the actual Supabase auth/login/session path and protected-vs-public Studio behavior in runtime and tests.
- [ ] Define the minimum onboarding journey for an internal/client operator: identity -> workspace -> client context -> budget policy -> Studio.
- [ ] Enforce server-side generation budget ceilings at workspace, operator/agent and run/job levels; UI values cannot increase authority.
- [ ] Preserve explicit approval before paid generation, publishing and ad activation.
- [ ] Add rate limits/idempotency where an agent retry could otherwise multiply cost.
- [ ] Run secret scanning/dependency/security checks; remove exposed debug/admin surfaces or prove they are authenticated.
- [ ] Verify RLS and workspace/client isolation with negative tests.
- [ ] Add tests for expired/invalid sessions, cross-workspace access, exhausted budgets, duplicate agent calls and privilege escalation attempts.

Exit: authenticated operators and agents can work productively while cost, tenant and consequential-action boundaries fail closed.