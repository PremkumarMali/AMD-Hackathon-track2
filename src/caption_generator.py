"""Mock / rule-based caption generator.

Turns a ``video_context`` dict (see ``video_utils.build_video_context``) into
four captions — one per voice defined in ``style_rules``. There is no model
and no network call: the output is templated so the demo runs fully offline
and deterministically (the same clip always yields the same captions, while
different clips vary).

Public API:
    generate_mock_captions(video_context) -> dict[str, str]
"""

from __future__ import annotations

import hashlib

from .style_rules import STYLE_KEYS


def generate_mock_captions(video_context: dict) -> dict[str, str]:
    """Return one caption per style for the given video context.

    Args:
        video_context: The dict produced by ``build_video_context`` (needs at
            least ``clip_name``/``filename``, ``num_frames_extracted`` and
            ``duration_label``).

    Returns:
        ``{"formal": ..., "sarcastic": ..., "humorous_tech": ...,
           "humorous_non_tech": ...}`` — keys matching the frontend styles.
    """
    if not isinstance(video_context, dict):
        raise TypeError(
            "video_context must be a dict from build_video_context()."
        )

    name = _clip_label(video_context)
    nframes = int(video_context.get("num_frames_extracted") or 0)
    dur_label = video_context.get("duration_label") or "unknown"
    has_dur = dur_label not in (None, "", "unknown")
    seed = (
        video_context.get("clip_name")
        or video_context.get("filename")
        or "clip"
    )

    pools = _build_pools(name, nframes, dur_label, has_dur)
    return {key: _pick(pools[key], f"{key}:{seed}") for key in STYLE_KEYS}


def _clip_label(context: dict) -> str:
    """A tidy, human phrase for the clip — its cleaned name or 'your clip'."""
    raw = (context.get("clip_name") or "").strip()
    cleaned = raw.replace("_", " ").replace("-", " ").strip()
    if not cleaned or len(cleaned) > 40:
        return "your clip"
    return f"“{cleaned}”"  # curly-quoted, e.g. “beach day”


def _pick(options: list[str], seed_text: str) -> str:
    """Deterministically choose one option based on ``seed_text``.

    Same seed → same choice (stable demos); different seeds spread the picks.
    """
    if not options:
        return ""
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    return options[int(digest, 16) % len(options)]


def _build_pools(
    name: str,
    nframes: int,
    dur_label: str,
    has_dur: bool,
) -> dict[str, list[str]]:
    """Assemble the candidate captions for each style.

    Templates weave in the clip name and frame count (always known); a few
    duration-flavoured extras are added only when the duration is measurable,
    so captions never reference an unknown length.
    """
    formal = [
        f"A clear, professional record of {name}. Reviewed across {nframes} "
        f"key frames, it documents its subject and their actions in a "
        f"straightforward, easy-to-follow sequence.",
        f"This video presents a concise, self-contained sequence of events. "
        f"Its main subject and their actions are captured plainly and "
        f"accurately across {nframes} sampled frames.",
        f"An organised visual summary of {name}. The footage unfolds in a "
        f"logical order and is well suited to a general audience.",
    ]
    sarcastic = [
        f"Oh, {name}? Groundbreaking. Truly the kind of footage that changes "
        f"lives — all captured in a breezy {nframes} frames of pure, "
        f"unmatched drama.",
        f"Stop the presses: {name} has arrived. Someone alert the Academy, "
        f"because this is clearly the cinematic event of the century.",
        f"Wow, {nframes} whole key frames and I'm still on the edge of my "
        f"seat — said absolutely no one. But here we are, captioning it "
        f"anyway.",
    ]
    humorous_tech = [
        f"This clip runs in O(fun) time with zero memory leaks. I sampled "
        f"{nframes} frames and every one passed code review — ship it to "
        f"prod. On a Friday. No tests.",
        f"Ran {name} through the pipeline: {nframes} frames extracted, 0 "
        f"exceptions thrown, 100% vibes coverage. The build is green and so "
        f"am I with envy.",
        f"POV: your video compiles on the first try. {nframes} frames, no "
        f"null pointers, no merge conflicts — just clean footage and "
        f"good energy.",
    ]
    humorous_non_tech = [
        f"Plot twist: nobody expected {name} to be this entertaining. Grab "
        f"some popcorn — these {nframes} snapshots are doing the "
        f"absolute most.",
        f"Somewhere between frame one and frame {nframes}, this clip decided "
        f"it was the main character. Honestly? Iconic behaviour.",
        f"They said it was just a short video. They were wrong. {name} is a "
        f"whole mood, and we're all better for having watched it.",
    ]

    if has_dur:
        formal.append(
            f"Running about {dur_label}, {name} delivers a clear and orderly "
            f"account of its subject, reviewed here through {nframes} "
            f"representative frames."
        )
        sarcastic.append(
            f"A full {dur_label} of content and somehow every second counts "
            f"— allegedly. Bravo, {name}. Bravo."
        )
        humorous_tech.append(
            f"{dur_label} of runtime, {nframes} frames buffered, zero lag. "
            f"This clip has better uptime than most of my side projects."
        )
        humorous_non_tech.append(
            f"{dur_label} very well spent. {name} packs more personality into "
            f"that runtime than most people manage before their morning coffee."
        )

    return {
        "formal": formal,
        "sarcastic": sarcastic,
        "humorous_tech": humorous_tech,
        "humorous_non_tech": humorous_non_tech,
    }
