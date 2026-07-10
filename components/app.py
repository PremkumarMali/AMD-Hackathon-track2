"""Main application UI logic — the dashboard page.

Wires together the pieces:
    • design tokens              → components.theme (single source of truth)
    • reusable primitives        → components.ui (nav, stats, timeline, states)
    • upload                     → components.video_preview
    • caption voice definitions  → components.caption_cards.STYLES
    • timed-subtitle player      → components.video_captioner
    • the model call             → services.api_client.generate_captions
    • validation / formatting    → utils.helpers

Layout is an asymmetric SaaS workspace: a glass nav, an editorial hero, a
row of stat cards, then a two-column workspace — upload + recent activity on
the left, the cinematic captioned player + AI status on the right. The
workflow is unchanged: captions are generated automatically on upload and
play on the clip as YouTube-style subtitles.

Run with:  streamlit run main.py
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import streamlit as st

from components import ui
from components.caption_cards import STYLES, render_caption_grid
from components.theme import css_variables
from components.video_captioner import can_inline, render_captioned_player
from components.video_preview import render_uploader
from services.api_client import generate_captions  # importing loads .env
from utils.helpers import (
    MAX_FILE_MB,
    captions_as_text,
    esc,
    load_brand_font_css,
    size_in_mb,
)

PAGE_TITLE = "Caption Studio"
PAGE_ICON = "✦"

logger = logging.getLogger(__name__)


def _fireworks_live() -> bool:
    """True when the backend will call Fireworks (flag on + key present).

    Mirrors services.api_client's checks; the .env is already loaded by the
    time this runs because importing generate_captions loads it.
    """
    return (
        os.environ.get("USE_FIREWORKS", "0").strip() == "1"
        and bool(os.environ.get("FIREWORKS_API_KEY", "").strip())
    )


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #

def inject_css() -> None:
    font_face = load_brand_font_css("Mortane")
    st.markdown(
        f"""
        <style>
        {font_face}
        {css_variables()}

        /* ---- App shell + ambient walnut lighting ---- */
        /* The warm glows + blurred orbs live in the shell's OWN background
           (background-attachment:fixed pins them to the viewport). This keeps
           them permanently behind content — a fixed full-screen overlay was
           painting on top and hiding the whole page. */
        .stApp {{
            background:
              radial-gradient(52% 40% at 82% -8%, rgba(212,161,90,.16), transparent 60%),
              radial-gradient(44% 38% at 4% 6%, rgba(120,86,42,.14), transparent 62%),
              radial-gradient(60% 55% at 50% 116%, rgba(90,64,32,.13), transparent 60%),
              radial-gradient(360px 360px at 88% 2%, rgba(212,161,90,.22), transparent 64%),
              radial-gradient(320px 320px at 4% 96%, rgba(243,199,125,.12), transparent 64%),
              var(--bg);
            background-attachment: fixed;
        }}

        .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="block-container"] {{
            max-width: 1320px !important; margin: 0 auto !important;
            padding-top: 1.4rem !important; padding-bottom: 4rem !important;
            padding-left: clamp(1.25rem, 4vw, 3rem) !important;
            padding-right: clamp(1.25rem, 4vw, 3rem) !important; }}
        html, body, [class*="css"] {{ font-family: var(--font-body); color: var(--ink); }}

        /* Hide default chrome for a cleaner "product" look */
        #MainMenu, footer {{ visibility: hidden; }}
        [data-testid="stHeader"], header {{ background: transparent !important; }}
        [data-testid="stHeader"] {{ height: 0 !important; }}
        [data-testid="stDecoration"] {{ display: none !important; }}
        [data-testid="stToolbar"] {{ display: none !important; }}
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none; }}

        /* ---- Focus (keyboard) ---- */
        .stApp :focus-visible {{
            outline: 2px solid var(--accent-2) !important; outline-offset: 2px;
            border-radius: var(--r-sm); }}

        /* ---- Glass navigation bar ---- */
        .vc-nav {{ position:sticky; top:10px; z-index:60; display:flex; align-items:center;
            justify-content:space-between; gap:var(--s-4); padding:12px 18px; margin-bottom:var(--s-6);
            border:1px solid var(--glass-line); border-radius:var(--r-lg);
            background:var(--glass-bg); backdrop-filter:var(--blur); -webkit-backdrop-filter:var(--blur);
            box-shadow:var(--shadow-1); }}
        .vc-nav-l {{ display:flex; align-items:center; gap:12px; min-width:0; }}
        .vc-nav-r {{ display:flex; align-items:center; gap:12px; }}
        .vc-logo {{ width:32px; height:32px; flex:none; display:grid; place-items:center;
            border-radius:10px; font-size:16px; color:var(--on-accent);
            background:linear-gradient(150deg, var(--accent-2), #a8763a);
            box-shadow:inset 0 1px 0 rgba(255,255,255,.4); }}
        .vc-brand {{ font-family:var(--font-display); font-weight:600; font-size:1.35rem;
            letter-spacing:.01em; color:var(--ink); }}
        .vc-navtag {{ font-size:var(--text-label); font-weight:600; letter-spacing:.2em;
            text-transform:uppercase; color:var(--ink-3); padding-left:10px; margin-left:2px;
            border-left:1px solid var(--line); }}
        @media (max-width:640px) {{ .vc-navtag {{ display:none; }} }}
        .vc-status {{ display:inline-flex; align-items:center; gap:8px; padding:7px 14px;
            border:1px solid var(--line); border-radius:999px; background:var(--surface);
            font-size:.74rem; font-weight:600; letter-spacing:.06em; color:var(--ink-2); }}
        .vc-status .dot {{ width:7px; height:7px; border-radius:50%; background:var(--ok);
            box-shadow:0 0 0 0 rgba(110,207,142,.5); animation: vc-pulse 2.4s var(--ease) infinite; }}
        @keyframes vc-pulse {{
            0% {{ box-shadow:0 0 0 0 rgba(110,207,142,.45); }}
            70% {{ box-shadow:0 0 0 7px rgba(110,207,142,0); }}
            100% {{ box-shadow:0 0 0 0 rgba(110,207,142,0); }} }}
        .vc-iconbtn {{ width:38px; height:38px; display:grid; place-items:center; border-radius:11px;
            border:1px solid var(--line); background:var(--surface); color:var(--ink-2);
            transition: color var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease); }}
        .vc-iconbtn:hover {{ color:var(--ink); border-color:var(--line-2); }}
        .vc-avatar {{ width:38px; height:38px; display:grid; place-items:center; border-radius:11px;
            font-weight:700; font-size:.8rem; color:var(--accent-2);
            background:linear-gradient(150deg,#3a2c18,#241a0f); border:1px solid var(--line-2); }}

        /* ---- Editorial hero ---- */
        .vc-hero {{ position:relative; padding: var(--s-5) 2px var(--s-2); }}
        .vc-hero::before {{ content:""; position:absolute; left:-4%; top:-30%; width:52%; height:150%;
            background:radial-gradient(60% 60% at 40% 50%, rgba(212,161,90,.18), transparent 70%);
            filter:blur(30px); pointer-events:none; z-index:0; }}
        .vc-eyebrow {{ position:relative; font-size:.72rem; font-weight:600; letter-spacing:.26em;
            text-transform:uppercase; color:var(--accent); margin:0 0 var(--s-3); }}
        .vc-herotitle {{ position:relative; font-family:var(--font-display); font-weight:600;
            font-size:var(--text-display); line-height:1.02; margin:0 0 var(--s-4);
            letter-spacing:-0.015em; max-width:16ch; text-wrap:balance;
            background:linear-gradient(96deg,#f6efe1 12%, var(--accent-2) 52%, #c98f47 90%);
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
            background-size:220% auto; animation: vc-shimmer-text 9s linear infinite; }}
        @keyframes vc-shimmer-text {{ to {{ background-position:220% center; }} }}
        .vc-herosub {{ position:relative; color:var(--ink-2); font-size:1.05rem; line-height:1.65;
            max-width:56ch; margin:0 0 var(--s-5); }}
        .vc-chips {{ position:relative; display:flex; flex-wrap:wrap; gap:var(--s-2); }}
        .vc-chip {{ display:inline-flex; align-items:center; gap:8px; padding:7px 14px;
            border:1px solid var(--line); border-radius:999px; background:var(--surface);
            color:var(--ink-2); font-size:var(--text-caption); font-weight:500; white-space:nowrap;
            transition: border-color var(--t-fast) var(--ease); }}
        .vc-chip:hover {{ border-color:var(--line-2); }}
        .vc-chip .dot {{ width:8px; height:8px; border-radius:50%; flex:none; }}

        /* ---- Stat cards ---- */
        .vc-stats {{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr));
            gap:var(--s-4); margin: var(--s-6) 0 var(--s-4); }}
        .vc-stat {{ position:relative; display:flex; flex-direction:column; gap:6px;
            background:linear-gradient(180deg, rgba(36,29,22,.55), var(--surface));
            border:1px solid var(--line); border-radius:var(--r-lg);
            padding:20px 22px 18px; box-shadow:var(--shadow-1); overflow:hidden;
            transition: border-color var(--t-base) var(--ease), transform var(--t-base) var(--ease),
                        box-shadow var(--t-base) var(--ease); }}
        .vc-stat:hover {{ transform:translateY(-2px); border-color:var(--accent-line);
            box-shadow:var(--glow); }}
        .vc-stat .ic {{ width:34px; height:34px; display:grid; place-items:center; border-radius:10px;
            color:var(--accent-2); background:var(--accent-soft); border:1px solid var(--accent-line);
            margin-bottom:8px; }}
        .vc-stat .trend {{ position:absolute; top:18px; right:18px; display:inline-flex; align-items:center;
            gap:4px; font-size:.7rem; font-weight:700; letter-spacing:.04em; color:var(--ok); }}
        .vc-stat .val {{ font-family:var(--font-display); font-size:var(--text-stat); line-height:1.05;
            color:var(--ink); font-variant-numeric:tabular-nums; }}
        .vc-stat .lab {{ font-size:.82rem; font-weight:600; letter-spacing:.03em; color:var(--ink); }}
        .vc-stat .note {{ font-size:.78rem; color:var(--ink-2); }}
        @media (max-width: 980px) {{ .vc-stats {{ grid-template-columns:repeat(2, minmax(0,1fr)); }} }}
        @media (max-width: 520px) {{ .vc-stats {{ grid-template-columns:1fr; }} }}

        /* ---- Section labels ---- */
        .vc-step {{ display:flex; align-items:center; gap:12px; margin: var(--s-6) 0 var(--s-4); }}
        .vc-step .m {{ margin-left:auto; color:var(--ink-3); font-size:var(--text-caption); font-style:italic; }}
        .vc-step .n {{ width:32px; height:32px; border-radius:10px; display:grid; place-items:center;
            color:var(--accent-2); background:var(--accent-soft); border:1px solid var(--accent-line); }}
        .vc-step.tight {{ margin-top: var(--s-2); }}
        /* .t is an <h2>; margin/line-height reset the browser default. */
        .vc-step .t {{ font-family:var(--font-display); font-weight:600; font-size:var(--text-h2);
            color:var(--ink); letter-spacing:.005em; margin:0; line-height:1.1; }}

        /* Captioned-player iframe: block layout kills the inline descender gap,
           and trim the component container's own spacing so the caption cards
           sit close beneath the video. */
        .stApp iframe {{ display:block; vertical-align:top; }}
        [data-testid="stCustomComponentV1"] {{ margin-bottom:0 !important; line-height:0; }}

        /* ---- File uploader → animated drag-and-drop zone ---- */
        [data-testid="stFileUploader"] section {{
            position:relative; border:0; border-radius:var(--r-lg); padding:26px 22px;
            background:
              radial-gradient(120% 120% at 50% 0%, var(--accent-soft), transparent 58%),
              var(--surface-2);
            transition: transform var(--t-base) var(--ease), box-shadow var(--t-base) var(--ease); }}
        [data-testid="stFileUploader"] section::before {{
            content:""; position:absolute; inset:0; border-radius:inherit; padding:1.5px;
            background:repeating-linear-gradient(90deg, var(--line-2) 0 12px, transparent 12px 22px);
            -webkit-mask:linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
            -webkit-mask-composite:xor; mask-composite:exclude; pointer-events:none; }}
        [data-testid="stFileUploader"] section:hover {{ transform:translateY(-2px); box-shadow:var(--glow); }}
        [data-testid="stFileUploader"] section:hover::before {{
            background:repeating-linear-gradient(90deg, var(--accent) 0 14px, transparent 14px 24px);
            animation: vc-march 12s linear infinite; }}
        @keyframes vc-march {{ to {{ background-position:220px 0; }} }}
        [data-testid="stFileUploaderDropzoneInstructions"] div span {{ color:var(--ink); font-weight:600; }}
        [data-testid="stFileUploader"] small {{ color:var(--ink-2); }}
        [data-testid="stFileUploader"] section button {{
            background:var(--surface) !important; color:var(--ink) !important;
            border:1px solid var(--line-2) !important; border-radius:var(--r-sm) !important;
            transition: border-color var(--t-fast) var(--ease) !important; }}
        [data-testid="stFileUploader"] section button:hover {{ border-color:var(--accent) !important; }}

        /* ---- Buttons ---- */
        .stButton > button, [data-testid="stDownloadButton"] > button {{
            border-radius:var(--r-md); font-weight:600; font-family:var(--font-body);
            letter-spacing:.02em; padding: 0.8rem 1rem; border:1px solid var(--line-2);
            background:var(--surface); color:var(--ink);
            transition: background var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease),
                        transform var(--t-fast) var(--ease), box-shadow var(--t-fast) var(--ease); }}
        .stButton > button:hover:not(:disabled),
        [data-testid="stDownloadButton"] > button:hover:not(:disabled) {{
            background:var(--surface-2); border-color:var(--accent); color:var(--ink); transform:translateY(-1px); }}
        .stButton > button[kind="primary"] {{
            background:linear-gradient(150deg, var(--accent-2), var(--accent)); color:var(--on-accent);
            border:1px solid transparent;
            box-shadow:0 8px 24px rgba(212,161,90,.28), inset 0 1px 0 rgba(255,255,255,.4); }}
        .stButton > button[kind="primary"]:hover:not(:disabled) {{
            box-shadow:0 12px 30px rgba(212,161,90,.4), inset 0 1px 0 rgba(255,255,255,.5);
            transform:translateY(-2px); }}
        .stButton > button[kind="primary"]:active:not(:disabled) {{ transform:translateY(0); }}
        .stButton > button:disabled {{ opacity:.45; }}

        /* ---- Video native ---- */
        [data-testid="stVideo"] video {{ border-radius:var(--r-lg); box-shadow:var(--shadow-2); }}

        /* ---- Meta card ---- */
        .vc-meta {{ background:var(--surface); border:1px solid var(--line);
            border-radius:var(--r-lg); padding:var(--s-2) 18px; box-shadow:var(--shadow-1); }}
        .vc-meta .row {{ display:flex; justify-content:space-between; padding:11px 0;
            border-bottom:1px solid var(--line); font-size:.9rem; }}
        .vc-meta .row:last-child {{ border-bottom:none; }}
        .vc-meta .k {{ color:var(--ink-2); }}
        .vc-meta .v {{ color:var(--ink); font-weight:600; }}

        /* ---- Caption cards (components.caption_cards grid) ---- */
        .vc-caps {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr));
            gap:var(--s-4); margin: var(--s-2) 0 var(--s-4); }}
        .vc-card {{ background:var(--surface); border:1px solid var(--line);
            border-radius:var(--r-lg); border-left:3px solid var(--accent);
            padding:24px 22px 20px; box-shadow:var(--shadow-1);
            height:100%; min-height:210px; position:relative; overflow:hidden;
            transition: border-color var(--t-base) var(--ease), transform var(--t-base) var(--ease),
                        box-shadow var(--t-base) var(--ease); }}
        .vc-card:hover {{ transform:translateY(-2px); box-shadow:var(--glow); }}
        .vc-card .head {{ display:flex; align-items:center; gap:12px; margin-bottom:4px; }}
        .vc-card .ic {{ width:40px; height:40px; border-radius:12px; display:grid; place-items:center;
            font-size:1.1rem; background:var(--soft); }}
        .vc-card .name {{ font-family:var(--font-display); font-weight:600; font-size:1.3rem;
            color:var(--ink); }}
        .vc-card .blurb {{ color:var(--ink-3); font-size:.8rem; margin: 2px 0 14px 52px; font-style:italic; }}
        .vc-card .body {{ color:var(--ink-2); font-size:.98rem; line-height:1.68; }}
        .vc-tag {{ position:absolute; top:18px; right:18px; font-size:.62rem; font-weight:600;
            letter-spacing:.16em; text-transform:uppercase; color:var(--accent); }}

        /* ---- Native widgets (alerts, captions, radio, spinner) ---- */
        [data-testid="stAlert"] {{ background:var(--surface) !important; border:1px solid var(--line);
            border-radius:var(--r-md); }}
        [data-testid="stAlert"] p, [data-testid="stAlert"] div {{ color:var(--ink); }}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:var(--ink-3); }}
        [data-testid="stRadio"] label p {{ color:var(--ink); }}
        [data-testid="stSpinner"], [data-testid="stSpinner"] div {{ color:var(--ink-2); }}

        /* ---- Skeleton loading (mirrors the captioned player) ---- */
        .vc-skelwrap {{ display:flex; flex-direction:column; gap:var(--s-3); }}
        .vc-skel {{ position:relative; border:1px solid var(--line); border-radius:var(--r-md);
            background:linear-gradient(100deg, var(--surface) 40%, var(--surface-2) 50%, var(--surface) 60%);
            background-size:200% 100%; animation: vc-shimmer 1.6s linear infinite; overflow:hidden; }}
        .vc-skel.stage {{ aspect-ratio:16/9; border-radius:var(--r-lg); display:grid; place-items:center; }}
        .vc-skelrow {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
        @media (max-width:520px) {{ .vc-skelrow {{ grid-template-columns:repeat(2,1fr); }} }}
        .vc-skel.btn {{ height:48px; }}
        .vc-skel.bar {{ height:13px; border-radius:6px; }}
        .vc-skel.w-40 {{ width:40%; }}
        .vc-skelspin {{ width:44px; height:44px; border-radius:50%; border:3px solid rgba(212,161,90,.2);
            border-top-color:var(--accent); animation: vc-spin .8s linear infinite; }}
        @keyframes vc-spin {{ to {{ transform:rotate(360deg); }} }}
        @keyframes vc-shimmer {{ from {{ background-position:200% 0; }} to {{ background-position:-200% 0; }} }}
        .vc-skelnote {{ color:var(--ink-2); font-size:var(--text-caption); font-style:italic;
            margin:var(--s-3) 0 0; }}

        /* ---- AI status card ---- */
        .vc-ai {{ display:flex; align-items:center; gap:14px; margin: var(--s-2) 0 var(--s-4);
            padding:16px 18px; border-radius:var(--r-lg);
            background:var(--glass-bg); backdrop-filter:var(--blur); -webkit-backdrop-filter:var(--blur);
            border:1px solid var(--glass-line); box-shadow:var(--shadow-1); }}
        .vc-ai .orb {{ width:44px; height:44px; flex:none; display:grid; place-items:center; border-radius:13px;
            color:var(--on-accent); background:radial-gradient(circle at 30% 30%, var(--accent-2), #8a5f2c);
            box-shadow:var(--glow); }}
        .vc-ai .txt {{ flex:1; min-width:0; display:flex; flex-direction:column; }}
        .vc-ai .txt b {{ font-size:.95rem; color:var(--ink); }}
        .vc-ai .txt span {{ font-size:.82rem; color:var(--ink-2); }}
        .vc-ai .state {{ flex:none; font-size:.72rem; font-weight:700; letter-spacing:.04em;
            padding:6px 12px; border-radius:999px; border:1px solid var(--line); color:var(--ink-2); }}
        .vc-ai .state.ready {{ color:var(--ok); border-color:rgba(110,207,142,.3); background:rgba(110,207,142,.08); }}
        .vc-ai .state.busy {{ color:var(--accent-2); border-color:var(--accent-line); background:var(--accent-soft); }}

        /* ---- Recent activity → Linear-style timeline ---- */
        .vc-timeline {{ display:flex; flex-direction:column; gap:8px; }}
        .vc-act {{ display:flex; align-items:center; gap:14px; padding:14px 16px;
            background:var(--surface); border:1px solid var(--line); border-radius:var(--r-md);
            box-shadow:var(--shadow-1);
            transition: border-color var(--t-fast) var(--ease), transform var(--t-fast) var(--ease); }}
        .vc-act:hover {{ border-color:var(--line-2); transform:translateY(-1px); }}
        .vc-act .thumb {{ width:54px; height:40px; flex:none; border-radius:9px; display:grid; place-items:center;
            color:var(--accent); background:linear-gradient(150deg,#2a2016,#14100b); border:1px solid var(--line-2); }}
        .vc-act .info {{ flex:1; min-width:0; display:flex; flex-direction:column; gap:3px; }}
        .vc-act .info b {{ font-size:.9rem; font-weight:600; color:var(--ink);
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        .vc-act .info .row {{ display:flex; align-items:center; gap:7px; flex-wrap:wrap;
            font-size:.76rem; color:var(--ink-3); }}
        .vc-act .info .row i {{ color:var(--ink-3); font-style:normal; opacity:.6; }}
        .vc-act .info .row .v {{ color:var(--accent-2); font-weight:600; }}
        .vc-act .ok {{ flex:none; display:inline-flex; align-items:center; gap:5px; font-size:.74rem;
            font-weight:600; color:var(--ok); }}
        .vc-act .fail {{ flex:none; font-size:.74rem; font-weight:600; color:var(--err); }}

        /* ---- Badges ---- */
        .vc-badge {{ display:inline-flex; align-items:center; padding:3px 10px; border-radius:999px;
            font-size:.7rem; font-weight:600; letter-spacing:.06em; }}
        .vc-badge.ok {{ color:var(--ok); border:1px solid rgba(110,207,142,.35); background:rgba(110,207,142,.08); }}
        .vc-badge.err {{ color:var(--err); border:1px solid rgba(224,147,126,.35); background:rgba(224,147,126,.08); }}

        /* ---- Empty states ---- */
        .vc-empty {{ display:flex; flex-direction:column; align-items:center; text-align:center;
            background:var(--surface); border:1px dashed var(--line-2); border-radius:var(--r-lg);
            padding:var(--s-7) var(--s-5); }}
        .vc-empty .ico {{ width:56px; height:56px; display:grid; place-items:center; border-radius:16px;
            color:var(--accent); background:var(--surface-2); border:1px solid var(--line-2);
            box-shadow:var(--shadow-1); margin-bottom:var(--s-4); }}
        .vc-empty h3 {{ font-family:var(--font-display); font-weight:600; font-size:var(--text-h3);
            color:var(--ink); margin:0 0 var(--s-2); }}
        .vc-empty p {{ color:var(--ink-2); font-size:var(--text-caption); max-width:42ch; margin:0; line-height:1.6; }}

        /* ---- Fallback subtitle bar (large clips) ---- */
        .vc-capbar {{ background:var(--surface); border:1px solid var(--line);
            border-left:4px solid var(--accent); border-radius:var(--r-md); padding:var(--s-4) 22px;
            margin-top:var(--s-3); }}
        .vc-capbar .lab {{ display:block; font-size:.66rem; letter-spacing:.18em; text-transform:uppercase;
            color:var(--accent); font-weight:600; margin-bottom:7px; }}
        .vc-capbar .txt {{ font-family:var(--font-display); color:var(--ink); font-size:var(--text-h3);
            line-height:1.42; }}

        .vc-foot {{ text-align:center; color:var(--ink-3); font-size:.78rem; margin-top:var(--s-8);
            letter-spacing:.04em; padding-top:22px; border-top:1px solid var(--line); }}

        /* ---- Reduced motion ---- */
        @media (prefers-reduced-motion: reduce) {{
            .stApp *, .stApp *::before, .stApp *::after {{
                animation:none !important; transition:none !important; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Page pieces
# --------------------------------------------------------------------------- #

def _session_stats(history: list[dict]) -> list[dict]:
    """Fold the session activity log into the four overview stats.

    Zero states show "0" / "—" so the grid keeps its shape before the
    first run — cards never appear or disappear.
    """
    done = [h for h in history if h["kind"] == "ok"]
    avg = (
        f"{sum(h['elapsed_s'] for h in done) / len(done):.1f}s" if done else "—"
    )
    last = done[-1]["at"] if done else "—"
    return [
        {"label": "Clips Captioned", "value": str(len(done)), "note": "this session",
         "icon": "clip", "trend": "live" if done else ""},
        {"label": "Captions Generated", "value": str(len(done) * len(STYLES)),
         "note": f"{len(STYLES)} voices per clip", "icon": "lines"},
        {"label": "Avg Processing", "value": avg, "note": "per clip", "icon": "clock"},
        {"label": "Last Session", "value": last, "note": "local time", "icon": "spark"},
    ]


def _render_captioned_fallback(video_file, captions: dict[str, str]) -> None:
    """Simpler player for clips too large to inline: native video + a
    Streamlit voice picker + a subtitle bar. (Switching reruns the app.)"""
    titles = [s["title"] for s in STYLES]
    choice = st.radio(
        "Choose a voice", titles, horizontal=True, label_visibility="collapsed"
    )
    style = STYLES[titles.index(choice)]
    st.video(video_file)
    st.markdown(
        f'<div class="vc-capbar" style="--accent:{style["accent"]};">'
        f'<span class="lab">{esc(style["title"])}</span>'
        f'<span class="txt">{esc(captions.get(style["key"], "—"))}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.session_state.setdefault("captions", None)
    st.session_state.setdefault("upload_sig", None)
    st.session_state.setdefault("history", [])  # session activity log
    st.session_state.setdefault("failed_sig", None)  # don't auto-retry a failed clip
    st.session_state.setdefault("fail_msg", "")

    live = _fireworks_live()
    engine_msg = "Fireworks vision model" if live else "Offline rule-based engine"

    # --- Shell: nav + hero + stats ------------------------------------- #
    ui.top_nav(
        "Caption Studio",
        tag="Track 02",
        status="Fireworks live" if live else "Offline engine",
    )
    ui.page_header(
        kicker="AI Caption Studio",
        title="Caption your videos with AI.",
        sub="Drop a short clip (30 seconds–2 minutes); the engine watches it, "
            "writes a caption in four voices, and plays them on the video as "
            "live subtitles. No buttons — just drop a clip.",
        chips=STYLES,
    )
    ui.stat_row(_session_stats(st.session_state.history))

    # --- Workspace: upload + activity (left) · player + AI (right) ------ #
    col_left, col_right = st.columns([5, 7], gap="large")

    # LEFT: upload, validation, recent activity ------------------------- #
    with col_left:
        ui.section("up", "Upload your clip")
        video_file = render_uploader()

        # Clear stale results whenever the uploaded clip changes (or is removed).
        # file_id is unique per upload, so re-uploading a same-named, same-sized
        # file still counts as a change; fall back to (name, size) just in case.
        upload_sig = (
            (getattr(video_file, "file_id", None), video_file.name, video_file.size)
            if video_file is not None
            else None
        )
        if upload_sig != st.session_state.upload_sig:
            st.session_state.upload_sig = upload_sig
            st.session_state.captions = None
            st.session_state.failed_sig = None  # a new clip gets a fresh attempt

        valid = False
        size_mb = 0.0
        if video_file is not None:
            size_mb = size_in_mb(video_file.size)
            if size_mb > MAX_FILE_MB:
                st.error(
                    f"That file is {size_mb:.1f} MB — over the {MAX_FILE_MB} MB limit. "
                    "Please upload a shorter or more compressed clip."
                )
            else:
                valid = True

        ui.section("lines", "Recent activity", meta="this session")
        if st.session_state.history:
            ui.activity_timeline(st.session_state.history)
        else:
            ui.empty_state(
                "Nothing here yet",
                "Caption your first clip and every run is logged here — "
                "clip, timing, and result.",
                icon_name="clock",
            )

    # RIGHT: preview → Generate Captions → captioned player ------------- #
    # Explicit flow: an uploaded clip previews here; the user presses
    # "Generate Captions" to run the engine; the clip then plays with
    # YouTube-style subtitles and a client-side voice switcher.
    with col_right:
        have_caps = bool(st.session_state.captions)
        failed = upload_sig is not None and st.session_state.failed_sig == upload_sig

        ui.section(
            "play", "Watch with captions",
            meta="switch voices as it plays" if have_caps
            else ("ready to caption" if valid else "waiting for a clip"),
        )
        ui.ai_status_card(
            "AI Caption Engine",
            f"{engine_msg} · captions ready" if have_caps
            else (f"{engine_msg} · clip ready to caption" if valid
                  else f"{engine_msg} · idle"),
            state="ready",
        )

        video_bytes: bytes | None = None

        if have_caps and video_file is not None:
            # --- Captioned player + download --------------------------- #
            if can_inline(video_file.size):
                video_bytes = video_file.getvalue()
                render_captioned_player(
                    video_bytes,
                    video_file.type or "video/mp4",
                    st.session_state.captions,
                    STYLES,
                )
            else:
                _render_captioned_fallback(video_file, st.session_state.captions)

            # The four full captions as cards, close below the player.
            ui.section("lines", "The four captions", meta="full text", tight=True)
            render_caption_grid(st.session_state.captions)

            st.download_button(
                "Download captions (.txt)",
                data=captions_as_text(st.session_state.captions, STYLES),
                file_name="captions.txt",
                mime="text/plain",
                use_container_width=True,
            )

        else:
            # --- Preview the clip (or empty state), then Generate ------ #
            if valid and video_file is not None:
                st.video(video_file)
            else:
                ui.empty_state(
                    "Your video preview appears here",
                    "Upload a clip on the left — preview it here, then press "
                    "Generate Captions to add live subtitles in four voices.",
                    icon_name="clip",
                )
            if failed:
                st.error(
                    "Something went wrong while generating captions.\n\n"
                    f"**Details:** {st.session_state.fail_msg}\n\n"
                    "Check your connection / API key and try again."
                )
            loading_slot = st.empty()  # skeleton renders here while working
            btn_label = "Try again" if failed else "Generate Captions"
            # Button is always visible; disabled until a valid clip is loaded.
            if st.button(
                btn_label, type="primary", use_container_width=True,
                disabled=not valid,
            ):
                st.session_state.failed_sig = None
                with loading_slot.container():
                    ui.skeleton_player("Watching your clip and writing four captions…")
                started = time.perf_counter()
                try:
                    video_bytes = video_file.getvalue()
                    st.session_state.captions = generate_captions(
                        video_bytes, video_file.name
                    )
                    elapsed = time.perf_counter() - started
                    st.session_state.history.append({
                        "clip": video_file.name,
                        "size": f"{size_mb:.1f} MB",
                        "voices": str(len(STYLES)),
                        "elapsed": f"{elapsed:.1f}s",
                        "elapsed_s": elapsed,
                        "at": datetime.now().strftime("%H:%M"),
                        "status": "Complete",
                        "kind": "ok",
                    })
                except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                    logger.exception("Caption generation failed")
                    st.session_state.captions = None
                    st.session_state.failed_sig = upload_sig
                    st.session_state.fail_msg = str(exc)
                    st.session_state.history.append({
                        "clip": video_file.name,
                        "size": f"{size_mb:.1f} MB",
                        "voices": "—",
                        "elapsed": f"{time.perf_counter() - started:.1f}s",
                        "elapsed_s": 0.0,
                        "at": datetime.now().strftime("%H:%M"),
                        "status": "Failed",
                        "kind": "err",
                    })
                finally:
                    loading_slot.empty()
                # Rerun so the player (on success) or the retry panel (on
                # failure) renders fresh. st.rerun() raises Streamlit's
                # control-flow exception, so it stays outside the try above.
                st.rerun()
            st.caption(
                "Writes a caption in all four voices, then plays them on the clip "
                "as live subtitles — switch voices without interrupting playback."
            )

    ui.footer(
        "Built for AMD Hackathon · Track 2 — Video Captioning · "
        + ("Powered by Fireworks&nbsp;AI" if live else "Offline rule-based engine")
    )
