# Agent Interfaces

Buffer Blaster exposes one governed production system through several clients. None of these clients may bypass backend approval, wallet, workspace, or provider checks.

## REST
Base: `BLASTER_API_URL`

Safe reads include:
- `GET /api/health`
- `GET /api/studio/status`
- `GET /api/studio/jobs`

Creative planning/execution lives under `/api/studio/*`. Consequential actions enforce server-side approval and budget rules.

## MCP
Endpoint: `POST /api/mcp`
Transport: HTTP JSON-RPC 2.0
Authentication: operator Bearer token

Useful tools include:
- `studio_status`
- `list_creative_jobs`
- `create_campaign_plan`
- `create_ugc_prompt`
- `create_ugc_ad_factory_plan`
- `execute_ugc_ad_factory`
- `schedule_social_drop`

`execute_ugc_ad_factory` requires `approved=true` plus a server-owned active wallet. The server reserves generation allowance before calling the media provider.

## CLI
```bash
export BLASTER_API_URL=https://<api-host>
export BLASTER_API_KEY=<operator-token>
python -m cli.blaster status
python -m cli.blaster jobs
python -m cli.blaster mcp-info
```

Planning examples:
```bash
python -m cli.blaster campaign brief.json
python -m cli.blaster ugc-plan brief.json
```

Execution examples remain approval-gated:
```bash
python -m cli.blaster ugc-execute approved-brief-with-wallet.json
python -m cli.blaster schedule approved-drop.json
```

## Remote-agent rule
An agent may call these interfaces from anywhere it can securely reach the API and obtain an operator credential. Never embed `BLASTER_API_KEY`, Supabase service-role keys, provider tokens, or client secrets in prompts, URLs, browser bundles, repositories, or screenshots.

## Walk-test proof
A production walk test should verify:
1. public health returns Buffer Blaster identity;
2. unauthenticated MCP privileged calls fail;
3. authenticated MCP `initialize` and `tools/list` succeed;
4. CLI `status` succeeds against the same API;
5. a no-spend UGC plan succeeds;
6. an unapproved paid execution is rejected;
7. no secret value is printed in normal output.
