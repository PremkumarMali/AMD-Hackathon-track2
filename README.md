# 🎬 Video Captioning Studio — Track 2

Streamlit frontend for the AMD Hackathon **Video Captioning** track. Upload a
short clip (30s–2min) and generate a caption/summary in **four styles**:
Formal · Sarcastic · Humorous (Tech) · Humorous (Non-Tech).

Models are served via the **Fireworks AI API**.

## Features

- Project title & description hero
- Video upload button
- Live video preview with file metadata
- **Generate Captions** button
- Four styled caption cards (+ copy-text popovers)
- Loading spinner during generation
- Friendly error / validation messages
- Clean, demo-ready UI (light + dark friendly)

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run main.py
```

The app runs out-of-the-box with mock captions so you can demo the whole flow
without an API key.

## Going live (Fireworks AI)

1. Add your key to `.streamlit/secrets.toml`:
   ```toml
   FIREWORKS_API_KEY = "your-api-key"
   ```
2. In `services/api_client.py`, open `generate_captions()` and replace the mock
   block with the real call (the scaffold is already there, commented out).
3. Tune the per-style prompts / model id in the same file.

## Project structure

```
main.py                     # Entry point — streamlit run main.py
requirements.txt            # Dependencies
.streamlit/                 # Theme config + secrets template
components/
  app.py                    # Main UI logic (CSS, nav, hero, orchestration)
  caption_cards.py          # STYLES + the 2×2 caption card grid
  video_preview.py          # Upload + preview
services/
  api_client.py             # generate_captions() + Fireworks AI client
utils/
  helpers.py                # File validation + formatting helpers
assets/                     # Logo + demo screenshots
```
