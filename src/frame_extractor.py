"""Key-frame extraction with OpenCV.

Given a path to a video file, pull a handful of evenly-spaced frames and save
them as JPEG images. These frames stand in for "what was looked at" when the
caption generator builds its (honest, mock) video context.

Public API:
    extract_key_frames(video_path, output_dir="frames", max_frames=8)
"""

from __future__ import annotations

import os

import cv2


class FrameExtractionError(Exception):
    """Raised when a video can't be opened or yields no usable frames."""


def extract_key_frames(
    video_path: str,
    output_dir: str = "frames",
    max_frames: int = 8,
) -> list[str]:
    """Extract evenly-spaced key frames from ``video_path``.

    Reads the video, samples up to ``max_frames`` frames at equal intervals,
    writes them as JPEGs into ``output_dir``, and returns the list of saved
    file paths in chronological order.

    Args:
        video_path: Path to a readable video file.
        output_dir: Folder to write the frame images into (created if needed).
        max_frames: Upper bound on how many frames to keep (default 8).

    Returns:
        A list of saved image paths (length 1..max_frames).

    Raises:
        FileNotFoundError: ``video_path`` does not exist.
        ValueError: ``max_frames`` is less than 1.
        FrameExtractionError: the file can't be opened or has no readable
            frames.
    """
    if not video_path or not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path!r}")
    if max_frames < 1:
        raise ValueError("max_frames must be at least 1.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        raise FrameExtractionError(
            f"Could not open video (unsupported or corrupt file): {video_path!r}"
        )

    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        os.makedirs(output_dir, exist_ok=True)

        saved: list[str] = []
        if frame_count > 0:
            indices = _even_indices(frame_count, max_frames)
            saved = _extract_by_seek(cap, indices, output_dir)

        # Fallback: metadata was unreliable (frame_count == 0) or seeking
        # produced nothing. Re-read the clip sequentially instead.
        if not saved:
            saved = _extract_by_scan(video_path, max_frames, output_dir)

        if not saved:
            raise FrameExtractionError(
                f"No frames could be read from video: {video_path!r}"
            )
        return saved
    finally:
        cap.release()


def _even_indices(frame_count: int, max_frames: int) -> list[int]:
    """Pick up to ``max_frames`` distinct frame indices spread across a clip.

    Sampling works in the interior of the video (skipping the exact first and
    last frame, which are often black) and never returns duplicates or an
    out-of-range index.
    """
    n = min(max_frames, frame_count)
    if n <= 0:
        return []
    if n == 1:
        return [frame_count // 2]

    step = frame_count / (n + 1)
    indices: list[int] = []
    for i in range(1, n + 1):
        idx = int(step * i)
        if idx < frame_count and idx not in indices:
            indices.append(idx)
    return indices


def _save_frame(frame, output_dir: str, position: int) -> str | None:
    """Write one frame to ``output_dir``; return its path (or None on failure)."""
    path = os.path.join(output_dir, f"frame_{position:02d}.jpg")
    # imwrite returns False (rather than raising) if the write fails.
    if cv2.imwrite(path, frame):
        return path
    return None


def _extract_by_seek(cap, indices: list[int], output_dir: str) -> list[str]:
    """Seek to each target index and save that frame."""
    saved: list[str] = []
    for position, idx in enumerate(indices, start=1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        path = _save_frame(frame, output_dir, position)
        if path:
            saved.append(path)
    return saved


def _extract_by_scan(video_path: str, max_frames: int, output_dir: str) -> list[str]:
    """Seek-free fallback for files whose frame count / seeking is unreliable.

    Uses two sequential passes (fresh captures, no seeking): one to count the
    readable frames, one to save the evenly-spaced targets. O(1) memory.
    """
    total = _count_frames(video_path)
    if total == 0:
        return []

    targets = set(_even_indices(total, max_frames))
    cap = cv2.VideoCapture(video_path)
    try:
        saved: list[str] = []
        position = 0
        idx = 0
        ok, frame = cap.read()
        while ok:
            if idx in targets:
                position += 1
                path = _save_frame(frame, output_dir, position)
                if path:
                    saved.append(path)
            idx += 1
            ok, frame = cap.read()
        return saved
    finally:
        cap.release()


def _count_frames(video_path: str) -> int:
    """Count readable frames by reading the clip once (no seeking)."""
    cap = cv2.VideoCapture(video_path)
    try:
        total = 0
        ok, _ = cap.read()
        while ok:
            total += 1
            ok, _ = cap.read()
        return total
    finally:
        cap.release()
