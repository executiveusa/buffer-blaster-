# Production: getting a paid render to work

This is the short path from a fresh server to a finished ad. Gates and proof
requirements live in [`GATES.production.md`](../GATES.production.md).

## Two ways to render

| Path | Needs | Use it for |
|---|---|---|
| **Server** (`/api/studio/ugc/factory/execute`, MCP `execute_ugc_ad_factory`) | API + Redis + Supabase storage + Fal key + ffmpeg | client work, agents, anything that must be recorded and wallet-capped |
| **Local one-shot** (`python -m cli.render_local`) | Python deps + ffmpeg + `FAL_KEY` in the shell | a single operator render on one machine, e.g. testing a brief |

Both run the same planner, script gates and executor. The local path keeps the
job record in memory and files on disk, and replaces the wallet with a
command-line spend cap (`--approve-cents`) that must cover the quote.

## 1. Server install

```bash
# On an Ubuntu/Debian VPS with a DNS name pointing at it (private repo: clone with your GitHub access)
git clone https://github.com/executiveusa/buffer-blaster-.git && cd buffer-blaster-
sudo bash scripts/selfhost/install.sh --domain api.example.com
```

`install.sh` checks out the repo, writes `.env.production` with generated app
secrets, and starts `docker-compose.prod.yml`: **Redis** (container `redis`,
`REDIS_URL=redis://redis:6379/0`), the API, the money-loop worker and Caddy.
Redis holds sessions, the job queue and the generation wallet; nothing else to set up.

## 2. Supabase (ledger + asset storage)

The API joins the self-hosted Supabase Docker network
(`SUPABASE_DOCKER_NETWORK`, default `supabase_default`).

1. Apply migrations in order: `supabase db push` (or run `supabase/migrations/*.sql`).
   `009_buffer_blaster_storage.sql` creates the private `buffer-blaster-assets` bucket.
2. In `.env.production` set `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   (service role, server only) and `BUFFER_BLASTER_WORKSPACE_ID`.
3. Restart: `docker compose -f docker-compose.prod.yml up -d api`.

Without storage the execute route stops at `asset_storage_not_configured`
before any spend.

## 3. Fal (video)

Set in `.env.production`: `FAL_KEY`, the model IDs, the model's input field
names, and its **real** price per clip. Talking UGC needs a model that makes
speech audio; otherwise the job ends in `visual_complete_needs_audio`.

| Preset (checked 2026-11-21) | `FAL_IMAGE_VIDEO_MODEL` | `FAL_IMAGE_INPUT_FIELD` | `FAL_DURATION_TYPE` | `FAL_AUDIO_INPUT_FIELD` | Clip length | ~cost / 10s clip |
|---|---|---|---|---|---|---|
| Kling v3 Pro (default) | `fal-ai/kling-video/v3/pro/image-to-video` | `start_image_url` | `string` | `generate_audio` | 3-15s | $1.40 |
| Veo 3.1 Fast | `fal-ai/veo3.1/fast/image-to-video` | `image_url` | needs `"8s"` format, not supported yet | `generate_audio` | 4/6/8s | $1.20 (8s) |

Set `FAL_ESTIMATED_CLIP_COST_CENTS` (default 150) to the chosen model's price.
The wallet reserves `price x expected calls x UGC_FACTORY_COST_SAFETY_BPS`
(1.25x by default); a one-clip ad is one call.

Image-to-video models **start on the image you give them**. Give them a
realistic first frame, not a flat product mockup; make one with
`cli.render_local keyframe` (below) and approve it first.

## 4. Wallet for internal work

Set `INTERNAL_WALLET_PROVISIONING_ENABLED=true`, then provision once with
`python -m cli.blaster wallet-provision wallet.json`. Paid execution needs that
`wallet_id`, `approved=true` and an `idempotency_key`.

## 5. Local one-shot render

```bash
pip install -r api/requirements.txt          # plus ffmpeg on PATH
export FAL_KEY=...                           # never commit or paste into files
export FAL_IMAGE_VIDEO_MODEL=fal-ai/kling-video/v3/pro/image-to-video
export FAL_IMAGE_INPUT_FIELD=start_image_url FAL_DURATION_TYPE=string FAL_AUDIO_INPUT_FIELD=generate_audio
export FAL_ESTIMATED_CLIP_COST_CENTS=140
export FAL_KEYFRAME_MODEL=fal-ai/nano-banana/edit FAL_KEYFRAME_COST_CENTS=4

python -m cli.render_local quote docs/examples/postatees-mariner-10s.json --first-frame
python -m cli.render_local keyframe docs/examples/postatees-mariner-10s.json \
  --reference hoodie-mockup.jpg --out frame.png --approve-cents 4
# look at frame.png, then:
python -m cli.render_local render docs/examples/postatees-mariner-10s.json \
  --first-frame frame.png --end-card-image hoodie-mockup.jpg --out final.mp4 --approve-cents 175
```

The machine needs HTTPS access to `queue.fal.run` and Fal's media hosts
(`*.fal.media`).

## 6. Reusing a locked character

Add `"character": "jalen"` to a brief to reuse the Postatees car-ad guy: same
face, hoodie, car setting, voice and delivery in every ad. Example:
[`docs/examples/jalen-postatees-10s.json`](examples/jalen-postatees-10s.json).
How it works and how to lock his voice on Fal: [`characters/README.md`](../characters/README.md).
