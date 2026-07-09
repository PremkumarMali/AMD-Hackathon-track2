"""Caption service — the bridge between the Streamlit UI and the backend.

``generate_captions()`` is the ONLY function the UI calls. It always processes
the uploaded clip into key frames and builds a video context, then:

  * if ``USE_FIREWORKS=1`` and a ``FIREWORKS_API_KEY`` is set, it tries
    Fireworks AI (a single vision request);
  * on ANY Fireworks failure — or when it is disabled/unconfigured — it falls
    back to the offline, rule-based mock generator.

Both paths return the same four-key dict, so the UI never changes and the app
never crashes because of an API problem. Config is read from a local ``.env``
(never committed); the API key is never printed or logged.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile

from dotenv import load_dotenv

# Make the project's `src/` backend importable no matter which directory
# Streamlit is launched from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.caption_generator import generate_mock_captions
from src.fireworks_client import (
    DEFAULT_MODEL,
    DEFAULT_TEXT_MODEL,
    generate_fireworks_captions,
)
from src.firebase_client import is_firebase_enabled, save_caption_run
from src.frame_extractor import extract_key_frames
from src.video_utils import build_video_context

# Load config from a local .env at the project root (never committed). Absent
# file is fine — load_dotenv just does nothing. override=False so an already-set
# environment variable (e.g. one forced by the tests) always wins.
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"), override=False)

# Same clip bytes -> same captions, so re-clicking "Generate" on one video does
# not spend more credits (and keeps the demo deterministic within a session).
_CAPTION_CACHE: dict[str, dict[str, str]] = {}


def generate_captions(video_bytes: bytes, filename: str) -> dict[str, str]:
    """Return a caption for each of the four styles (Fireworks or mock).

    Never raises for an API problem: any Fireworks failure degrades to the
    offline mock generator so the demo keeps working.
    """
    cache_key = hashlib.md5(video_bytes).hexdigest()
    if cache_key in _CAPTION_CACHE:
        return _CAPTION_CACHE[cache_key]

    suffix = os.path.splitext(filename or "")[1] or ".mp4"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(video_bytes)
        tmp.close()  # release the handle so OpenCV can read it (needed on Windows)

        frame_paths = extract_key_frames(tmp.name)
        context = build_video_context(tmp.name, frame_paths, original_name=filename)
        captions, mode = _caption_from_context(context, frame_paths)
        _CAPTION_CACHE[cache_key] = captions
        # Best-effort history write (Firestore). No-op unless Firebase is
        # enabled and configured; never raises, so it cannot break captioning.
        _save_run_history(filename, video_bytes, mode, captions)
        return captions
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _caption_from_context(
    context: dict, frame_paths: list[str]
) -> tuple[dict[str, str], str]:
    """Fireworks when enabled + configured; otherwise (or on failure) mock.

    Returns ``(captions, mode)`` where ``mode`` is ``"fireworks"`` or ``"mock"``
    so the caller can record which engine actually produced the captions. The
    caption generation itself is unchanged.
    """
    if _fireworks_enabled():
        api_key = os.environ.get("FIREWORKS_API_KEY", "").strip()
        model = os.environ.get("FIREWORKS_MODEL", "").strip() or None
        # Safe debug logging: booleans + model + exception only. Never the key,
        # request headers, or base64 image data.
        _log(f"enabled=True key_present={bool(api_key)} model={model or 'default'}")
        if api_key:
            try:
                captions = generate_fireworks_captions(
                    context, frame_paths, api_key, model
                )
                _log("success -> using Fireworks captions")
                return captions, "fireworks"
            except Exception as exc:  # noqa: BLE001 - any failure degrades to mock
                # The message from src.fireworks_client never contains the key.
                _log(f"failed ({type(exc).__name__}): {exc} -> falling back to mock")
        else:
            _log("no API key -> falling back to mock")
    return generate_mock_captions(context), "mock"


def _save_run_history(
    filename: str, video_bytes: bytes, mode: str, captions: dict[str, str]
) -> None:
    """Persist this caption run to Firestore (best-effort; never raises).

    Does nothing unless Firebase is enabled and configured. The models are only
    reported for the ``fireworks`` mode (mock captions use no model).
    """
    try:
        if not is_firebase_enabled():
            return
        fireworks = mode == "fireworks"
        record = {
            "filename": filename or "",
            "file_size_mb": round(len(video_bytes) / (1024 * 1024), 3),
            "generation_mode": mode,
            "vision_model": (
                (os.environ.get("FIREWORKS_MODEL", "").strip() or DEFAULT_MODEL)
                if fireworks
                else None
            ),
            "text_model": (
                (os.environ.get("FIREWORKS_TEXT_MODEL", "").strip() or DEFAULT_TEXT_MODEL)
                if fireworks
                else None
            ),
            "captions": {
                "formal": captions.get("formal", ""),
                "sarcastic": captions.get("sarcastic", ""),
                "humorous_tech": captions.get("humorous_tech", ""),
                "humorous_non_tech": captions.get("humorous_non_tech", ""),
            },
        }
        save_caption_run(record)
    except Exception as exc:  # noqa: BLE001 - history must never break captioning
        _log(f"history save skipped ({type(exc).__name__})")


def _log(message: str) -> None:
    """Emit a safe, prefixed debug line to stderr (no secrets ever)."""
    print(f"[fireworks] {message}", file=sys.stderr, flush=True)


def _fireworks_enabled() -> bool:
    """True only when USE_FIREWORKS is explicitly set to '1'."""
    return os.environ.get("USE_FIREWORKS", "0").strip() == "1"
