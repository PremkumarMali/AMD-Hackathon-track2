"""Main application UI logic — the dashboard page.

Wires together the pieces:
    • design tokens              → components.theme (single source of truth)
    • reusable primitives        → components.ui (nav, stats, table, states)
    • upload                     → components.video_preview
    • caption voice definitions  → components.caption_cards.STYLES
    • timed-subtitle player      → components.video_captioner
    • the model call             → services.api_client.generate_captions
    • validation / formatting    → utils.helpers

Run with:  streamlit run main.py
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import streamlit as st

from components import ui
from components.caption_cards import STYLES
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

PAGE_TITLE = "Video Captioning Studio"
PAGE_ICON = "🎬"

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

        /* ---- App shell ---- */
        .stApp {{ background:
            radial-gradient(110% 80% at 100% -10%, #221a0f 0%, rgba(34,26,15,0) 50%),
            var(--bg); }}
        .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="block-container"] {{
            max-width: 100% !important;
            padding-top: 2.4rem !important; padding-bottom: 4rem !important;
            padding-left: clamp(1.5rem, 4vw, 4.5rem) !important;
            padding-right: clamp(1.5rem, 4vw, 4.5rem) !important; }}
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
            outline: 2px solid var(--accent) !important; outline-offset: 2px;
            border-radius: var(--r-sm); }}

        /* ---- Top bar ---- */
        .vc-nav {{ display:flex; align-items:center; justify-content:space-between;
            padding: 0 2px var(--s-4); border-bottom:1px solid var(--line);
            margin-bottom: var(--s-6); }}
        .vc-brand {{ display:flex; align-items:baseline; gap:10px;
            font-family:var(--font-display); font-weight:400; font-size:1.5rem;
            letter-spacing:.01em; color:var(--ink); }}
        .vc-brand .mark {{ color:var(--accent); }}
        .vc-nav-side {{ display:flex; align-items:center; gap:var(--s-4); }}
        .vc-nav .tag {{ font-size:var(--text-label); font-weight:600; letter-spacing:.22em;
            text-transform:uppercase; color:var(--ink-3); }}
        .vc-status {{ display:inline-flex; align-items:center; gap:8px; padding:6px 14px;
            border:1px solid var(--line); border-radius:999px; background:var(--surface);
            font-size:.72rem; font-weight:600; letter-spacing:.08em; color:var(--ink-2); }}
        .vc-status .dot {{ width:7px; height:7px; border-radius:50%; background:var(--ok);
            animation: vc-pulse 2.4s var(--ease) infinite; }}
        @keyframes vc-pulse {{
            0%   {{ box-shadow:0 0 0 0 rgba(168,191,144,.4); }}
            70%  {{ box-shadow:0 0 0 6px rgba(168,191,144,0); }}
            100% {{ box-shadow:0 0 0 0 rgba(168,191,144,0); }}
        }}

        /* ---- Page header ---- */
        .vc-pagehead {{ display:grid; grid-template-columns: minmax(0,1fr) auto;
            gap:var(--s-6); align-items:end; padding: var(--s-4) 2px 0; }}
        .vc-eyebrow {{ font-size:.72rem; font-weight:600; letter-spacing:.26em;
            text-transform:uppercase; color:var(--accent); margin:0 0 var(--s-3); }}
        .vc-pagehead h1 {{ font-family:var(--font-display); font-weight:400;
            font-size:var(--text-h1); line-height:1.1; margin:0 0 var(--s-3);
            color:var(--ink); letter-spacing:-0.01em; }}
        .vc-pagehead .sub {{ color:var(--ink-2); font-size:var(--text-body);
            max-width:56ch; margin:0; line-height:1.65; }}

        /* Voice identity chips */
        .vc-chips {{ display:grid; grid-template-columns:repeat(2, auto);
            gap:var(--s-2) var(--s-2); justify-content:end; }}
        .vc-chip {{ display:inline-flex; align-items:center; gap:8px;
            padding:7px 14px; border:1px solid var(--line); border-radius:999px;
            background:var(--surface); color:var(--ink-2);
            font-size:var(--text-caption); font-weight:500; white-space:nowrap;
            transition: border-color var(--t-fast) var(--ease); }}
        .vc-chip:hover {{ border-color:var(--line-2); }}
        .vc-chip .dot {{ width:8px; height:8px; border-radius:50%; flex:none; }}

        /* ---- Stat cards ---- */
        .vc-stats {{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr));
            gap:var(--s-4); margin: var(--s-5) 0 var(--s-2); }}
        .vc-stat {{ display:flex; flex-direction:column; gap:5px;
            background:var(--surface); border:1px solid var(--line);
            border-radius:var(--r-lg); padding:18px 20px 16px; box-shadow:var(--shadow-1);
            transition: border-color var(--t-fast) var(--ease); }}
        .vc-stat:hover {{ border-color:var(--line-2); }}
        .vc-stat .lab {{ font-size:var(--text-label); font-weight:600;
            letter-spacing:.18em; text-transform:uppercase; color:var(--ink-3); }}
        .vc-stat .val {{ font-family:var(--font-display); font-size:var(--text-stat);
            line-height:1.15; color:var(--ink); }}
        .vc-stat .note {{ font-size:var(--text-caption); color:var(--ink-3); }}

        @media (max-width: 980px) {{
            .vc-pagehead {{ grid-template-columns:1fr; align-items:start; gap:var(--s-4); }}
            .vc-chips {{ display:flex; flex-wrap:wrap; justify-content:flex-start; }}
            .vc-stats {{ grid-template-columns:repeat(2, minmax(0,1fr)); }}
        }}
        @media (max-width: 560px) {{
            .vc-stats {{ grid-template-columns:1fr; }}
        }}

        /* ---- Section labels ---- */
        .vc-step {{ display:flex; align-items:center; gap:14px; margin: 34px 0 14px; }}
        .vc-step .m {{ margin-left:auto; color:var(--ink-3);
            font-size:var(--text-caption); font-style:italic; }}
        .vc-step .n {{ width:30px; height:30px; border-radius:50%; display:grid; place-items:center;
            font-family:var(--font-display); font-size:.95rem; color:var(--accent);
            border:1px solid var(--accent); background:transparent; }}
        .vc-step .t {{ font-family:var(--font-display); font-weight:400;
            font-size:var(--text-h2); color:var(--ink); letter-spacing:.005em; }}

        /* ---- File uploader restyle ---- */
        [data-testid="stFileUploader"] section {{
            border:1px dashed var(--line-2); border-radius:var(--r-lg);
            background:var(--surface); padding: 20px;
            transition: border-color var(--t-base) var(--ease),
                        background var(--t-base) var(--ease); }}
        [data-testid="stFileUploader"] section:hover {{
            border-color:var(--accent); background:var(--surface-2); }}
        [data-testid="stFileUploaderDropzoneInstructions"] div span {{
            color:var(--ink); font-weight:600; }}
        [data-testid="stFileUploader"] small {{ color:var(--ink-2); }}
        [data-testid="stFileUploader"] section button {{
            background:var(--surface-2) !important; color:var(--ink) !important;
            border:1px solid var(--line-2) !important; border-radius:var(--r-sm) !important;
            transition: border-color var(--t-fast) var(--ease) !important; }}
        [data-testid="stFileUploader"] section button:hover {{
            border-color:var(--accent) !important; }}

        /* ---- Buttons ---- */
        .stButton > button, [data-testid="stDownloadButton"] > button {{
            border-radius:var(--r-md); font-weight:600; font-family:var(--font-body);
            letter-spacing:.03em; padding: 0.7rem 1rem; border:1px solid var(--line-2);
            background:var(--surface); color:var(--ink);
            transition: background var(--t-fast) var(--ease),
                        border-color var(--t-fast) var(--ease),
                        transform var(--t-fast) var(--ease),
                        box-shadow var(--t-fast) var(--ease); }}
        .stButton > button:hover:not(:disabled),
        [data-testid="stDownloadButton"] > button:hover:not(:disabled) {{
            background:var(--surface-2); border-color:var(--accent); color:var(--ink); }}
        .stButton > button[kind="primary"] {{
            background:var(--accent); color:var(--on-accent); border:1px solid var(--accent);
            box-shadow:0 8px 22px rgba(217,158,87,.16); }}
        .stButton > button[kind="primary"]:hover:not(:disabled) {{
            background:var(--accent-2); border-color:var(--accent-2); color:var(--on-accent);
            box-shadow:0 10px 26px rgba(217,158,87,.24); transform:translateY(-1px); }}
        .stButton > button[kind="primary"]:active:not(:disabled) {{ transform:translateY(0); }}
        .stButton > button:disabled {{ opacity:.4; }}

        /* ---- Video ---- */
        [data-testid="stVideo"] video {{ border-radius:var(--r-md); box-shadow:var(--shadow-1); }}

        /* ---- Meta card ---- */
        .vc-meta {{ background:var(--surface); border:1px solid var(--line);
            border-radius:var(--r-lg); padding:var(--s-2) 18px; box-shadow:var(--shadow-1); }}
        .vc-meta .row {{ display:flex; justify-content:space-between; padding:11px 0;
            border-bottom:1px solid var(--line); font-size:.9rem; }}
        .vc-meta .row:last-child {{ border-bottom:none; }}
        .vc-meta .k {{ color:var(--ink-2); letter-spacing:.02em; }}
        .vc-meta .v {{ color:var(--ink); font-weight:600; }}

        /* ---- Caption cards (components.caption_cards grid) ---- */
        .vc-card {{ background:var(--surface); border:1px solid var(--line);
            border-radius:var(--r-lg); padding:24px 22px 20px; box-shadow:var(--shadow-1);
            height:100%; min-height:230px; position:relative; overflow:hidden;
            transition: border-color var(--t-base) var(--ease),
                        transform var(--t-base) var(--ease); }}
        .vc-card:hover {{ transform:translateY(-2px); border-color:var(--line-2); }}
        .vc-card:before {{ content:""; position:absolute; inset:0 0 auto 0; height:3px;
            background:var(--accent); opacity:.85; }}
        .vc-card .head {{ display:flex; align-items:center; gap:12px; margin-bottom:4px; }}
        .vc-card .ic {{ width:40px; height:40px; border-radius:50%; display:grid;
            place-items:center; font-size:1.15rem; background:var(--soft); }}
        .vc-card .name {{ font-family:var(--font-display); font-weight:400;
            font-size:1.35rem; color:var(--ink); letter-spacing:.005em; }}
        .vc-card .blurb {{ color:var(--ink-3); font-size:.8rem; margin: 2px 0 14px 52px;
            font-style:italic; }}
        .vc-card .body {{ color:var(--ink-2); font-size:.98rem; line-height:1.68; }}
        .vc-tag {{ position:absolute; top:18px; right:18px; font-size:.62rem; font-weight:600;
            letter-spacing:.16em; text-transform:uppercase; color:var(--accent); }}

        /* ---- Native widgets (alerts, captions, radio, spinner) ---- */
        [data-testid="stAlert"] {{ background:var(--surface) !important;
            border:1px solid var(--line); border-radius:var(--r-md); }}
        [data-testid="stAlert"] p, [data-testid="stAlert"] div {{ color:var(--ink); }}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
            color:var(--ink-3); }}
        [data-testid="stRadio"] label p {{ color:var(--ink); }}
        [data-testid="stSpinner"], [data-testid="stSpinner"] div {{ color:var(--ink-2); }}

        /* ---- Skeleton loading (mirrors the player layout) ---- */
        .vc-skelwrap {{ display:grid; grid-template-columns: minmax(0,1.7fr) minmax(250px,1fr);
            gap:var(--s-5); align-items:start; }}
        @media (max-width: 820px) {{ .vc-skelwrap {{ grid-template-columns:1fr; }} }}
        .vc-skel {{ border:1px solid var(--line); border-radius:var(--r-md);
            background:linear-gradient(100deg, var(--surface) 40%, var(--surface-2) 50%,
                var(--surface) 60%);
            background-size:200% 100%; animation: vc-shimmer 1.6s linear infinite; }}
        .vc-skel.stage {{ aspect-ratio:16/9; border-radius:var(--r-lg); }}
        .vc-skelside {{ display:flex; flex-direction:column; gap:10px; }}
        .vc-skel.btn {{ height:50px; }}
        .vc-skel.bar {{ height:13px; border-radius:6px; border:none; }}
        .vc-skel.w-40 {{ width:40%; margin-bottom:4px; }}
        .vc-skel.w-60 {{ width:60%; margin-top:4px; }}
        @keyframes vc-shimmer {{
            from {{ background-position:200% 0; }} to {{ background-position:-200% 0; }}
        }}
        .vc-skelnote {{ color:var(--ink-2); font-size:var(--text-caption);
            font-style:italic; margin:var(--s-3) 0 0; }}

        /* ---- Activity table ---- */
        .vc-tablewrap {{ overflow-x:auto; background:var(--surface);
            border:1px solid var(--line); border-radius:var(--r-lg);
            box-shadow:var(--shadow-1); }}
        .vc-table {{ width:100%; min-width:640px; border-collapse:collapse;
            font-size:var(--text-caption); }}
        .vc-table th {{ text-align:left; padding:12px 18px;
            font-size:var(--text-label); font-weight:600; letter-spacing:.16em;
            text-transform:uppercase; color:var(--ink-3);
            border-bottom:1px solid var(--line); }}
        .vc-table td {{ padding:13px 18px; color:var(--ink-2);
            border-bottom:1px solid var(--line); white-space:nowrap; }}
        .vc-table td.clip {{ color:var(--ink); font-weight:600;
            max-width:280px; overflow:hidden; text-overflow:ellipsis; }}
        .vc-table tbody tr {{ transition: background var(--t-fast) var(--ease); }}
        .vc-table tbody tr:hover {{ background:var(--surface-2); }}
        .vc-table tbody tr:last-child td {{ border-bottom:none; }}

        /* ---- Badges ---- */
        .vc-badge {{ display:inline-flex; align-items:center; padding:3px 10px;
            border-radius:999px; font-size:.7rem; font-weight:600;
            letter-spacing:.06em; }}
        .vc-badge.ok  {{ color:var(--ok); border:1px solid rgba(168,191,144,.35);
            background:rgba(168,191,144,.08); }}
        .vc-badge.err {{ color:var(--err); border:1px solid rgba(217,145,128,.35);
            background:rgba(217,145,128,.08); }}

        /* ---- Empty states ---- */
        .vc-empty {{ background:var(--surface); border:1px dashed var(--line-2);
            border-radius:var(--r-lg); padding:var(--s-7) var(--s-5);
            text-align:center; }}
        .vc-empty h3 {{ font-family:var(--font-display); font-weight:400;
            font-size:var(--text-h3); color:var(--ink); margin:0 0 var(--s-2); }}
        .vc-empty p {{ color:var(--ink-2); font-size:var(--text-caption);
            max-width:44ch; margin:0 auto; line-height:1.6; }}

        /* ---- Fallback subtitle bar (large clips) ---- */
        .vc-capbar {{ background:var(--surface); border:1px solid var(--line);
            border-left:4px solid var(--accent); border-radius:var(--r-md);
            padding:var(--s-4) 22px; margin-top:var(--s-3); }}
        .vc-capbar .lab {{ display:block; font-size:.66rem; letter-spacing:.18em;
            text-transform:uppercase; color:var(--accent); font-weight:600; margin-bottom:7px; }}
        .vc-capbar .txt {{ font-family:var(--font-display); color:var(--ink);
            font-size:var(--text-h3); line-height:1.42; }}

        .vc-foot {{ text-align:center; color:var(--ink-3); font-size:.78rem;
            margin-top:var(--s-7); letter-spacing:.04em; padding-top:22px;
            border-top:1px solid var(--line); }}

        /* ---- Reduced motion ---- */
        @media (prefers-reduced-motion: reduce) {{
            .stApp *, .stApp *::before, .stApp *::after {{
                animation:none !important; transition:none !important; }}
        }}
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
        {"label": "Clips captioned", "value": str(len(done)), "note": "this session"},
        {"label": "Captions written", "value": str(len(done) * len(STYLES)),
         "note": f"{len(STYLES)} voices per clip"},
        {"label": "Avg generation", "value": avg, "note": "per clip"},
        {"label": "Last run", "value": last, "note": "local time"},
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

    # --- Shell ---------------------------------------------------------- #
    ui.top_nav(
        "Caption Studio",
        tag="AMD Hackathon · Track 02",
        status="Fireworks live" if live else "Offline engine",
    )
    ui.page_header(
        kicker="Studio",
        title="Caption your clip in four voices.",
        sub="Upload a short clip (30 seconds–2 minutes); the engine watches it, "
            "writes a caption in each voice, and plays them on the video as "
            "subtitles. No buttons — just drop a clip.",
        chips=STYLES,
    )
    ui.stat_row(_session_stats(st.session_state.history))

    # --- Step 1: Upload ------------------------------------------------ #
    ui.section("1", "Upload your clip")
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

    # --- Step 2: Watch with captions ----------------------------------- #
    # No preview / generate button: captions are generated automatically on
    # upload, then the clip plays with YouTube-style subtitles at the bottom.
    ui.section(
        "2", "Watch with captions",
        meta="captions appear as the clip plays" if valid else "waiting for a clip",
    )

    video_bytes: bytes | None = None
    loading_slot = st.empty()  # skeleton renders where the player will appear

    needs_generation = valid and not st.session_state.captions

    if needs_generation and st.session_state.failed_sig == upload_sig:
        # Last attempt for THIS clip failed — hold for an explicit retry so a
        # broken clip doesn't hammer the engine on every rerun.
        st.error(
            "Something went wrong while generating captions.\n\n"
            f"**Details:** {st.session_state.fail_msg}\n\n"
            "Check your connection / API key and try again."
        )
        if st.button("Try again", type="primary", use_container_width=True):
            st.session_state.failed_sig = None
            st.rerun()
    elif needs_generation:
        with loading_slot.container():
            ui.skeleton_player("Watching your clip and writing four captions…")
        started = time.perf_counter()
        succeeded = False
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
            succeeded = True
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
        # Rerun either way: on success the player + stats render fresh; on
        # failure the retry panel above takes over (failed_sig is set).
        # st.rerun() raises Streamlit's control-flow exception, so it must
        # stay outside the try above.
        st.rerun()

    # --- Player --------------------------------------------------------- #
    if st.session_state.captions and video_file is not None:
        if can_inline(video_file.size):
            if video_bytes is None:
                video_bytes = video_file.getvalue()
            render_captioned_player(
                video_bytes,
                video_file.type or "video/mp4",
                st.session_state.captions,
                STYLES,
            )
        else:
            _render_captioned_fallback(video_file, st.session_state.captions)

        st.download_button(
            "Download captions (.txt)",
            data=captions_as_text(st.session_state.captions, STYLES),
            file_name="captions.txt",
            mime="text/plain",
            use_container_width=True,
        )
    elif video_file is None:
        ui.empty_state(
            "No clip yet",
            "Upload a video above — it will start playing here with captions "
            "on screen, and you can switch voices while it runs.",
        )

    # --- Recent activity ------------------------------------------------ #
    ui.section("≡", "Recent activity", meta="this session")
    if st.session_state.history:
        ui.activity_table(st.session_state.history)
    else:
        ui.empty_state(
            "Nothing here yet",
            "Caption your first clip and every run will be logged here — "
            "clip, timing, and result.",
        )

    ui.footer(
        "Built for AMD Hackathon · Track 2 — Video Captioning · "
        + ("Powered by Fireworks&nbsp;AI" if live else "Offline rule-based engine")
    )
