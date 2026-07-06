"""Caption service — the bridge between the Streamlit UI and the backend.

`generate_captions()` is the ONLY function the UI calls. Right now it runs the
offline, rule-based backend in `src/`: the uploaded clip is processed into key
frames and a mock generator writes the four captions. The Fireworks AI scaffold
further down is kept for a possible future "live" mode but is intentionally
unused for now.
"""

from __future__ import annotations

import os
import sys
import tempfile

import requests

# Make the project's `src/` backend importable no matter which directory
# Streamlit is launched from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.caption_generator import generate_mock_captions
from src.frame_extractor import extract_key_frames
from src.video_utils import build_video_context

# Endpoint + model are placeholders — replace with the values revealed on
# launch day. Chat-completions style is assumed here.
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
DEFAULT_MODEL = "accounts/fireworks/models/your-vision-model"
REQUEST_TIMEOUT = 120

_STYLE_PROMPTS = {
    "formal": "Write a clear, professional caption summarizing this video.",
    "sarcastic": "Write a dry, sarcastic caption for this video.",
    "humorous_tech": "Write a funny, tech-flavored caption for this video (jokes about code/engineering).",
    "humorous_non_tech": "Write a light, funny caption for this video that anyone would get.",
}


def generate_captions(video_bytes: bytes, filename: str) -> dict[str, str]:
    """Return a caption for each of the four styles.

    This is the ONLY function the UI calls. It runs entirely offline: the
    uploaded clip is written to a temp file, processed into key frames, and a
    rule-based generator writes the four captions from that context.

    To go live later, swap the body for ``fetch_captions(...)`` (see the
    Fireworks scaffold below) — the signature and return shape stay the same.
    """
    suffix = os.path.splitext(filename or "")[1] or ".mp4"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(video_bytes)
        tmp.close()  # release the handle so OpenCV can read it (needed on Windows)

        frame_paths = extract_key_frames(tmp.name)
        context = build_video_context(tmp.name, frame_paths, original_name=filename)
        return generate_mock_captions(context)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    # ----- REAL CALL (uncomment & adapt on launch day) --------------------- #
    # import streamlit as st
    # api_key = st.secrets.get("FIREWORKS_API_KEY")
    # if not api_key:
    #     raise RuntimeError("Missing FIREWORKS_API_KEY in .streamlit/secrets.toml")
    # return fetch_captions(video_bytes, filename, api_key)


def fetch_captions(video_bytes: bytes, filename: str, api_key: str) -> dict[str, str]:
    """Call Fireworks once per style and return {style_key: caption}.

    NOTE: The exact payload depends on the launch-day model (whether it takes
    a video URL, frames, or a transcript). Adapt `_build_payload` accordingly.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    captions: dict[str, str] = {}
    for style_key, instruction in _STYLE_PROMPTS.items():
        payload = _build_payload(instruction, filename)
        response = requests.post(
            FIREWORKS_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        captions[style_key] = data["choices"][0]["message"]["content"].strip()

    return captions


def _build_payload(instruction: str, filename: str) -> dict:
    return {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a witty, accurate video captioner."},
            {"role": "user", "content": f"{instruction} (source clip: {filename})"},
        ],
        "max_tokens": 200,
        "temperature": 0.7,
    }
