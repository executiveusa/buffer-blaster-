# 03_launch — authorize and launch test

One job: convert an approved experiment into bounded provider actions.

## Inputs
- Working: ../01_define/output/experiment.md
- Working: ../02_bind_channels/output/channel-bindings.md

Do NOT load: unrelated client channels or credentials into ICM files.

## Process
1. Build the exact launch packet: variants, audience, budget, schedule, channel, stop condition.
2. Require explicit human approval artifact before any spend/publish action.
3. Submit through provider adapters only after approval; record provider IDs and receipts.

## Outputs
- launch-receipt.md → output/

## Human check
Approve the exact spend, audience, creative variants, and stop condition before provider submission. No approval artifact means no launch.
