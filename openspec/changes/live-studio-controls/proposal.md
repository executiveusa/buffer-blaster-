# Proposal — live-studio-controls

## Objective

Finish the production control path that the V1 UI already exposes: the command surface must call the shared Studio API when live, and the calendar must resolve a connected TryPost account before it can schedule explicitly approved content.

## Problem

The V1 backend already exposes `/api/studio/agent/command`, `/api/studio/social/accounts`, and `/api/studio/social/schedule`, but the production UI still treated the agent command locally and the calendar's scheduling button did not call the publishing boundary. That made the interface look more complete than the verified execution path.

## Outcome

- Agent commands use the shared REST contract in live mode and remain explicitly simulated in demo/public-console mode.
- Calendar scheduling loads real TryPost social accounts, requires an exact account selection, exact content, future time, format, and explicit human approval, then calls the existing Social Drop scheduling route.
- Demo mode returns receipts that are clearly labeled as simulation rather than external publish proof.
- No provider secret, social-account ID, or public post is invented.
- No database migration is required.

## Non-goals

- No automatic publishing.
- No selection of a social account without resolving it from TryPost.
- No environment secret changes in git.
- No destructive Supabase change.

## External verification used

TryPost's current API exposes `GET /social-accounts`; its API resource returns `id`, `platform`, `display_name`, `username`, `is_active`, and `status`. Scheduling requires a real active UUID `social_account_id`, a compatible `content_type`, and a future `scheduled_at`.
