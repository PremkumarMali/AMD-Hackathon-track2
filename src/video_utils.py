"""Video metadata + honest "video context" helpers.

Two small jobs:
  1. Read basic technical metadata from a clip (fps, frame count, duration).
  2. Assemble a plain, honest ``video_context`` dict that the caption
     generator turns into captions.

We deliberately do NOT pretend to understand the video's content. The scene
description is an explicit placeholder — see ``build_video_context``.
"""

from __future__ import annotations

import os

import cv2


def get_video_metadata(video_path: str) -> dict:
    """Return basic technical metadata for a clip.

    Keys: ``fps``, ``frame_count``, ``duration_seconds``, ``width``,
    ``height``. Anything OpenCV can't measure comes back as ``None`` (or ``0``
    for ``frame_count``). Never raises for a readable file.
    """
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            return {
                "fps": None,
                "frame_count": 0,
                "duration_seconds": None,
                "width": None,
                "height": None,
            }
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
        duration = frame_count / fps if fps > 0 and frame_count > 0 else None
        return {
            "fps": round(fps, 2) if fps > 0 else None,
            "frame_count": frame_count,
            "duration_seconds": round(duration, 1) if duration else None,
            "width": width,
            "height": height,
        }
    finally:
        cap.release()


def format_duration(seconds: float | None) -> str:
    """Seconds → ``'M:SS'`` label, or ``'unknown'`` when unmeasured."""
    if not seconds or seconds <= 0:
        return "unknown"
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def build_video_context(
    video_path: str,
    frame_paths: list[str],
    original_name: str | None = None,
) -> dict:
    """Build an honest context dict describing the processed clip.

    This is exactly what the (mock) caption generator reads. It contains only
    facts we can actually measure, plus an explicit placeholder scene
    description — no pretend "AI understanding" of the footage.

    Args:
        video_path: Path to the clip (used to read metadata).
        frame_paths: Paths returned by ``extract_key_frames``.
        original_name: The user-facing filename to display. Falls back to the
            basename of ``video_path`` (useful when the clip was saved to a
            temporary path first).
    """
    meta = get_video_metadata(video_path)
    display_name = original_name or os.path.basename(video_path)
    return {
        "filename": display_name,
        "clip_name": os.path.splitext(os.path.basename(display_name))[0],
        "num_frames_extracted": len(frame_paths),
        "frame_paths": list(frame_paths),
        "frame_count": meta["frame_count"],
        "fps": meta["fps"],
        "duration_seconds": meta["duration_seconds"],
        "duration_label": format_duration(meta["duration_seconds"]),
        "resolution": (
            f"{meta['width']}x{meta['height']}"
            if meta["width"] and meta["height"]
            else None
        ),
        "scene_description": "A short video clip.",
    }
