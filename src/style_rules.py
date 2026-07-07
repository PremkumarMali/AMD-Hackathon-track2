"""Definitions for the four caption voices.

This is the backend's single source of truth for *how* each caption should
sound. ``caption_generator`` reads these rules to shape its output, and they
double as plain-English documentation of the project's captioning styles.

The four keys here MUST match the ``key`` values in
``components/caption_cards.py::STYLES`` so the generated captions line up with
the cards the frontend renders.
"""

from __future__ import annotations

STYLE_RULES: dict[str, dict] = {
    "formal": {
        "title": "Formal",
        "description": "Professional, clear and neutral — like a report caption.",
        "tone": ["professional", "concise", "neutral"],
        "guidelines": [
            "Use complete, grammatically correct sentences.",
            "Stay objective — describe, don't joke.",
            "Avoid slang, emoji and exclamation marks.",
        ],
    },
    "sarcastic": {
        "title": "Sarcastic",
        "description": "Witty and dry with light sarcasm — playful, never mean.",
        "tone": ["witty", "dry", "playful"],
        "guidelines": [
            "Lean on gentle irony and understatement.",
            "Tease the video, never a person.",
            "Keep it clean — no insults or offensive language.",
        ],
    },
    "humorous_tech": {
        "title": "Humorous · Tech",
        "description": "Funny, with a programming / AI / systems reference.",
        "tone": ["geeky", "playful", "clever"],
        "guidelines": [
            "Work in one light tech reference (code, AI, bugs, deploys).",
            "Keep jokes friendly and PG.",
            "One tech metaphor is plenty — don't drown it in jargon.",
        ],
    },
    "humorous_non_tech": {
        "title": "Humorous · Non-Tech",
        "description": "Funny and relatable — no technical knowledge needed.",
        "tone": ["light", "relatable", "cheerful"],
        "guidelines": [
            "Everyday humour anyone can get.",
            "No programming or technical terms.",
            "Keep it warm and family-friendly.",
        ],
    },
}

# Style order == the order the frontend expects on screen.
STYLE_KEYS: list[str] = list(STYLE_RULES.keys())


def get_style(style_key: str) -> dict:
    """Return the rule block for one style, or raise a clear error."""
    try:
        return STYLE_RULES[style_key]
    except KeyError:
        valid = ", ".join(STYLE_KEYS)
        raise KeyError(
            f"Unknown caption style {style_key!r}. Valid styles: {valid}"
        ) from None
