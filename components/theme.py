"""Design tokens — the single source of truth for the visual system.

Every color, size, radius, and duration in the UI comes from here. Two
stylesheets consume these tokens:

    • components/app.py          — the main app stylesheet
    • components/video_captioner — the captioned-player iframe (its own DOM,
                                    so it must inject the variables itself)

Change a value here and the whole product follows. Never hardcode a hex
value or a pixel size in component CSS — reference the CSS variable.

The palette is a warm luxury-dark system: espresso blacks, one bronze
accent, warm off-white text. Contrast pairs are WCAG AA:
ink/bg ≈ 14:1 · ink-2/surface ≈ 7:1 · accent/bg ≈ 8:1.
"""

from __future__ import annotations

TOKENS: dict[str, str] = {
    # ---- Color ----------------------------------------------------------- #
    "bg":         "#0e0b06",   # canvas — deep espresso black
    "surface":    "#17110a",   # cards, inputs
    "surface-2":  "#221a10",   # raised / hover surfaces
    "line":       "#332a1e",   # resting hairline borders
    "line-2":     "#4d3f2a",   # interactive / hover borders
    "ink":        "#f1e9d7",   # primary text — warm white
    "ink-2":      "#b0a288",   # secondary text — muted beige
    "ink-3":      "#877a5e",   # tertiary text — metadata only
    "accent":     "#d99e57",   # bronze — the single accent
    "accent-2":   "#e8b26b",   # accent hover / emphasis
    "on-accent":  "#1d1204",   # text set on accent fills
    "ok":         "#a8bf90",   # success — warm sage
    "err":        "#d99180",   # error — warm terracotta

    # ---- Elevation ------------------------------------------------------- #
    "shadow-1":   "0 1px 2px rgba(0,0,0,.35), 0 8px 24px rgba(0,0,0,.25)",
    "shadow-2":   "0 2px 4px rgba(0,0,0,.4), 0 18px 50px rgba(0,0,0,.45)",

    # ---- Typography ------------------------------------------------------ #
    "font-display": "'Mortane','Playfair Display',Georgia,'Times New Roman',serif",
    "font-body": "-apple-system,system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif",
    "text-display": "clamp(2.6rem, 5vw, 4.2rem)",
    "text-h1":      "clamp(1.9rem, 3vw, 2.6rem)",   # dashboard page titles
    "text-stat":    "1.9rem",                        # stat-card values
    "text-h2":      "1.45rem",
    "text-h3":      "1.2rem",
    "text-body":    "0.95rem",
    "text-caption": "0.82rem",
    "text-label":   "0.68rem",   # always 600 weight, uppercase, tracked

    # ---- Spacing (8-pt grid) --------------------------------------------- #
    "s-1": "4px",
    "s-2": "8px",
    "s-3": "12px",
    "s-4": "16px",
    "s-5": "24px",
    "s-6": "32px",
    "s-7": "48px",
    "s-8": "64px",

    # ---- Radius ---------------------------------------------------------- #
    "r-sm": "8px",
    "r-md": "12px",
    "r-lg": "16px",
    "r-xl": "20px",

    # ---- Motion ---------------------------------------------------------- #
    "t-fast": "150ms",
    "t-base": "200ms",
    "ease":   "cubic-bezier(.33,.9,.35,1)",
}


def css_variables() -> str:
    """Render the tokens as a ``:root { … }`` CSS block."""
    body = "".join(f"--{name}:{value};" for name, value in TOKENS.items())
    return f":root{{{body}}}"
