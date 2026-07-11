"""Mock / rule-based caption generator (offline fallback).

Turns a ``video_context`` dict (see ``video_utils.build_video_context``) into
four captions — one per voice defined in ``style_rules``. There is no model and
no network call, so the demo still works when Fireworks/Gemma is unavailable.

The mock has no real understanding of the footage, so its captions are kept
deliberately generic and content-neutral. Crucially, they NEVER mention the
filename, clip name, file extension, frame counts, or "key frames" — a fallback
caption should read like a caption, not like a file report. Output is
deterministic (same clip → same captions) so the demo is stable.

Public API:
    generate_mock_captions(video_context) -> dict[str, str]
"""

from __future__ import annotations

import hashlib

from .style_rules import STYLE_KEYS


def generate_mock_captions(video_context: dict) -> dict[str, str]:
    """Return one clean, content-neutral caption per style.

    Args:
        video_context: The dict produced by ``build_video_context``. Only
            coarse, non-identifying metadata is used (duration presence) — never
            the filename, clip name, or frame count.

    Returns:
        ``{"formal": ..., "sarcastic": ..., "humorous_tech": ...,
           "humorous_non_tech": ...}`` — keys matching the frontend styles.
    """
    if not isinstance(video_context, dict):
        raise TypeError(
            "video_context must be a dict from build_video_context()."
        )

    dur_label = video_context.get("duration_label") or ""
    has_dur = dur_label not in (None, "", "unknown")

    # Deterministic-but-varied: seed on coarse metadata (duration/resolution/
    # frame count) so different clips get different picks and the same clip is
    # stable — WITHOUT ever putting the filename into a caption.
    seed = "|".join(
        str(video_context.get(k) or "")
        for k in ("duration_seconds", "resolution", "frame_count")
    ) or "clip"

    pools = _build_pools(has_dur)
    return {key: _pick(pools[key], f"{key}:{seed}") for key in STYLE_KEYS}


def generate_mock_segment_captions(
    index: int, count: int, has_dur: bool = True
) -> dict[str, str]:
    """Clean generic captions for ONE timeline segment (offline fallback).

    Used when Fireworks is disabled or fails: each segment gets safe, generic
    captions that hint at their position in the clip (opening / middle /
    closing) so the timed overlay still progresses — but NEVER mention the
    filename, clip name, frame counts, or "key frames".

    Args:
        index: 0-based segment index.
        count: total number of segments.
        has_dur: unused flag kept for signature symmetry with the global mock.

    Returns:
        ``{formal, sarcastic, humorous_tech, humorous_non_tech}``.
    """
    lead = _position_lead(index, count)
    pools = _segment_pools(lead)
    seed = f"seg:{index}:{count}"
    return {key: _pick(pools[key], f"{key}:{seed}") for key in STYLE_KEYS}


def _position_lead(index: int, count: int) -> str:
    """A short, generic phrase describing where in the clip a segment sits."""
    if count <= 1:
        return ""
    if index == 0:
        return "Early on, "
    if index >= count - 1:
        return "Toward the end, "
    return "As the clip continues, "


def _cap(lead: str, body: str) -> str:
    """Join a position lead and a body, capitalising when there is no lead."""
    if not lead:
        return body[0].upper() + body[1:]
    return lead + body


def _segment_pools(lead: str) -> dict[str, list[str]]:
    """Clean, generic per-segment caption options (no filename/frame wording)."""
    formal = [
        "the video shows a scene with visible movement and changing on-screen "
        "elements.",
        "the footage presents an unfolding scene with steady on-screen activity.",
        "the clip follows a scene as it shifts and develops on screen.",
    ]
    sarcastic = [
        "a lot is clearly happening, even if the details are playing it cool.",
        "the scene is fully committed to keeping everyone guessing.",
        "it is riveting stuff, assuming the bar for riveting is set right here.",
    ]
    humorous_tech = [
        "the scene renders cleanly and the caption engine stays comfortably "
        "online.",
        "zero crashes, stable runtime, just footage doing its thing on screen.",
        "the visuals compile without errors, so this part ships straight to prod.",
    ]
    humorous_non_tech = [
        "something is clearly going on, and it has got real personality.",
        "the scene shows up ready to entertain and does not sit quietly.",
        "whatever is happening here, it is putting on a little show.",
    ]
    return {
        "formal": [_cap(lead, b) for b in formal],
        "sarcastic": [_cap(lead, b) for b in sarcastic],
        "humorous_tech": [_cap(lead, b) for b in humorous_tech],
        "humorous_non_tech": [_cap(lead, b) for b in humorous_non_tech],
    }


def _pick(options: list[str], seed_text: str) -> str:
    """Deterministically choose one option based on ``seed_text``.

    Same seed → same choice (stable demos); different seeds spread the picks.
    """
    if not options:
        return ""
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    return options[int(digest, 16) % len(options)]


def _build_pools(has_dur: bool) -> dict[str, list[str]]:
    """Assemble clean, content-neutral captions for each style.

    None of these reference the filename, clip name, file extension, frame
    count, "key frames", "sampled frames", "reviewed across", "record of", or
    "uploaded clip" — they describe a generic on-screen scene so the offline
    fallback still reads like a real caption.
    """
    formal = [
        "The video shows a scene with visible movement and changing on-screen "
        "elements.",
        "A short clip that follows an unfolding scene as it shifts and develops "
        "on screen.",
        "The footage presents a scene with steady on-screen activity from start "
        "to finish.",
    ]
    sarcastic = [
        "A lot is clearly happening here, even if the details are playing it "
        "cool.",
        "Riveting stuff — the scene is fully committed to keeping everyone "
        "guessing.",
        "Truly edge-of-your-seat material, assuming the seat is pulled right up "
        "to the screen.",
    ]
    humorous_tech = [
        "Scene rendered, pixels streaming, and the caption engine is still very "
        "much online.",
        "The visuals compiled without a single error, so this scene is shipping "
        "straight to prod.",
        "Runtime looks stable, zero crashes — just clean footage doing its "
        "thing on screen.",
    ]
    humorous_non_tech = [
        "Something is definitely happening on screen, and honestly, it has got "
        "personality.",
        "The scene showed up ready to entertain, and it did not come to sit "
        "quietly in the corner.",
        "Whatever is going on here, it is putting on a show and we are all here "
        "for it.",
    ]

    if has_dur:
        formal.append(
            "Over its brief runtime, the video follows a scene as it moves and "
            "changes on screen."
        )
        sarcastic.append(
            "A whole runtime of pure, understated drama — blink and you might "
            "miss the plot entirely."
        )
        humorous_tech.append(
            "Low latency, high vibes: the scene plays back smoother than most of "
            "my side projects."
        )
        humorous_non_tech.append(
            "A short watch that somehow packs in more character than it has any "
            "right to."
        )

    return {
        "formal": formal,
        "sarcastic": sarcastic,
        "humorous_tech": humorous_tech,
        "humorous_non_tech": humorous_non_tech,
    }
