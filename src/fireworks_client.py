"""Fireworks AI caption client (optional, disabled by default).

Uses a robust TWO-CALL pipeline so a reasoning-style vision model does not have
to emit structured JSON directly (which was unreliable):

  Call 1 (vision):  send a few key frames -> a short plain-English scene
                    description (no JSON, no captions).
  Call 2 (text):    send that description -> the four styled captions as a
                    schema-constrained JSON object.

Safety guarantees:
  * only 3-4 downscaled frames are sent;
  * the API key is never printed, logged, or placed in an error message;
  * request headers, base64 image data, and chain-of-thought / reasoning text
    are never logged;
  * any failure in either call raises ``FireworksError`` so the caller can fall
    back to the offline mock generator.

Public API:
    generate_fireworks_captions(context, frame_paths, api_key, model, timeout=60)
    generate_scene_description(context, frame_paths, api_key, vision_model)
    generate_styled_captions_from_description(description, api_key, text_model)
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys

import cv2
import requests

# OpenAI-compatible chat-completions endpoint.
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"

# Default models. NOTE: ids change over time and must be accessible to your
# account — confirm in the dashboard. The vision model sees the frames; the
# text model formats the captions (configurable via FIREWORKS_TEXT_MODEL).
DEFAULT_MODEL = "accounts/fireworks/models/kimi-k2p6"
DEFAULT_TEXT_MODEL = "accounts/fireworks/models/gpt-oss-120b"

# The four style keys the frontend expects.
STYLE_KEYS = ("formal", "sarcastic", "humorous_tech", "humorous_non_tech")

# Credit-frugal frame settings.
MAX_FRAMES_SENT = 4
MAX_FRAME_DIM = 512      # longest side, px
JPEG_QUALITY = 70

# Per-call generation settings.
VISION_MAX_TOKENS = 512
VISION_TEMPERATURE = 0.4
CAPTION_MAX_TOKENS = 1024
CAPTION_TEMPERATURE = 0.2
MAX_DESC_CHARS = 1500   # cap the description passed to call 2 (token safety)

# Structured-output schema for call 2: forces exactly the four string fields.
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "video_captions",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {key: {"type": "string"} for key in STYLE_KEYS},
            "required": list(STYLE_KEYS),
            "additionalProperties": False,
        },
    },
}


class FireworksError(Exception):
    """Raised for any Fireworks failure (network, HTTP, no valid output)."""


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def generate_fireworks_captions(context, frame_paths, api_key, model=None, timeout=60):
    """Two-call pipeline: vision description -> schema-constrained captions.

    Args:
        context: dict from ``build_video_context``.
        frame_paths: extracted key-frame image paths.
        api_key: Fireworks API key (never logged).
        model: vision model id; falls back to ``DEFAULT_MODEL``.
        timeout: per-request timeout in seconds.

    Returns:
        ``{"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}`` -> str.

    Raises:
        FireworksError: on any failure in either call or invalid output.
    """
    if not api_key:
        raise FireworksError("Missing Fireworks API key.")

    vision_model = model or DEFAULT_MODEL
    text_model = _text_model()
    description = generate_scene_description(
        context, frame_paths, api_key, vision_model, timeout
    )
    return generate_styled_captions_from_description(
        description, api_key, text_model, timeout
    )


def generate_scene_description(context, frame_paths, api_key, vision_model, timeout=60):
    """Call 1: ask the vision model for a short plain-English scene description."""
    if not api_key:
        raise FireworksError("Missing Fireworks API key.")
    if not frame_paths:
        raise FireworksError("No frames available to send.")

    data_uris = _encode_frames(frame_paths)
    if not data_uris:
        raise FireworksError("Could not encode any frames for the request.")

    payload = {
        "model": vision_model or DEFAULT_MODEL,
        "messages": _build_vision_messages(context, data_uris),
        "max_tokens": VISION_MAX_TOKENS,
        "temperature": VISION_TEMPERATURE,
    }
    message = _post_chat(payload, api_key, timeout)
    description = _text_from_message(message)
    if not description:
        raise FireworksError("Vision model returned no scene description.")
    return description


def generate_styled_captions_from_description(description, api_key, text_model, timeout=60):
    """Call 2: turn the scene description into the four styled captions (JSON)."""
    if not api_key:
        raise FireworksError("Missing Fireworks API key.")
    if not description or not description.strip():
        raise FireworksError("Empty scene description for caption formatting.")

    payload = {
        "model": text_model or DEFAULT_TEXT_MODEL,
        "messages": _build_caption_messages(description),
        "max_tokens": CAPTION_MAX_TOKENS,
        "temperature": CAPTION_TEMPERATURE,
        "response_format": _RESPONSE_FORMAT,
    }
    message = _post_chat(payload, api_key, timeout)
    return _captions_from_message(message)


# --------------------------------------------------------------------------- #
# HTTP + config
# --------------------------------------------------------------------------- #

def _post_chat(payload, api_key, timeout):
    """POST one chat request and return the response ``message`` dict.

    Raises FireworksError on network/HTTP/shape problems. The key lives only in
    the headers and is never included in any error message.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(
            FIREWORKS_URL, headers=headers, json=payload, timeout=timeout
        )
    except requests.RequestException as exc:
        raise FireworksError(f"Network error contacting Fireworks: {exc}") from None
    if resp.status_code != 200:
        raise FireworksError(
            f"Fireworks returned HTTP {resp.status_code}: {_safe_snippet(resp.text)}"
        )
    try:
        return resp.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise FireworksError(f"Unexpected Fireworks response shape: {exc}") from None


def _text_model():
    """The configured text model for call 2 (env override or default)."""
    return (os.environ.get("FIREWORKS_TEXT_MODEL") or "").strip() or DEFAULT_TEXT_MODEL


def _text_from_message(message):
    """Extract plain description text from a message (content, else reasoning).

    Never printed/logged; only returned for internal use in call 2. Truncated
    to keep call 2's token usage bounded.
    """
    if not isinstance(message, dict):
        return ""
    text = message.get("content")
    if not (isinstance(text, str) and text.strip()):
        text = message.get("reasoning_content")
    if not (isinstance(text, str) and text.strip()):
        return ""
    return text.strip()[:MAX_DESC_CHARS]


# --------------------------------------------------------------------------- #
# Frame encoding
# --------------------------------------------------------------------------- #

def _select_frames(frame_paths, k):
    """Pick up to ``k`` evenly-spaced frames to limit credit usage."""
    n = len(frame_paths)
    if n <= k:
        return list(frame_paths)
    step = n / k
    return [frame_paths[int(step * i)] for i in range(k)]


def _downscale(img, max_dim):
    """Shrink so the longest side is <= ``max_dim`` (keeps requests small)."""
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_dim:
        return img
    scale = max_dim / longest
    return cv2.resize(
        img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
    )


def _encode_frames(frame_paths):
    """Read, downscale and base64-encode selected frames as JPEG data URIs."""
    uris = []
    for path in _select_frames(frame_paths, MAX_FRAMES_SENT):
        img = cv2.imread(path)
        if img is None:
            continue
        img = _downscale(img, MAX_FRAME_DIM)
        ok, buf = cv2.imencode(
            ".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        )
        if not ok:
            continue
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        uris.append(f"data:image/jpeg;base64,{b64}")
    return uris


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

def _build_vision_messages(context, data_uris):
    """Call 1 prompt: a short plain-English scene description (no JSON)."""
    duration = context.get("duration_label") or "unknown"
    nframes = context.get("num_frames_extracted") or len(data_uris)
    instruction = (
        f"These are {len(data_uris)} still frames sampled from a short video "
        f"(about {duration} long, {nframes} key frames total). In 2 to 4 short "
        "sentences of plain English, describe only what is visibly happening: "
        "the scene, the main subject or objects, colours, and any action or "
        "motion. Do not write captions, do not use JSON or markdown, and do not "
        "include any reasoning — just the description."
    )
    content = [{"type": "text", "text": instruction}]
    content += [{"type": "image_url", "image_url": {"url": uri}} for uri in data_uris]
    return [
        {
            "role": "system",
            "content": "You describe images accurately and concisely in plain "
                       "English.",
        },
        {"role": "user", "content": content},
    ]


def _build_caption_messages(description):
    """Call 2 prompt: turn the description into the four styled captions (JSON)."""
    instruction = (
        "Here is a description of a short video:\n\n"
        f"{description}\n\n"
        "Based on this description, write a REAL caption for the video in each of "
        "four styles. Return a JSON object with exactly four keys: formal, "
        "sarcastic, humorous_tech, humorous_non_tech.\n\n"
        "Style guide:\n"
        "- formal: professional and neutral.\n"
        "- sarcastic: witty with light sarcasm, not offensive.\n"
        "- humorous_tech: funny, with programming / AI / tech-style humor.\n"
        "- humorous_non_tech: funny but understandable without any tech terms.\n\n"
        "Each caption must be a complete sentence specific to the described "
        'video. Do not use placeholder text such as "..." or "caption here". '
        "Return only the JSON object with no extra text."
    )
    return [
        {
            "role": "system",
            "content": "You write short, vivid video captions and return only the "
                       "requested JSON object.",
        },
        {"role": "user", "content": instruction},
    ]


# --------------------------------------------------------------------------- #
# Response handling — balanced JSON scan + validation
# --------------------------------------------------------------------------- #

def _captions_from_message(message):
    """Pull the four captions from a message (content, then reasoning fallback)."""
    if not isinstance(message, dict):
        raise FireworksError("Unexpected Fireworks message shape.")
    caps = _extract_captions(message.get("content"))
    if caps is None:
        caps = _extract_captions(message.get("reasoning_content"))
    if caps is None:
        _emit_failure_debug(message)
        raise FireworksError("Fireworks did not return a valid 4-key JSON object.")
    return {k: caps[k].strip() for k in STYLE_KEYS}


def _extract_captions(text):
    """Return a normalised 4-key caption dict from the last valid JSON object
    found in ``text``, or ``None`` if there isn't one."""
    if not isinstance(text, str) or not text.strip():
        return None
    best = None
    for fragment in _balanced_json_objects(text):
        obj = _try_json(fragment)
        if obj is None:
            continue
        norm = _normalize_keys(obj)
        if _has_valid_captions(norm):
            best = norm  # keep the LAST valid object (the final answer)
    return best


def _balanced_json_objects(text):
    """Return every balanced ``{...}`` substring in ``text`` (string-aware)."""
    fragments = []
    n, i = len(text), 0
    while i < n:
        if text[i] == "{":
            depth = 0
            in_str = False
            esc = False
            j = i
            while j < n:
                c = text[j]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                else:
                    if c == '"':
                        in_str = True
                    elif c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            fragments.append(text[i:j + 1])
                            break
                j += 1
            i = j + 1
        else:
            i += 1
    return fragments


def _try_json(fragment):
    """Parse a fragment as a JSON dict, tolerating smart quotes / trailing commas."""
    candidates = (
        fragment,
        _normalize_smart_quotes(fragment),
        _remove_trailing_commas(fragment),
        _remove_trailing_commas(_normalize_smart_quotes(fragment)),
    )
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _normalize_smart_quotes(text):
    """Convert curly quotes to straight quotes so JSON can parse."""
    return (
        text.replace("“", '"').replace("”", '"')
        .replace("‘", "'").replace("’", "'")
    )


def _remove_trailing_commas(text):
    """Drop trailing commas before a closing } or ] (a common model slip)."""
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _normalize_keys(obj):
    """Lowercase keys and turn spaces/hyphens into underscores.

    e.g. ``"Humorous-Tech"`` / ``"humorous tech"`` / ``"humorous_non-tech"`` /
    ``"humorous non tech"`` -> ``"humorous_tech"`` / ``"humorous_non_tech"``.
    """
    out = {}
    for k, v in obj.items():
        nk = str(k).strip().lower().replace("-", "_").replace(" ", "_")
        out[nk] = v
    return out


# Guards against echoed placeholders / filler being accepted as real captions.
_MIN_CAPTION_LEN = 10
_PLACEHOLDER_VALUES = {
    "...", "placeholder", "caption", "caption here", "n/a", "none", "null",
    "string", "text",
}


def _looks_placeholder(value):
    """True if a caption value is a placeholder, generic filler, or too short."""
    s = value.strip()
    if len(s) < _MIN_CAPTION_LEN:
        return True
    if set(s) <= set(". "):  # only dots/spaces, e.g. "..." or ". . ."
        return True
    return s.lower() in _PLACEHOLDER_VALUES


def _has_valid_captions(d):
    """True if ``d`` has all four keys as real, non-placeholder captions."""
    for k in STYLE_KEYS:
        v = d.get(k)
        if not isinstance(v, str) or not v.strip() or _looks_placeholder(v):
            return False
    return True


# --------------------------------------------------------------------------- #
# Safe logging (never emits key, headers, base64, full response, or reasoning)
# --------------------------------------------------------------------------- #

def _emit_failure_debug(message):
    """Print only SAFE structural facts about an unparseable reply."""
    content = message.get("content")
    clen = len(content) if isinstance(content, str) else 0
    n_objs = len(_balanced_json_objects(content)) if isinstance(content, str) else 0
    has_reasoning = isinstance(message.get("reasoning_content"), str)
    print(
        f"[fireworks] no valid 4-key JSON found: content_len={clen} "
        f"balanced_objects={n_objs} reasoning_field_present={has_reasoning}",
        file=sys.stderr, flush=True,
    )


def _safe_snippet(text, limit=200):
    """A short, single-line slice of an HTTP error body for diagnostics."""
    return (text or "").replace("\n", " ")[:limit]
