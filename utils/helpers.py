"""Small, dependency-free helpers: file validation + formatting.

Kept pure (no Streamlit imports) so they're easy to unit-test and reuse.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

# Where brand font files live. Drop Mortane here (see load_brand_font_css).
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

_FONT_FORMATS = {
    "woff2": "woff2",
    "woff": "woff",
    "ttf": "truetype",
    "otf": "opentype",
}

# Upload rules — the single source of truth for both the uploader and the
# config.toml server cap. Change here to change everywhere.
SUPPORTED_TYPES = ["mp4", "mov", "avi", "mkv", "webm"]
MAX_FILE_MB = 200


def is_supported_video(filename: str) -> bool:
    """True if the filename's extension is one we accept."""
    return Path(filename).suffix.lower().lstrip(".") in SUPPORTED_TYPES


def size_in_mb(size_bytes: int) -> float:
    """Bytes → megabytes."""
    return size_bytes / (1024 * 1024)


def is_within_size_limit(size_bytes: int, max_mb: int = MAX_FILE_MB) -> bool:
    """True if the upload is within the size cap."""
    return size_in_mb(size_bytes) <= max_mb


def esc(text: object) -> str:
    """HTML-escape any value before injecting it into ``unsafe_allow_html``.

    Guards against injection from user-controlled strings (filenames) and
    model output (captions) that get rendered as raw HTML.
    """
    return html.escape(str(text))


def load_brand_font_css(family: str = "Mortane", fonts_dir: Path = FONTS_DIR) -> str:
    """Return ``@font-face`` CSS for the brand display font, base64-embedded.

    Scans ``fonts_dir`` for any font file whose name contains ``family``
    (e.g. ``Mortane.otf``, ``Mortane-Regular.woff2``) and embeds it as a data
    URI so it works offline with no static-file server. A filename containing
    "bold" is registered at weight 700, "italic" as italic style.

    Returns an empty string if no matching file is found — the CSS then falls
    back to the elegant serif stack, so the app never breaks.
    """
    if not fonts_dir.is_dir():
        return ""

    blocks: list[str] = []
    for path in sorted(fonts_dir.iterdir()):
        ext = path.suffix.lower().lstrip(".")
        if ext not in _FONT_FORMATS or family.lower() not in path.stem.lower():
            continue
        stem = path.stem.lower()
        weight = "700" if "bold" in stem else "400"
        style = "italic" if "italic" in stem or "oblique" in stem else "normal"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        blocks.append(
            f"@font-face{{font-family:'{family}';font-style:{style};"
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/{ext};base64,{b64}) format('{_FONT_FORMATS[ext]}');}}"
        )
    return "\n".join(blocks)


def captions_as_text(captions: dict[str, str], styles: list[dict]) -> str:
    """Flatten the four captions into a downloadable .txt body."""
    lines: list[str] = []
    for s in styles:
        lines.append(f"### {s['title'].upper()}")
        lines.append(captions.get(s["key"], ""))
        lines.append("")
    return "\n".join(lines).strip()
