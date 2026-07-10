"""The four caption cards rendered as a 2×2 grid.

``STYLES`` is the single source of truth for the caption voices — it drives
the hero chips, the cards, and the download text. Add a style here and it
shows up everywhere automatically.
"""

from __future__ import annotations

import streamlit as st

from utils.helpers import esc

# The four required caption styles. Order here == order on screen.
# Accents are calibrated for the dark theme (components/theme.py): similar
# luminance, low saturation, so no single voice outshouts the bronze brand
# accent. They mark identity (dots, labels, hairlines) — never large fills.
STYLES: list[dict] = [
    {
        "key": "formal",
        "title": "Formal",
        "emoji": "📝",
        "blurb": "Clear, professional, to the point.",
        "accent": "#93aed6",  # dusty slate blue
        "soft": "rgba(147,174,214,0.13)",
    },
    {
        "key": "sarcastic",
        "title": "Sarcastic",
        "emoji": "😏",
        "blurb": "Dry wit with a raised eyebrow.",
        "accent": "#c79cc0",  # muted plum
        "soft": "rgba(199,156,192,0.13)",
    },
    {
        "key": "humorous_tech",
        "title": "Humorous · Tech",
        "emoji": "🤓",
        "blurb": "Jokes for people who read stack traces.",
        "accent": "#8ec4ae",  # sage teal
        "soft": "rgba(142,196,174,0.13)",
    },
    {
        "key": "humorous_non_tech",
        "title": "Humorous · Non-Tech",
        "emoji": "😂",
        "blurb": "Light, relatable, everybody laughs.",
        "accent": "#D4A15A",  # amber (brand accent)
        "soft": "rgba(212,161,90,0.14)",
    },
]


def render_caption_card(style: dict, caption: str) -> None:
    """Render a single caption card. All dynamic text is HTML-escaped."""
    tag = style["title"].split(" · ")[-1] if "·" in style["title"] else style["title"]
    st.markdown(
        f"""
        <div class="vc-card" style="--accent:{style['accent']};--soft:{style['soft']};">
          <span class="vc-tag">{esc(tag)}</span>
          <div class="head">
            <span class="ic">{style['emoji']}</span>
            <span class="name">{esc(style['title'])}</span>
          </div>
          <div class="blurb">{esc(style['blurb'])}</div>
          <div class="body">{esc(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_caption_grid(captions: dict[str, str]) -> None:
    """Render the four captions as a responsive card grid (auto-fit: 2-up on
    wide columns, 1-up when narrow) in a single markdown block, so it lays out
    cleanly below the player. All dynamic text is HTML-escaped.
    """
    # Single concatenated string (no indentation): st.markdown parses its
    # input as Markdown, where a 4+ space indent becomes a literal code block.
    cards = ""
    for style in STYLES:
        tag = (
            style["title"].split(" · ")[-1] if "·" in style["title"] else style["title"]
        )
        cards += (
            f'<div class="vc-card" style="--accent:{style["accent"]};--soft:{style["soft"]};">'
            f'<span class="vc-tag">{esc(tag)}</span>'
            '<div class="head">'
            f'<span class="ic">{style["emoji"]}</span>'
            f'<span class="name">{esc(style["title"])}</span>'
            "</div>"
            f'<div class="blurb">{esc(style["blurb"])}</div>'
            f'<div class="body">{esc(captions.get(style["key"], "—"))}</div>'
            "</div>"
        )
    st.markdown(f'<div class="vc-caps">{cards}</div>', unsafe_allow_html=True)
