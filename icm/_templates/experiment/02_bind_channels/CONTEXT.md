# 02_bind_channels — bind execution and attribution

One job: map experiment variants to authorized ad and commerce channels without launching them.

## Inputs
- Working: ../01_define/output/experiment.md
- Reference: ../../../../_system/CONTEXT.md

Do NOT load: unrelated clients, unrelated provider payloads, secrets into the workspace.

## Process
1. Resolve authorized Meta/TikTok ad account references and Shopify/store attribution source through runtime configuration.
2. Bind each control/variant to stable external IDs or placeholders.
3. Record the attribution key strategy (UTM, click/ad ID, discount code, landing route, or approved equivalent).
4. Verify read/write capabilities separately; configured is not verified.

## Outputs
- channel-bindings.md → output/

## Human check
Confirm the accounts belong to the intended client/workspace and the experiment cannot spend or publish outside the approved scope.
