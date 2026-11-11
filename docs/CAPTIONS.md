# Captions (S7)

Shared transcription + SRT/VTT export + brand burn-in. Self-hosted: zero API
fee per call, recorded in the usage ledger at provider-known
`actual_cents=0` (kind `transcribe`). Zero fee is not zero host cost, so the
host bounds below are enforced, not advisory.

## Pinned components (manifest row)

| Component | Pinned version | License | Role |
|---|---|---|---|
| faster-whisper | 1.2.1 | MIT | transcription API |
| ctranslate2 | 4.9.0 | MIT | inference runtime |
| Whisper model | `base` (`WHISPER_MODEL` env) | MIT (OpenAI Whisper) | weights - HF `Systran/faster-whisper-base` snapshot revision `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`, enforced AT RUNTIME via `snapshot_download(revision=...)` (offline falls back to local files only), not just documented |
| Golden fixture | tests/fixtures/jfk.wav | Public domain (JFK speech, via whisper.cpp samples) | accuracy/timing proof |

Golden proof: `tests/golden/jfk_base_words.json`, captured 2026-11-10 with
exactly these pins on CPU int8; two consecutive runs byte-identical
("And so my fellow Americans, ask not what your country can do for you...").
The golden test asserts real speech recognized, word count within ±1 and
first/last boundaries within ±150 ms. A stub backend proves formatting only.

## Pinned decoding (determinism contract)

All decode parameters are explicit constants in `api/services/captions.py`;
no library default is relied on: `beam_size=5`, `temperature=0.0`,
`vad_filter=False`, `condition_on_previous_text=False`, `cpu_threads=1`,
`num_workers=1`. Changing any of them invalidates the golden fixture.

Threading is pinned at EVERY layer: ctranslate2's int8 GEMM honors the math
libraries' own threading below the model pin, and unpinned OMP/BLAS threads
produced divergent transcripts of the golden fixture (2/10 runs: zero words,
wrong-language output, runaway repetition). `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1` and `MKL_NUM_THREADS=1` are therefore set in
`api/app.py` (before router imports) and `tests/conftest.py` (before native
imports), and re-asserted at `captions` module import: OpenMP latches its
thread count at first use, so the pins must land before any native import.
Operators embedding the service in another host must set the same env before
importing native code.

The native model is loaded ONCE per process (`_MODEL_CACHE`): repeatedly
constructing and dropping ctranslate2 model objects was correlated with
corrupt decodes; the Redis busy lock already serializes transcriptions per
host, so the shared instance is never used concurrently.

Even with all pins, token-level punctuation can vary on CPU int8
(`Americans` vs `Americans,`); the golden bar (real speech, word count ±1,
boundaries ±150 ms) is the stability contract. A repeated-fixture test
(5 real runs) enforces it, and the catastrophic modes all violate it loudly.

## Empty transcript = error, never success

A transcription returning zero words is `{"ok": False, "error":
"empty_transcript"}`: it is NOT cached (the content-hash cache is never
poisoned), NOT ledgered, and no caption job can report done with zero cues.
This was a real defect: an unpinned run returned zero words 2/14 times and
the pipeline accepted it. Retry or inspect the audio.

## Flow

1. `transcribe_footage` (MCP plan scope; REST POST /api/studio/captions/transcribe,
   execute role) - word timestamps + cues (max 2 lines, <=42 chars/line,
   <=5 words/cue) + SRT + VTT. Cached FOREVER by content sha256
   (`bb:captions:{sha256}`); a cache hit never re-runs the model.
2. `burn_captions` (MCP plan; REST POST /burn) - burns the cached words into
   a NEW asset (original opened read-only, sha256 asserted unchanged) via a
   generated ASS karaoke script. Brand style (pixel-verified in tests, raw
   RGB band diffs, not ffprobe alone): opaque ink #111111 box
   (BorderStyle=3), WHITE inactive words, the ACTIVE word in lime #B9FF66
   (one Dialogue line per word interval; the highlight advances word by
   word), Inter (fontconfig fallback DejaVu Sans when Inter is not
   installed on the host - the layout contract is font-independent).
   MarginV=70 on libass PlayResY 288 places text ~311px above the bottom of
   a 1280-tall 9:16 frame: lower third, clear of the lower tenth (platform
   UI zone).
3. `get_captions` (MCP read; REST GET /{asset_id}) - cached transcript only,
   `not_transcribed` otherwise; never recomputes.

## Bounds and isolation

- `CAPTIONS_MAX_SECONDS` (default 600) and `CAPTIONS_MAX_BYTES` (default
  250 MB); duration read via ffprobe - missing ffprobe FAILS CLOSED
  (`ffprobe_unavailable`, operator-visible).
- One concurrent transcription per host (`bb:captions:busy` Redis lock,
  15 min PX) - `captions_busy` otherwise.
- Workspace authorization BEFORE any global sha256 cache lookup: an asset
  owned by another workspace returns `asset_not_found`, so cached
  transcripts can never leak across workspaces.
- No secrets: self-hosted model, no API keys. `WHISPER_MODEL` only selects
  the local model size (golden proof pins `base`; larger models are a
  deliberate accuracy choice, not covered by the golden).
