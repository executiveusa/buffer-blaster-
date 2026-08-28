# Tasks — V1 Production Proof

- [ ] Update the API root contract test to include the accepted `/api/mcp` route.
- [ ] Remove or remediate every high-severity production dependency advisory reported by the frontend audit without lowering the audit threshold.
- [ ] Run the existing API, frontend gauntlet, lint, build, route smoke, and security gates through GitHub Actions.
- [ ] Fix failures until required verification is green.
- [ ] Squash-merge the verified PR to `main`.
- [ ] Verify the resulting production Vercel deployment and runtime error state.
- [ ] Verify Supabase remains healthy and no destructive migration was introduced.
- [ ] Record the Fal model choice/configuration boundary without committing credentials.
- [ ] Keep real social publishing blocked until exact content receives explicit human approval.
