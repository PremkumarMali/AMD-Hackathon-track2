"""Upload + preview: the file uploader and the video/metadata preview."""

from __future__ import annotations

import streamlit as st

from utils.helpers import MAX_FILE_MB, SUPPORTED_TYPES, esc


def render_uploader():
    """Render the file uploader and return the uploaded file (or ``None``)."""
    video_file = st.file_uploader(
        "Choose a video file",
        type=SUPPORTED_TYPES,
        help="Clips should be between 30 seconds and 2 minutes.",
        label_visibility="collapsed",
    )
    st.caption(
        f"Supported formats: {', '.join(SUPPORTED_TYPES)} · up to {MAX_FILE_MB} MB"
    )
    return video_file


def render_preview(video_file, size_mb: float) -> None:
    """Show the video player alongside a metadata card."""
    col_vid, col_meta = st.columns([3, 2], gap="medium")
    with col_vid:
        st.video(video_file)
    with col_meta:
        fmt = (video_file.type or "video").split("/")[-1]
        st.markdown(
            f"""
            <div class="vc-meta">
              <div class="row"><span class="k">File name</span><span class="v">{esc(video_file.name)}</span></div>
              <div class="row"><span class="k">Size</span><span class="v">{size_mb:.1f} MB</span></div>
              <div class="row"><span class="k">Format</span><span class="v">{esc(fmt)}</span></div>
              <div class="row"><span class="k">Required length</span><span class="v">30s – 2min</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
