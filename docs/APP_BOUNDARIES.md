# Application Boundaries

## Strict Isolation: Buffer Blaster vs. Downstream Services

Buffer Blaster / Social Studio is a standalone, proprietary content-operations and UGC generation system.

External scheduling, publishing, or social distribution platforms (such as TryPost, PostaStudios, or other third-party schedulers) are completely separate applications.

### Buffer Blaster Owns
- Campaign planning and strategy
- Brand and product memory / creative inputs
- Content ideation, creative angles, hooks, and scripts
- UGC video prompting and multi-modal prompt compilation
- Image and video rendering (via configured media engines such as Fal)
- Media library and asset management
- Content scoring and creative evaluation
- Human review and strict approval gate enforcement
- Studio analytics and creator performance insights
- Agent, REST, MCP, CLI, and voice interfaces
- Dedicated Redis session and cache state
- Dedicated Supabase schema and data scope
- Dedicated secrets and deployment lifecycle

### Downstream Publishers Own
- Their own source code and repositories
- Their own frontend and backend runtimes
- Their own databases, schemas, and persistence
- Their own credentials, API keys, and OAuth connection tokens
- Their own social account connections (Instagram, TikTok, YouTube, X, etc.)
- Their own scheduling queues and worker infrastructure
- Their own deployment lifecycles

### Architectural Invariants
1. **No Code Merging**: External publishing code is never vendored or merged into Buffer Blaster.
2. **No Shared Infrastructure**: Buffer Blaster does not share Docker Compose services, Redis cache, database tables, or migrations with external publishers.
3. **Optional Downstream Boundary**: External publishing is an optional downstream integration.
4. **Independent Core Readiness**: Buffer Blaster boots, passes preflight, reports healthy, creates campaigns, generates UGC, and enforces human approvals completely independently. The absence of an external publishing integration is NOT an error or blocker for Buffer Blaster core operations.
5. **Fail-Closed Approval**: Under all circumstances, unapproved content can never be published.
