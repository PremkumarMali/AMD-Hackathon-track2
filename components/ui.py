"""Reusable UI primitives for the dashboard.

Small, composable building blocks — each renders one design-system
component. All styling lives in the app stylesheet (components/app.py)
under a matching ``.vc-*`` selector and references tokens from
components/theme.py; these functions only produce structure.

Rules for this module:
    • Every user- or model-controlled string is escaped with ``esc``.
    • No inline hex values — voice colors come through STYLES accents.
    • No component knows about session state; callers pass plain data.
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
# Shell
# --------------------------------------------------------------------------- #

def top_nav(brand: str, tag: str, status: str) -> None:
    """Top bar: brand identity left, product tag + live status right."""
    _html(
        f"""
        <div class="vc-nav">
          <div class="vc-brand"><span class="mark">&#10022;</span> {esc(brand)}</div>
          <div class="vc-nav-side">
            <span class="tag">{esc(tag)}</span>
            <span class="vc-status"><span class="dot"></span>{esc(status)}</span>
          </div>
        </div>
        """
    )


def page_header(kicker: str, title: str, sub: str, chips: list[dict]) -> None:
    """Compact dashboard header: kicker + H1 + support line, voice chips right.

    ``chips``: [{"title": str, "accent": str}, …] — the voice identities.
    """
    chip_html = "".join(
        f'<span class="vc-chip"><span class="dot" style="background:{esc(c["accent"])}"></span>'
        f'{esc(c["title"])}</span>'
        for c in chips
    )
    _html(
        f"""
        <div class="vc-pagehead">
          <div>
            <p class="vc-eyebrow">{esc(kicker)}</p>
            <h1>{esc(title)}</h1>
            <p class="sub">{esc(sub)}</p>
          </div>
          <div class="vc-chips">{chip_html}</div>
        </div>
        """
    )


def footer(text: str) -> None:
    _html(f'<div class="vc-foot">{text}</div>')


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #

def section(marker: str, title: str, meta: str | None = None) -> None:
    """Numbered section header; optional right-aligned meta note."""
    meta_html = f'<span class="m">{esc(meta)}</span>' if meta else ""
    _html(
        f'<div class="vc-step"><span class="n">{esc(marker)}</span>'
        f'<span class="t">{esc(title)}</span>{meta_html}</div>'
    )


# --------------------------------------------------------------------------- #
# Data display
# --------------------------------------------------------------------------- #

def stat_row(stats: list[dict]) -> None:
    """Row of stat cards. ``stats``: [{"label", "value", "note"}, …].

    Values render in the display serif; pass "—" for zero states rather
    than hiding the card, so the grid never jumps.
    """
    # Compact, single-line markup: st.markdown parses this as Markdown, and
    # lines indented 4+ spaces inside a mixed-indentation block become a
    # literal code block (raw HTML on screen). Never emit indented children
    # inside an unindented wrapper here.
    cards = "".join(
        '<div class="vc-stat">'
        f'<span class="lab">{esc(s["label"])}</span>'
        f'<span class="val">{esc(s["value"])}</span>'
        f'<span class="note">{esc(s["note"])}</span>'
        "</div>"
        for s in stats
    )
    _html(f'<div class="vc-stats">{cards}</div>')


def badge(label: str, kind: str = "ok") -> str:
    """Return badge markup (string, not rendered) for embedding in tables."""
    return f'<span class="vc-badge {esc(kind)}">{esc(label)}</span>'


def activity_table(rows: list[dict]) -> None:
    """Session activity log, newest first.

    ``rows``: [{"clip", "size", "voices", "elapsed", "at", "status", "kind"}, …]
    ``kind`` is a badge kind: "ok" | "err".
    """
    # Single-line rows for the same reason as stat_row: indented multi-line
    # markup inside a template risks Markdown's indented-code-block rule.
    body = "".join(
        "<tr>"
        f'<td class="clip">{esc(r["clip"])}</td>'
        f'<td>{esc(r["size"])}</td>'
        f'<td>{esc(r["voices"])}</td>'
        f'<td>{esc(r["elapsed"])}</td>'
        f'<td>{esc(r["at"])}</td>'
        f'<td>{badge(r["status"], r["kind"])}</td>'
        "</tr>"
        for r in reversed(rows)
    )
    _html(
        '<div class="vc-tablewrap"><table class="vc-table">'
        "<thead><tr><th>Clip</th><th>Size</th><th>Voices</th>"
        "<th>Generated in</th><th>At</th><th>Status</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


# --------------------------------------------------------------------------- #
# States
# --------------------------------------------------------------------------- #

def empty_state(title: str, body: str) -> None:
    """Quiet, designed empty state — used wherever data hasn't arrived yet."""
    _html(
        f"""
        <div class="vc-empty">
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
          <div class="vc-skel stage"></div>
          <div class="vc-skelside">
            <div class="vc-skel bar w-40"></div>
            <div class="vc-skel btn"></div>
            <div class="vc-skel btn"></div>
            <div class="vc-skel btn"></div>
            <div class="vc-skel btn"></div>
            <div class="vc-skel bar w-60"></div>
          </div>
        </div>
        <p class="vc-skelnote">{esc(status)}</p>
        """
    )
