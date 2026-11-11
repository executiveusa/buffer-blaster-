# Buffer Blaster Claude Code plugin

Install: `claude plugin install ./plugins/claude` (or add this folder to a plugin marketplace).
Set in your shell (never in a file): `BLASTER_API_URL` (e.g. https://api.example.com) and
`BLASTER_AGENT_TOKEN` (a scoped `bba_` token from a human operator: `POST /api/agent/tokens`).
Alternative stdio transport from a repo checkout: `python -m cli.mcp_stdio` with the same env vars.
The skill enforces plan-first and human approval for every render or publish.
