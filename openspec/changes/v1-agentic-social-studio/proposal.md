# Proposal — v1-agentic-social-studio

## Owner acceptance

Accepted by the owner in chat on 2026-08-28: ship a usable V1 tonight that combines UGC creation, social scheduling, agent-first operation, redesigned UI/UX, pricing, plugin, MCP, CLI, API, and voice.

## Problem

The repository has strong content-operations primitives, a UGC prompting skill, client isolation, scoring, and an admin backend, but its current public/product surfaces are split between an older Creator Studio experience and internal Stavarai/Buffer Blaster architecture. UGC creation is guidance rather than an executable provider workflow, social publishing is not abstracted behind the new TryPost option, voice is a canned queue response, and there is no single agent-first product surface.

## Outcome

Ship one coherent V1 that lets an operator or agent:

1. plan a campaign from a natural-language objective;
2. compile production-ready UGC prompts from a structured brief;
3. submit media generation through a provider adapter when credentials exist;
4. review and explicitly approve content;
5. schedule approved content through TryPost;
6. operate the same system through UI, REST, MCP, CLI, plugin skill, or voice;
7. use a polished public site and product UI influenced by Adpanel's restrained visual system without copying its branding or implementation.

## Non-goals

- No bypass of the human publishing gate.
- No direct coupling to one LLM or one video model.
- No vendoring or modifying TryPost source inside this proprietary repository.
- No destructive database migration for V1.

## Commercial position

Primary analog: Adpanel for the combined publishing + UGC workspace. Secondary analogs: Predis for create-to-publish breadth, Creatify for UGC/ad generation value, Buffer for scheduling/API expectations, and TryPost for the publishing kernel. V1 pricing will preserve a low-friction entry tier while charging for autonomous campaign generation, UGC credits, and programmatic/agency surfaces.
