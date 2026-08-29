# Application Boundaries

Buffer Blaster / Social Studio is a standalone application.

Other schedulers, publishers, analytics products, and agent products are separate applications.

They must not share Buffer Blaster source code, database ownership, Docker services, secrets, migrations, branding, deployment lifecycle, or release status.

Any connection to another application must use an explicit external API boundary. External integrations are optional and must never determine whether Buffer Blaster itself is healthy or beta-ready.
