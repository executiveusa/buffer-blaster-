# Playwright MCP + Production Browser Audit

Buffer Blaster carries a project-scoped Playwright MCP definition in `.mcp.json`.

## Why

Repository agents must verify the product from the user's point of view, not infer success from source code or HTTP 200 responses. Playwright MCP gives agents deterministic browser interaction through accessibility snapshots.

Official upstream: Microsoft Playwright MCP (`@playwright/mcp`).

## Agent rule

For public-site, Studio, auth, form, navigation, component, or release work:

1. Read `AGENTS.md`, `EMERALD_TABLETS.md`, and `docs/PRODUCTION.md`.
2. Start the project Playwright MCP server from `.mcp.json` when the client supports project MCP configuration.
3. Navigate to the exact production or preview URL under test.
4. Inventory links, buttons, inputs, selects, video, dialogs, and navigation.
5. Click every safe user control.
6. Do not click controls that cause paid generation, public publishing, ad activation, destructive mutation, or contractual commitment unless the repository's explicit approval gate is satisfied.
7. For guarded controls, verify the guard/disabled state instead of bypassing it.
8. Record console errors, page errors, failed network requests, redirects, visible error states, and unexpected simulation.
9. Test desktop and mobile.
10. Do not claim production readiness without browser evidence.

## MCP configuration

The checked-in configuration runs:

```text
npx -y @playwright/mcp@latest --headless --isolated --browser=chromium
```

Node 20+ is recommended.

Clients that do not automatically consume repository `.mcp.json` can add the same command to their MCP settings manually.

## Deterministic production suite

The repository also includes a Playwright test suite under:

```text
frontend/e2e/
```

Run:

```bash
cd frontend
bash scripts/run-production-playwright.sh
```

Defaults:

```text
PLAYWRIGHT_BASE_URL=https://bufferblaster.netlify.app
```

Optional authenticated operator pass:

```bash
PLAYWRIGHT_OPERATOR_PASSWORD='<runtime secret>' bash scripts/run-production-playwright.sh
```

Never commit that password or any session token.

Optional real Netlify form proof:

```bash
PLAYWRIGHT_ALLOW_FORM_SUBMIT=true \
PLAYWRIGHT_FORM_EMAIL='buffer-blaster-qa@example.com' \
bash scripts/run-production-playwright.sh
```

Use an obvious QA address and clean up the resulting test submission.

## Safety boundary

Playwright MCP is a browser automation surface, not an authorization boundary. Browser automation does not grant permission to bypass Buffer Blaster's spend, approval, publishing, security, or destructive-operation controls.

## Evidence

Browser runs should preserve:

- Playwright HTML report
- traces for failures
- screenshots for failures
- JSON/console evidence when produced
- exact production URL
- exact deployed SHA/deploy ID when known
