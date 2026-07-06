"""Fireworks AI API client.

This is the bridge between the Streamlit UI and the caption model. Swap the
`_STYLE_PROMPTS` and endpoint details for whatever the launch-day model spec
requires. The function signature is what `app.py::generate_captions` expects.
"""

from __future__ import annotations

import time

import requests

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

    This is the ONLY function the UI calls. Today it returns a mock so the
    demo runs offline; to go live, uncomment the REAL CALL block below and
    supply ``FIREWORKS_API_KEY`` via ``.streamlit/secrets.toml``.
    """
    # ----- MOCK RESPONSE (safe placeholder for the demo) ------------------- #
    time.sleep(1.6)  # simulate model latency so the spinner is visible

    name = filename or "your clip"
    return {
        "formal": (
            f"The video presents a concise sequence of events captured in "
            f"“{name}”. It documents the primary subject and its actions in a "
            f"clear, straightforward manner suitable for a general audience."
        ),
        "sarcastic": (
            "Oh wow, groundbreaking footage. Truly the kind of content that "
            "changes lives. Someone alert the Academy — a masterpiece has "
            "arrived, and it's about 30 seconds long."
        ),
        "humorous_tech": (
            "This clip runs in O(fun) time with zero memory leaks. 10/10 would "
            "deploy to prod on a Friday. No exceptions thrown, only vibes."
        ),
        "humorous_non_tech": (
            "Plot twist: nobody expected this to be that entertaining. Grab "
            "some popcorn — this little clip is doing the absolute most."
        ),
    }

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
