"""Main application UI logic.

Wires together the pieces:
    • styling / nav / hero / step headers (defined here)
    • upload + preview          → components.video_preview
    • the 2×2 caption cards      → components.caption_cards
    • the model call            → services.api_client.generate_captions
    • validation / formatting    → utils.helpers

Run with:  streamlit run main.py
"""

from __future__ import annotations

import streamlit as st

from components.caption_cards import STYLES
from components.video_captioner import can_inline, render_captioned_player
from components.video_preview import render_preview, render_uploader
from services.api_client import generate_captions
from utils.helpers import (
    MAX_FILE_MB,
    captions_as_text,
    esc,
    load_brand_font_css,
    size_in_mb,
)

PAGE_TITLE = "Video Captioning Studio"
PAGE_ICON = "🎬"


# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #

def inject_css() -> None:
    font_face = load_brand_font_css("Mortane")
    st.markdown(
        f"""
        <style>
        {font_face}

        :root {{
            --paper:   #f7f3ec;   /* warm editorial paper       */
            --surface: #fffdf8;   /* card / raised surface       */
            --ink:     #1c1815;   /* warm near-black text        */
            --muted:   #857a6c;   /* secondary text              */
            --line:    #e7ded0;   /* hairline rules              */
            --accent:  #b45309;   /* burnt amber — used sparingly */
            --accent-ink:#7c3a06;
            --shadow:  0 1px 2px rgba(28,24,21,.04), 0 10px 30px rgba(28,24,21,.05);

            --font-display: 'Mortane', 'Playfair Display', 'Georgia', 'Times New Roman', serif;
            --font-body: -apple-system, system-ui, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}

        /* ---- App shell ---- */
        .stApp {{ background:
            radial-gradient(120% 90% at 100% -10%, #fbeede 0%, rgba(251,238,222,0) 45%),
            var(--paper); }}
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

        /* ---- Top bar ---- */
        .vc-nav {{ display:flex; align-items:center; justify-content:space-between;
            padding: 0 2px 14px; border-bottom:1px solid var(--line); margin-bottom: 30px; }}
        .vc-brand {{ display:flex; align-items:baseline; gap:10px;
            font-family:var(--font-display); font-weight:400; font-size:1.5rem;
            letter-spacing:.01em; color:var(--ink); }}
        .vc-brand .mark {{ color:var(--accent); }}
        .vc-nav .tag {{ font-size:.68rem; font-weight:600; letter-spacing:.22em;
            text-transform:uppercase; color:var(--muted); }}

        /* ---- Hero ---- */
        .vc-hero {{ position:relative; display:grid; align-items:center;
            grid-template-columns: minmax(0, 1.05fr) minmax(340px, 0.95fr);
            gap: clamp(40px, 6vw, 96px); padding: 26px 2px 12px; margin-bottom: 18px; }}
        .vc-eyebrow {{ font-size:.72rem; font-weight:600; letter-spacing:.26em;
            text-transform:uppercase; color:var(--accent); margin:0 0 20px; }}
        .vc-hero h1 {{ font-family:var(--font-display); font-weight:400;
            font-size: clamp(2.6rem, 5vw, 4.2rem); line-height:1.04; margin:0 0 22px;
            color:var(--ink); letter-spacing:-0.01em; }}
        .vc-hero h1 em {{ font-style:italic; color:var(--accent); }}
        .vc-hero p {{ font-family:var(--font-body); color:var(--muted); font-size:1.06rem;
            max-width:520px; margin:0; line-height:1.65; }}

        /* Hero right-side "voices index" panel */
        .vc-index {{ background:var(--surface); border:1px solid var(--line); border-radius:18px;
            padding: 6px 24px; box-shadow:var(--shadow); }}
        .vc-index .item {{ display:flex; align-items:baseline; gap:16px; padding:18px 0;
            border-bottom:1px solid var(--line); }}
        .vc-index .item:last-child {{ border-bottom:none; }}
        .vc-index .num {{ font-family:var(--font-display); font-size:1.05rem; color:var(--muted);
            min-width:2ch; }}
        .vc-index .nm {{ font-family:var(--font-display); font-size:1.25rem; color:var(--ink);
            display:flex; align-items:center; gap:10px; }}
        .vc-index .nm .dot {{ width:8px; height:8px; border-radius:50%; }}
        .vc-index .bl {{ color:var(--muted); font-size:.82rem; font-style:italic; margin-top:3px; }}

        @media (max-width: 980px) {{
            .vc-hero {{ grid-template-columns: 1fr; gap: 30px; }}
        }}

        /* ---- Section labels ---- */
        .vc-step {{ display:flex; align-items:center; gap:14px; margin: 34px 0 14px; }}
        .vc-step .n {{ width:30px; height:30px; border-radius:50%; display:grid; place-items:center;
            font-family:var(--font-display); font-size:.95rem; color:var(--accent);
            border:1px solid var(--accent); background:transparent; }}
        .vc-step .t {{ font-family:var(--font-display); font-weight:400; font-size:1.5rem;
            color:var(--ink); letter-spacing:.005em; }}

        /* ---- File uploader restyle ---- */
        [data-testid="stFileUploader"] section {{
            border:1px dashed #dcc9ab; border-radius:14px; background:var(--surface);
            padding: 20px; transition:.18s ease; }}
        [data-testid="stFileUploader"] section:hover {{ border-color:var(--accent); background:#fffaf1; }}
        [data-testid="stFileUploaderDropzoneInstructions"] div span {{ color:var(--ink); font-weight:600; }}
        [data-testid="stFileUploader"] small {{ color:var(--muted); }}

        /* ---- Buttons ---- */
        .stButton > button {{
            border-radius:11px; font-weight:600; font-family:var(--font-body);
            letter-spacing:.03em; padding: 0.7rem 1rem; border:1px solid var(--line);
            background:var(--surface); color:var(--ink); transition:.18s ease; }}
        .stButton > button[kind="primary"] {{
            background:var(--ink); color:#fdf8ef; border:1px solid var(--ink);
            box-shadow:0 8px 22px rgba(28,24,21,0.16); }}
        .stButton > button[kind="primary"]:hover:not(:disabled) {{
            background:var(--accent); border-color:var(--accent);
            box-shadow:0 10px 26px rgba(180,83,9,0.28); transform:translateY(-1px); }}
        .stButton > button:disabled {{ opacity:.45; }}
        [data-testid="stDownloadButton"] > button {{ font-weight:600; }}

        /* ---- Video ---- */
        [data-testid="stVideo"] video {{ border-radius:12px; box-shadow:var(--shadow); }}

        /* ---- Meta card ---- */
        .vc-meta {{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
            padding:8px 18px; box-shadow:var(--shadow); }}
        .vc-meta .row {{ display:flex; justify-content:space-between; padding:11px 0;
            border-bottom:1px solid var(--line); font-size:.9rem; }}
        .vc-meta .row:last-child {{ border-bottom:none; }}
        .vc-meta .k {{ color:var(--muted); letter-spacing:.02em; }}
        .vc-meta .v {{ color:var(--ink); font-weight:600; }}

        /* ---- Caption cards ---- */
        .vc-card {{ background:var(--surface); border:1px solid var(--line); border-radius:16px;
            padding:24px 22px 20px; box-shadow:var(--shadow); height:100%; min-height:230px;
            transition:.2s ease; position:relative; overflow:hidden; }}
        .vc-card:hover {{ transform:translateY(-3px); border-color:var(--accent);
            box-shadow:0 18px 40px rgba(28,24,21,0.10); }}
        .vc-card:before {{ content:""; position:absolute; inset:0 0 auto 0; height:3px;
            background:var(--accent); opacity:.9; }}
        .vc-card .head {{ display:flex; align-items:center; gap:12px; margin-bottom:4px; }}
        .vc-card .ic {{ width:40px; height:40px; border-radius:50%; display:grid; place-items:center;
            font-size:1.15rem; background:var(--soft); }}
        .vc-card .name {{ font-family:var(--font-display); font-weight:400; font-size:1.35rem;
            color:var(--ink); letter-spacing:.005em; }}
        .vc-card .blurb {{ color:var(--muted); font-size:.8rem; margin: 2px 0 14px 52px;
            font-style:italic; }}
        .vc-card .body {{ color:var(--ink); font-size:.98rem; line-height:1.68; opacity:.92; }}
        .vc-tag {{ position:absolute; top:18px; right:18px; font-size:.62rem; font-weight:600;
            letter-spacing:.16em; text-transform:uppercase; color:var(--accent); }}

        /* ---- Fallback subtitle bar (large clips) ---- */
        .vc-capbar {{ background:#141210; border:1px solid var(--line); border-left:4px solid var(--accent);
            border-radius:12px; padding:16px 22px; margin-top:12px; }}
        .vc-capbar .lab {{ display:block; font-size:.66rem; letter-spacing:.18em; text-transform:uppercase;
            color:var(--accent); font-weight:600; margin-bottom:7px; }}
        .vc-capbar .txt {{ font-family:var(--font-display); color:#f3ece0; font-size:1.2rem; line-height:1.42; }}

        .vc-foot {{ text-align:center; color:var(--muted); font-size:.78rem; margin-top:48px;
            letter-spacing:.04em; padding-top:22px; border-top:1px solid var(--line); }}

        /* ---- Dark mode ---- */
        @media (prefers-color-scheme: dark) {{
            :root {{ --paper:#16120d; --surface:#211b14; --ink:#f3ece0; --muted:#a89c8b;
                    --line:#342b20; --accent:#e0913f; --accent-ink:#f0b878;
                    --shadow:0 1px 2px rgba(0,0,0,.3), 0 10px 30px rgba(0,0,0,0.35); }}
            .stApp {{ background:
                radial-gradient(120% 90% at 100% -10%, #241a10 0%, rgba(36,26,16,0) 45%),
                var(--paper); }}
            .vc-card .body {{ opacity:.85; }}
            .stButton > button[kind="primary"] {{ background:var(--accent); border-color:var(--accent);
                color:#1a1206; }}
            .stButton > button[kind="primary"]:hover:not(:disabled) {{ filter:brightness(1.06); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# UI pieces
# --------------------------------------------------------------------------- #

def render_nav() -> None:
    st.markdown(
        """
        <div class="vc-nav">
          <div class="vc-brand"><span class="mark">✦</span> Caption Studio</div>
          <div class="tag">AMD Hackathon · Track 02</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    items = "".join(
        f"""
        <div class="item">
          <span class="num">0{i}</span>
          <div>
            <div class="nm"><span class="dot" style="background:{s['accent']}"></span>{s['title']}</div>
            <div class="bl">{s['blurb']}</div>
          </div>
        </div>
        """
        for i, s in enumerate(STYLES, start=1)
    )
    st.markdown(
        f"""
        <div class="vc-hero">
          <div class="vc-hero-copy">
            <p class="vc-eyebrow">Four voices · One clip</p>
            <h1>Turn any clip into a caption people <em>remember</em>.</h1>
            <p>Upload a short video (30&nbsp;seconds–2&nbsp;minutes) and generate a caption
               in four distinct voices. One click, four takes.</p>
          </div>
          <div class="vc-index">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def step(n, title: str) -> None:
    st.markdown(
        f'<div class="vc-step"><span class="n">{n}</span><span class="t">{title}</span></div>',
        unsafe_allow_html=True,
    )


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

    render_nav()
    render_hero()

    # --- Step 1: Upload ------------------------------------------------ #
    step(1, "Upload your clip")
    video_file = render_uploader()

    # Clear stale results whenever the uploaded clip changes (or is removed).
    upload_sig = (video_file.name, video_file.size) if video_file is not None else None
    if upload_sig != st.session_state.upload_sig:
        st.session_state.upload_sig = upload_sig
        st.session_state.captions = None

    valid = False
    if video_file is not None:
        size_mb = size_in_mb(video_file.size)
        if size_mb > MAX_FILE_MB:
            st.error(
                f"That file is {size_mb:.1f} MB — over the {MAX_FILE_MB} MB limit. "
                "Please upload a shorter or more compressed clip."
            )
        else:
            valid = True
            # --- Step 2: Preview (hidden once captions exist; the
            #     captioned player below then plays the clip instead) --- #
            if not st.session_state.captions:
                step(2, "Preview")
                render_preview(video_file, size_mb)
    else:
        st.info("Drop a video above to get started — no clip, no captions. 🙂")

    # --- Step 3: Generate --------------------------------------------- #
    step(3, "Generate captions")
    generate = st.button(
        "✨  Generate Captions",
        type="primary",
        use_container_width=True,
        disabled=not valid,
    )

    if generate and valid:
        try:
            with st.spinner("Watching your video and writing four captions…"):
                st.session_state.captions = generate_captions(
                    video_file.getvalue(), video_file.name
                )
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            st.session_state.captions = None
            st.error(
                "Something went wrong while generating captions.\n\n"
                f"**Details:** {exc}\n\nCheck your connection / API key and try again."
            )

    # --- Results ------------------------------------------------------- #
    if st.session_state.captions and video_file is not None:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="vc-step"><span class="n">✓</span>'
            '<span class="t">Your captioned clip</span></div>',
            unsafe_allow_html=True,
        )

        if can_inline(video_file.size):
            render_captioned_player(
                video_file.getvalue(),
                video_file.type or "video/mp4",
                st.session_state.captions,
                STYLES,
            )
        else:
            _render_captioned_fallback(video_file, st.session_state.captions)

        st.download_button(
            "⬇  Download all captions (.txt)",
            data=captions_as_text(st.session_state.captions, STYLES),
            file_name="captions.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown(
        '<div class="vc-foot">Built for AMD Hackathon · Track 2 — Video Captioning · '
        'Powered by Fireworks&nbsp;AI</div>',
        unsafe_allow_html=True,
    )
