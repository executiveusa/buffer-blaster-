# Tasks — live-studio-controls

- [x] Add a structural gauntlet that fails unless the command surface calls the shared Studio API.
- [x] Add a structural gauntlet that fails unless the calendar resolves accounts and calls the approval-gated scheduler.
- [x] Add `runAgentCommand` to the shared frontend Studio API client.
- [x] Add TryPost social-account retrieval and normalization.
- [x] Mark seeded command/render/schedule results as simulated.
- [x] Wire agent command execution to `/api/studio/agent/command` in live mode.
- [x] Require exact content, future time, connected account, format, and human approval before scheduling.
- [x] Surface schedule receipts and distinguish demo simulation from external proof.
- [ ] Verify CI on the PR.
- [ ] Squash-merge after CI is green.
- [ ] Verify the production Vercel deployment and runtime error table after merge.
- [ ] Configure Fal/TryPost/OpenAI runtime credentials outside git before a real end-to-end publish proof.
