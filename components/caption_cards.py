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
        "accent": "#d99e57",  # bronze (brand accent)
        "soft": "rgba(217,158,87,0.13)",
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
    """Lay the four cards out in a single full-width row (4 across)."""
    cols = st.columns(4, gap="medium")
    for col, style in zip(cols, STYLES):
        with col:
            render_caption_card(style, captions.get(style["key"], "—"))
