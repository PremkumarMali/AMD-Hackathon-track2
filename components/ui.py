"""Reusable UI primitives for the dashboard.

Small, composable building blocks — each renders one design-system
component. All styling lives in the app stylesheet (components/app.py)
under a matching ``.vc-*`` selector and references tokens from
components/theme.py; these functions only produce structure.

Rules for this module:
    • Every user- or model-controlled string is escaped with ``esc``.
    • No inline hex values — voice colors come through STYLES accents.
    • No component knows about session state; callers pass plain data.
    • Icons are inline Lucide-style SVG strings (ICONS) — premium, restrained.
"""

from __future__ import annotations

from textwrap import dedent

import streamlit as st

from utils.helpers import esc


def _html(block: str) -> None:
    """Render an HTML fragment through st.markdown, safely.

    st.markdown parses its input as *Markdown*: a blank line terminates an
    HTML block, and any following line indented 4+ spaces renders as a
    literal code block — raw HTML on screen. Dropping blank lines and all
    leading indentation removes both traps entirely, so components can
    format their markup readably without corrupting the page. (Newlines
    between tags still count as whitespace in HTML, so rendering is
    unchanged; nothing here emits <pre> content.)
    """
    block = "\n".join(
        line.strip() for line in dedent(block).splitlines() if line.strip()
    )
    st.markdown(block, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Icons — inline, currentColor, Lucide-style (premium + restrained)
# --------------------------------------------------------------------------- #

def _svg(path: str, size: int = 18, fill: bool = False) -> str:
    """Wrap SVG inner markup in a sized <svg>. ``fill`` toggles solid glyphs."""
    stroke = "" if fill else (
        'fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round"'
    )
    fillattr = 'fill="currentColor"' if fill else stroke
    return (
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" {fillattr}>{path}</svg>'
    )


ICONS: dict[str, str] = {
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "clip":  '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/>',
    "lines": '<path d="M4 6h16M4 12h16M4 18h11"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "spark": '<path d="M12 3v3m0 12v3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M3 12h3m12 0h3M5.6 18.4l2.1-2.1m8.6-8.6 2.1-2.1"/><circle cx="12" cy="12" r="3"/>',
    "play":  '<path d="M8 5v14l11-7z"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "up":    '<path d="M5 12l7-7 7 7M12 5v14"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8M21 7v5h-5"/>',
}


def icon(name: str, size: int = 18, fill: bool = False) -> str:
    """Return inline SVG markup for a named icon (string, not rendered)."""
    return _svg(ICONS.get(name, ""), size=size, fill=fill)


# --------------------------------------------------------------------------- #
# Shell
# --------------------------------------------------------------------------- #

def top_nav(brand: str, tag: str, status: str) -> None:
    """Glass navigation bar: brand + product tag left; engine badge, settings
    and profile right. A pulsing dot marks live status."""
    _html(
        f"""
        <div class="vc-nav">
          <div class="vc-nav-l">
            <span class="vc-logo">&#10022;</span>
            <span class="vc-brand">{esc(brand)}</span>
            <span class="vc-navtag">{esc(tag)}</span>
          </div>
          <div class="vc-nav-r">
            <span class="vc-status"><span class="dot"></span>{esc(status)}</span>
            <span class="vc-iconbtn" role="img" aria-label="Settings">{icon("settings", 17)}</span>
            <span class="vc-avatar">PK</span>
          </div>
        </div>
        """
    )


def page_header(kicker: str, title: str, sub: str, chips: list[dict]) -> None:
    """Editorial hero: kicker + animated-gradient H1 + support line, with the
    voice identities as pills. ``chips``: [{"title", "accent"}, …]."""
    chip_html = "".join(
        f'<span class="vc-chip"><span class="dot" style="background:{esc(c["accent"])}"></span>'
        f'{esc(c["title"])}</span>'
        for c in chips
    )
    _html(
        f"""
        <div class="vc-hero">
          <p class="vc-eyebrow">{esc(kicker)}</p>
          <h1 class="vc-herotitle">{esc(title)}</h1>
          <p class="vc-herosub">{esc(sub)}</p>
          <div class="vc-chips">{chip_html}</div>
        </div>
        """
    )


def footer(text: str) -> None:
    _html(f'<div class="vc-foot">{text}</div>')


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #

def section(marker: str, title: str, meta: str | None = None,
            tight: bool = False) -> None:
    """Section header; optional right-aligned meta note. ``marker`` is a short
    label (icon name or symbol) shown in a chip before the title. ``tight``
    collapses the top margin — used when a header follows tall media closely."""
    meta_html = f'<span class="m">{esc(meta)}</span>' if meta else ""
    chip = icon(marker, 16) if marker in ICONS else esc(marker)
    cls = "vc-step tight" if tight else "vc-step"
    # Real <h2> so the page has a screen-reader heading outline under the
    # page's single <h1>; .vc-step .t styling resets the default h2 margin.
    _html(
        f'<div class="{cls}"><span class="n">{chip}</span>'
        f'<h2 class="t">{esc(title)}</h2>{meta_html}</div>'
    )


# --------------------------------------------------------------------------- #
# Data display
# --------------------------------------------------------------------------- #

def stat_row(stats: list[dict]) -> None:
    """Row of premium stat cards. ``stats``: [{"label","value","note","icon",
    "trend"?}, …]. Values render in the display serif; pass "—" for zero
    states rather than hiding the card, so the grid never jumps. ``trend`` is
    optional small print (e.g. "live") shown top-right."""
    # Compact, single-line markup: st.markdown parses this as Markdown, and
    # lines indented 4+ spaces inside a mixed-indentation block become a
    # literal code block (raw HTML on screen). Never emit indented children
    # inside an unindented wrapper here.
    cards = "".join(
        '<div class="vc-stat">'
        f'<span class="ic">{icon(s.get("icon", "spark"), 17)}</span>'
        + (f'<span class="trend">{icon("trend", 12)}{esc(s["trend"])}</span>'
           if s.get("trend") else "")
        + f'<span class="val">{esc(s["value"])}</span>'
        f'<span class="lab">{esc(s["label"])}</span>'
        f'<span class="note">{esc(s["note"])}</span>'
        "</div>"
        for s in stats
    )
    _html(f'<div class="vc-stats">{cards}</div>')


def ai_status_card(title: str, message: str, state: str = "ready") -> None:
    """Glass 'AI engine' status card. ``state``: "ready" | "busy"."""
    label = "Working" if state == "busy" else "Ready"
    _html(
        f"""
        <div class="vc-ai">
          <span class="orb">{icon("spark", 20)}</span>
          <span class="txt"><b>{esc(title)}</b><span>{esc(message)}</span></span>
          <span class="state {esc(state)}">{esc(label)}</span>
        </div>
        """
    )


def badge(label: str, kind: str = "ok") -> str:
    """Return badge markup (string, not rendered) for embedding in cards."""
    return f'<span class="vc-badge {esc(kind)}">{esc(label)}</span>'


def activity_timeline(rows: list[dict]) -> None:
    """Session activity as Linear-style cards, newest first.

    ``rows``: [{"clip","size","voices","elapsed","at","status","kind"}, …].
    ``kind`` is a badge kind: "ok" | "err".
    """
    # Single-line cards for the same reason as stat_row: indented multi-line
    # markup inside a template risks Markdown's indented-code-block rule.
    ok_check = icon("check", 12)
    play = icon("play", 15, fill=True)
    cards = "".join(
        '<div class="vc-act">'
        f'<span class="thumb">{play}</span>'
        '<span class="info">'
        f'<b>{esc(r["clip"])}</b>'
        f'<span class="row"><span>{esc(r["at"])}</span><i>·</i>'
        f'<span class="v">{esc(r["voices"])} voices</span><i>·</i>'
        f'<span>{esc(r["elapsed"])}</span><i>·</i><span>{esc(r["size"])}</span></span>'
        "</span>"
        + (f'<span class="ok">{ok_check}Done</span>'
           if r["kind"] == "ok"
           else f'<span class="fail">{esc(r["status"])}</span>')
        + "</div>"
        for r in reversed(rows)
    )
    _html(f'<div class="vc-timeline">{cards}</div>')


# --------------------------------------------------------------------------- #
# States
# --------------------------------------------------------------------------- #

def empty_state(title: str, body: str, icon_name: str = "clip") -> None:
    """Quiet, designed empty state — used wherever data hasn't arrived yet."""
    _html(
        f"""
        <div class="vc-empty">
          <span class="ico">{icon(icon_name, 24)}</span>
          <h3>{esc(title)}</h3>
          <p>{esc(body)}</p>
        </div>
        """
    )


def skeleton_player(status: str) -> None:
    """Loading state shaped like the captioned player it will become.

    Communicates *what* is loading, not just *that* something is —
    the stage, the four voice buttons, and a status line.
    """
    _html(
        f"""
        <div class="vc-skelwrap">
          <div class="vc-skel bar w-40"></div>
          <div class="vc-skel stage"><span class="vc-skelspin"></span></div>
          <div class="vc-skelrow">
            <div class="vc-skel btn"></div>
            <div class="vc-skel btn"></div>
            <div class="vc-skel btn"></div>
            <div class="vc-skel btn"></div>
          </div>
        </div>
        <p class="vc-skelnote">{esc(status)}</p>
        """
    )
