# Buffer Blaster for Claude Code and Codex

Buffer Blaster is an **internal agent tool**, not a public subscription service.
Claude Code and Codex connect to the **same** governed API via the local stdio
bridge `python -m cli.mcp_stdio`. This adapter forwards MCP JSON-RPC; it does
not store client data, issue provider credentials, approve spending, or execute
generation outside the canonical backend.

## Prerequisites

- Clone the Buffer Blaster repository and run commands from its root, with Python 3.10+.
- Have a reachable Buffer Blaster API, with its backend, wallet and ledger configured.
- Set `BLASTER_API_URL` to the API origin (not the frontend).
- Set `BLASTER_API_KEY` to an operator token **in your shell or secret manager**.
  Never place token values in a committed `.mcp.json`, `config.toml`, prompt,
  screenshot, or agent skill. Prefer HTTPS for remote APIs.

Local development (example only):

```sh
export BLASTER_API_URL=http://localhost:8000
export BLASTER_API_KEY="$(your-secret-manager-read-command)"
python -m cli.blaster mcp-info
```

The secret-manager command above is a placeholder, not a command to run
literally. Obtain an actual operator token from the authorized runtime store.

## Claude Code

Run from the repository root:

```sh
claude mcp add --transport stdio buffer-blaster -- python -m cli.mcp_stdio
claude mcp list
```

The MCP process inherits the environment of the Claude Code process. If
starting Claude from a desktop app or another shell, configure its secret
environment securely rather than relying on an unrelated terminal session.

## Codex CLI

Run from the repository root:

```sh
codex mcp add buffer-blaster -- python -m cli.mcp_stdio
codex mcp list
```

The Codex MCP process also needs `BLASTER_API_URL` and `BLASTER_API_KEY`
available in its environment. If the agent's working directory is outside the
checkout, install the package or set a trusted `PYTHONPATH` pointing at the
checkout; do not use a copied standalone bridge that drifts from the repo.

## Install the agent skill (optional)

The canonical operating skill is `plugins/social-studio/SKILL.md`. To make it
discoverable by both clients, copy it to each client's recognized skill folder
in the project where your agents run:

```sh
mkdir -p .claude/skills/buffer-blaster .agents/skills/buffer-blaster
cp plugins/social-studio/SKILL.md .claude/skills/buffer-blaster/SKILL.md
cp plugins/social-studio/SKILL.md .agents/skills/buffer-blaster/SKILL.md
```

Review and update copies when the canonical skill changes. The MCP tool
catalog remains the server's authority, not the prose in a skill file.

## Safe walk test

1. Run `python -m pytest tests/clients/test_mcp_stdio.py tests/studio/test_mcp.py -q`.
2. In Claude or Codex, invoke `studio_status`, `list_provider_capabilities`,
   then `create_ugc_ad_factory_plan` with a synthetic product brief. No
   provider generation or wallet reservation should occur.
3. Call `execute_ugc_ad_factory` with `approved=false`. It must return
   `human_approval_required` without spending. Do not test live spend using
   `approved=true` unless an authorized human has approved the exact job.
4. Verify a missing/invalid token fails closed; verify no token is printed.
5. For a real release, complete `GATES.production.md` and the production
   MCP/CLI walk test. A local unit test does **not** prove production readiness.

## Troubleshooting

- MCP server missing: run `python -m cli.mcp_stdio` from the checkout and
  confirm Python can import `cli`. It will wait for MCP JSON-RPC on stdin.
- Unauthorized: verify the operator token is present in the *agent process*
  environment; do not paste the token into a chat or issue.
- API unavailable: check `BLASTER_API_URL` points to the FastAPI service,
  not the public Next.js site.
- Tool not available: use `tools/list` to discover the live backend tool
  names; do not invent a route or bypass the MCP boundary.

Rollback: remove the `buffer-blaster` MCP server entry from Claude/Codex and
revert this branch/PR. No schema or provider configuration changes are needed.
