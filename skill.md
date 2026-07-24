# Creator Studio Skill

## Purpose
Find a small number of useful, provenance-aware creative recipes, adapt one with project-specific inputs, and export a portable agent pack.

## Workflow
1. Call `POST /v1/discover` with a plain-language `intent` and `limit: 3`.
2. Present only the returned candidates. Do not load the entire catalog into context.
3. Inspect a selected card with `GET /v1/cards/{id}` when full card context is needed.
4. Call `POST /v1/adapt` with `card_id` and all `required_inputs`.
5. Keep human review before publishing or sending generated work.
6. Export the selected/adapted recipe with `POST /v1/export/icm` when portability is requested.

## API examples

### Discover
```json
{"intent":"cinematic nonprofit event reel for Instagram","limit":3}
```

### Adapt
```json
{"card_id":"bb-video-launch-reel-001","inputs":{"subject":"community youth event","audience":"local families","tone":"documentary","platform":"Instagram"}}
```

### Export
```json
{"card_id":"bb-video-launch-reel-001","inputs":{"subject":"community youth event","audience":"local families","tone":"documentary","platform":"Instagram"}}
```

## Context discipline
Load discovery summaries first. Load only the selected card's full prompt and provenance. Keep mutable generated work outside the read-only recipe context.

## Safety and provenance
Use only cards marked `license_verified: true`. Preserve source attribution and license metadata. Do not assume repository licensing clears third-party likeness, trademark, or preview-image rights.
