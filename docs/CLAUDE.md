# CLAUDE.md — Root ICM Router
# Stavarai Platform | Interpretable Context Methodology (Van Clief, 2026)
# Version: 1.0.0 | Classification: PRIVATE — Stavarai + Partner eyes only

---

## YOU ARE CLAUDE CODE. READ THIS ENTIRE FILE BEFORE TOUCHING ANY OTHER FILE.

This file is the root of the ICM (Interpretable Context Methodology) pipeline.
Every folder is a numbered stage. Every stage has a CONTEXT.md.
You read CONTEXT.md first. You execute. You move to the next stage.
You never skip. You never assume. You never combine stages unless told.

---

## WHAT THIS IS

**Stavarai Platform** is a private, enterprise-grade AI content operations system
built for one social media management company. It is not SaaS. It is not generic.
It is trained on proprietary data and runs exclusively for internal use.

The company never sees how it works — only that it works.
Stavarai and his partner are the only people with full visibility.
Everyone else sees results.

---

## ICM STAGE MAP

```
00_context/     ← Read this first on every session. Project identity, constraints, secrets.
01_research/    ← Competitor intelligence, trend analysis, client intake
02_specs/       ← TDD specs. Tests BEFORE code. Always.
03_tests/       ← Test files. Run these. Pass these. Then build.
04_implementation/ ← Actual code. Only after tests exist.
05_deploy/      ← Vercel, VPS, Supabase migrations, CI commands
agents/         ← Hermes SOUL.md, config, skills
skills/         ← All SKILL.md files (grill-me, stop-slop, scoring, etc.)
docs/           ← Architecture decisions, changelogs, gap analysis
landing/        ← Public-facing marketing site
dashboard/      ← Stavarai's private admin panel (password: BLASTER2026)
blog/           ← Company blog (public, sticky, affiliate-ready)
api/            ← FastAPI backend (Python) + Rust performance modules
rust_core/      ← High-security, high-speed Rust components
```

---

## CORE LAWS (NEVER VIOLATE)

1. **Tests before code.** Every feature has a test spec before implementation starts.
2. **ICM structure is sacred.** Every new file goes in the correct numbered stage folder.
3. **No client data mixes.** Each client project lives in a sandboxed Supabase schema.
4. **Stop-slop on all text.** Every word the platform generates passes the anti-slop filter.
5. **LLM-agnostic.** No hardcoded model names in business logic. Provider is a config value.
6. **Beads on every change.** `.beads/` entry before every destructive operation.
7. **Rust for speed + security.** Auth, encryption, rate limiting, task queuing = Rust.
8. **Stavarai only.** Backend access requires BLASTER2026. No exceptions.
9. **Built to Sell.** Every feature makes the system MORE independent, not more dependent on its builders.
10. **No lock-in.** Buffer, Higgsfield, Airtable — all swappable via adapter pattern.

---

## CONTEXT ROUTING

When you start a task, read in order:
1. This file (CLAUDE.md) — you're here
2. `00_context/PROJECT.md` — who Stavarai is, what the company is, the mission
3. `00_context/SECRETS.md` — env var locations, API key structure (never hardcode)
4. The CONTEXT.md of the relevant stage for your current task
5. Any SKILL.md files referenced in that CONTEXT.md

---

## COMPANY & POSITIONING (Built to Sell)

Stavarai and partner work inside a social media management company.
They are building this platform to:
1. Add unmistakable AI-powered value to the company's clients
2. Become the internal experts the company depends on
3. Position the platform for acquisition at $500K (cash + stock + shares)
4. Execute the Warrillow "options strategy" — build it right whether or not they sell

**The 3 Warrillow tests this platform must pass:**
- Teachable: Any future employee can run it from the SOPs
- Unique: The internal training data + client history is the moat
- Repeatable: Monthly recurring output, not one-off projects

The blog is the public face. The platform is the secret weapon.
The acquisition pitch is: "You already depend on us. Now own us."

---

## TECHNICAL ARCHITECTURE SUMMARY

```
Frontend:   Next.js 15 + shadcn/ui + Tailwind v4 (TailAdmin free base)
Backend:    FastAPI (Python 3.11+) + SQLAlchemy + Pydantic v2
Rust core:  Auth tokens, AES-256 encryption, rate limiting, job queuing
Database:   Supabase (Postgres) — per-client schema isolation
Agent:      Hermes (NousResearch) — LLM-agnostic via adapter
Video:      Higgsfield MCP → CLI (mcp2cli) → Sandcastle sandboxes
Voice:      Whisper → Hermes → TTS response (Telegram + Meta Glasses)
Telegram:   python-telegram-bot → Hermes command interface
Meta:       VisionClaw (Intent-Lab) → gesture + voice → Hermes
Dashboard:  TailAdmin React (customized) — Stavarai only
Blog:       Next.js MDX — public, SEO-optimized, affiliate-ready
Deploy:     Vercel (frontend) + VPS (agents, Rust, FastAPI)
Autoresearch: Karpathy loop adapted for social content A/B testing
```

---

## DEMO CONFIGURATION

For demo mode (no auth):
- Landing page: fully public
- Demo dashboard: `BLASTER2026` password only, no OAuth
- Backend greeting: "Welcome back, Stavarai." + one-time walkthrough overlay
- All demo data: seeded fake clients, real-looking metrics
- No real client data in demo mode

---

## UPSTREAM REPOS TO MONITOR

| Repo | Role |
|------|------|
| NousResearch/hermes-agent | Orchestrator |
| Intent-Lab/VisionClaw | Meta Glasses interface |
| karpathy/autoresearch | A/B test loop |
| RinDig/Interpreted-Context-Methdology | ICM spec |
| knowsuchagency/mcp2cli | Higgsfield CLI |
| earendil-works/absurd | Task resilience |
| mattpocock/sandcastle | Client sandboxes |
| executiveusa/buffer-blaster- | Buffer Blaster core |

---

*Read `00_context/PROJECT.md` next.*
