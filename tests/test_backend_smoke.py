"""End-to-end smoke test for the backend.

Runnable straight from the project root with no extra setup:

    python tests/test_backend_smoke.py

It also works under pytest (``pytest tests/``) via ``test_backend_smoke``.

The test self-locates the project root, so it does not depend on the current
working directory or PYTHONPATH. It synthesizes a real short video, then
exercises:
  - src.frame_extractor.extract_key_frames
  - src.video_utils.build_video_context / get_video_metadata
  - src.caption_generator.generate_mock_captions
  - services.api_client.generate_captions  (the exact call the UI makes)

Terminal output is kept ASCII-only (no emoji / curly quotes) to avoid Windows
console encoding errors.
"""

import os
import sys
import tempfile

# Make the project root importable no matter where this test is launched from.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import cv2
import numpy as np

STYLE_KEYS = ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]


def _ascii(text):
    """Down-convert smart punctuation so any Windows console can print it."""
    return (
        str(text)
        .replace("“", '"').replace("”", '"')
        .replace("‘", "'").replace("’", "'")
        .replace("—", "-").replace("–", "-")
    )


def make_test_video(path, seconds=3, fps=30, size=(320, 240)):
    """Write a short synthetic clip. Tries a couple of codecs for portability."""
    for codec in ("mp4v", "XVID", "MJPG"):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(path, fourcc, fps, size)
        if writer.isOpened():
            break
        writer.release()
    else:
        raise RuntimeError("Could not open any VideoWriter codec on this machine.")

    total = seconds * fps
    for i in range(total):
        frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        c = int(255 * i / total)                 # a shifting background colour
        frame[:] = (c, 128, 255 - c)
        x = int((size[0] - 40) * i / total)      # a moving white block
        frame[100:140, x:x + 40] = (255, 255, 255)
        writer.write(frame)
    writer.release()
    return total


def check_captions(caps):
    assert isinstance(caps, dict), f"expected dict, got {type(caps)}"
    assert set(caps) == set(STYLE_KEYS), f"wrong keys: {sorted(caps)}"
    for k, v in caps.items():
        assert isinstance(v, str) and v.strip(), f"empty caption for {k!r}"


def run_smoke():
    from src.caption_generator import generate_mock_captions
    from src.frame_extractor import extract_key_frames
    from src.video_utils import build_video_context, get_video_metadata
    from services.api_client import generate_captions

    tmpdir = tempfile.mkdtemp()
    video_path = os.path.join(tmpdir, "beach_day.mp4")
    frames_dir = os.path.join(tmpdir, "frames")

    print("== 1. Synthesize a test video ==")
    total = make_test_video(video_path)
    print(f"   wrote {total} frames -> {video_path}")

    print("\n== 2. Metadata ==")
    meta = get_video_metadata(video_path)
    print("  ", meta)
    assert meta["frame_count"] > 0
    assert meta["duration_seconds"] and meta["duration_seconds"] > 0

    print("\n== 3. Frame extraction ==")
    frames = extract_key_frames(video_path, output_dir=frames_dir, max_frames=8)
    for f in frames:
        print("     ", os.path.basename(f), os.path.getsize(f), "bytes")
    assert 1 <= len(frames) <= 8
    assert all(os.path.isfile(f) for f in frames)

    print("\n== 4. Build context ==")
    ctx = build_video_context(video_path, frames, original_name="beach_day.mp4")
    for k, v in ctx.items():
        if k != "frame_paths":
            print(f"   {k}: {v}")

    print("\n== 5. generate_mock_captions(context) ==")
    caps = generate_mock_captions(ctx)
    check_captions(caps)
    for k in STYLE_KEYS:
        print(f"   [{k}] {_ascii(caps[k])}")

    print("\n== 6. Determinism (same clip -> same captions) ==")
    assert generate_mock_captions(ctx) == caps, "captions were not deterministic!"
    print("   OK: identical on repeat")

    print("\n== 7. Full UI bridge: api_client.generate_captions(bytes, name) ==")
    with open(video_path, "rb") as fh:
        video_bytes = fh.read()
    ui_caps = generate_captions(video_bytes, "beach_day.mp4")
    check_captions(ui_caps)
    for k in STYLE_KEYS:
        print(f"   [{k}] {_ascii(ui_caps[k])[:70]}...")

    print("\n== 8. Error handling: missing file ==")
    try:
        extract_key_frames(os.path.join(tmpdir, "nope.mp4"))
        raise AssertionError("expected a FileNotFoundError")
    except FileNotFoundError as e:
        print(f"   OK: raised FileNotFoundError -> {_ascii(e)}")

    print("\n== 9. Different filename -> different captions ==")
    ctx_b = build_video_context(video_path, frames, original_name="quarterly_report.mp4")
    caps_b = generate_mock_captions(ctx_b)
    differ = sum(1 for k in STYLE_KEYS if caps_b[k] != caps[k])
    print(f"   {differ}/4 styles differ from the first clip")
    assert differ > 0, "different clips should not produce identical captions"

    print("\nALL CHECKS PASSED")


def test_backend_smoke():
    """pytest entry point."""
    run_smoke()


if __name__ == "__main__":
    run_smoke()
