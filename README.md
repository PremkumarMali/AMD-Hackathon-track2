# 🎬 Video Captioning Studio — Track 2

Streamlit app for the AMD Hackathon **Video Captioning** track. Upload a short
clip (30s–2min) and generate a caption/summary in **four styles**:
Formal · Sarcastic · Humorous (Tech) · Humorous (Non-Tech).

It runs in two modes:

- **Offline mock (default)** — Python + Streamlit + OpenCV process the clip and a
  rule-based generator writes the four captions. No API key needed.
- **Live Fireworks AI (optional)** — a vision model looks at the extracted frames
  and a text model writes the four captions. If anything goes wrong it
  automatically falls back to the offline mock, so the app never breaks.

## Features

- Project title & description hero
- Video upload button
- Live video preview with file metadata
- **Generate Captions** button
- Four styled caption cards (+ copy-text popovers)
- Loading spinner during generation
- Friendly error / validation messages
- Clean, demo-ready UI (light + dark friendly)

## How it works

1. **Upload** a short clip in the browser.
2. **Frame processing** — OpenCV samples a handful of evenly-spaced key frames
   (`src/frame_extractor.py`) and reads basic metadata (fps, duration, size).
3. **Video context** — a summary of the processed clip is assembled
   (`src/video_utils.py`).
4. **Caption generation** — one caption per style, either:
   - **mock:** a deterministic, rule-based generator
     (`src/caption_generator.py`; voices in `src/style_rules.py`), or
   - **Fireworks:** a two-call pipeline (`src/fireworks_client.py`) — call 1 asks
     a vision model to describe the frames, call 2 asks a text model to turn that
     description into the four styled captions as strict JSON.

Both paths return the same four-key result, so the UI is identical either way.

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
pip install -r requirements.txt
streamlit run main.py
```

Out of the box it uses the offline mock generator — no API key required.

## Live captions with Fireworks AI (optional)

Copy `.env.example` to `.env` (which is git-ignored — never commit it) and fill
in your own values:

```
FIREWORKS_API_KEY=your-key-here
FIREWORKS_MODEL=accounts/fireworks/models/kimi-k2p6
FIREWORKS_TEXT_MODEL=accounts/fireworks/models/gpt-oss-120b
USE_FIREWORKS=1
```

- `FIREWORKS_API_KEY` — your key from https://fireworks.ai.
- `FIREWORKS_MODEL` — vision model (call 1, describes the frames).
- `FIREWORKS_TEXT_MODEL` — text model (call 2, writes the JSON captions).
- `USE_FIREWORKS` — `1` for live captions; anything else uses offline mock.

Model ids must be accessible to your Fireworks account (check the dashboard). If
a Fireworks call fails for any reason, the app quietly falls back to the offline
mock captions, so a missing key or network hiccup never breaks the demo.

> Windows note: if Python HTTPS requests fail with a certificate error (common
> behind a VPN/proxy/antivirus that inspects TLS), run
> `pip install pip-system-certs` so Python trusts the Windows certificate store.
> This is a local machine fix, not a project dependency.

## Testing

```bash
python tests/test_backend_smoke.py
```

Runs entirely offline (mock mode) — it synthesizes a short test video and checks
frame extraction, the video context, caption generation (all four styles),
determinism, and the UI bridge. It never calls Fireworks or spends credits.

## Project structure

```
main.py                     # Entry point — streamlit run main.py
requirements.txt            # Dependencies
.env.example                # Template for local .env (Fireworks config)
.streamlit/                 # Theme config + secrets template
components/                 # Frontend UI (Streamlit)
  app.py                    # Main UI logic (CSS, nav, hero, orchestration)
  caption_cards.py          # STYLES + the caption card grid
  video_preview.py          # Upload + preview
  video_captioner.py        # Captioned video player
services/
  api_client.py             # generate_captions() — bridges UI <-> backend
src/                        # Backend logic (video processing + captions)
  frame_extractor.py        # extract_key_frames() — OpenCV key frames
  video_utils.py            # metadata + build_video_context()
  caption_generator.py      # generate_mock_captions() — rule-based captions
  style_rules.py            # the four caption voice definitions
  fireworks_client.py       # optional two-call Fireworks caption pipeline
utils/
  helpers.py                # File validation + formatting helpers
tests/
  test_backend_smoke.py     # End-to-end backend smoke test (offline)
assets/                     # Logo + demo screenshots
```
