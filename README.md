# 🎬 Video Captioning Studio — Track 2

Streamlit app for the AMD Hackathon **Video Captioning** track. Upload a short
clip (30s–2min) and generate a caption/summary in **four styles**:
Formal · Sarcastic · Humorous (Tech) · Humorous (Non-Tech).

The current MVP runs **fully offline**. It uses **Python + Streamlit + OpenCV**
for the video/frame processing and a **mock / rule-based generator** for the
four captions — no external API or key is required to run the demo.

## Features

- Project title & description hero
- Video upload button
- Live video preview with file metadata
- **Generate Captions** button
- Four styled caption cards (+ copy-text popovers)
- Loading spinner during generation
- Friendly error / validation messages
- Clean, demo-ready UI (light + dark friendly)

## How it works (MVP)

1. **Upload** a short clip in the browser.
2. **Frame processing** — OpenCV samples a handful of evenly-spaced key frames
   (`src/frame_extractor.py`) and reads basic metadata (fps, duration, size).
3. **Video context** — an honest summary of the processed clip is assembled
   (`src/video_utils.py`). No real "AI understanding" of the footage is claimed.
4. **Caption generation** — a rule-based generator writes one caption per style
   (`src/caption_generator.py`; voices defined in `src/style_rules.py`). Output
   is deterministic per clip, so demos are repeatable.

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

The app runs out-of-the-box with the offline rule-based generator, so you can
demo the whole flow without any API key.

## Testing

Run the backend smoke test from the project root:

```bash
python tests/test_backend_smoke.py
```

It synthesizes a short test video and checks frame extraction, the video
context, caption generation (all four styles), determinism, and the UI bridge.

## Future integration (Fireworks AI — not active)

Fireworks AI is **not used** in the current MVP. A scaffold is left in
`services/api_client.py` (`fetch_captions`) for a possible future "live" mode
that would swap the mock generator for a hosted vision model. It stays inactive
until it is wired up and given an API key — the app runs entirely without it.

## Project structure

```
main.py                     # Entry point — streamlit run main.py
requirements.txt            # Dependencies
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
utils/
  helpers.py                # File validation + formatting helpers
tests/
  test_backend_smoke.py     # End-to-end backend smoke test
assets/                     # Logo + demo screenshots
```
