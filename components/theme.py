"""Design tokens — the single source of truth for the visual system.

Every color, size, radius, and duration in the UI comes from here. Two
stylesheets consume these tokens:

    • components/app.py          — the main app stylesheet
    • components/video_captioner — the captioned-player iframe (its own DOM,
                                    so it must inject the variables itself)

Change a value here and the whole product follows. Never hardcode a hex
value or a pixel size in component CSS — reference the CSS variable.

The palette is a warm luxury-dark system: black-walnut + matte-black
grounds, one soft amber accent, warm off-white text. Contrast pairs are
WCAG AA: ink/bg ≈ 15:1 · ink-2/surface ≈ 6:1 · accent/bg ≈ 8:1.
"""

from __future__ import annotations

TOKENS: dict[str, str] = {
    # ---- Color ----------------------------------------------------------- #
    "bg":         "#090806",   # canvas — matte black-walnut
    "panel":      "#13100D",   # mid-layer panels / deep wells
    "surface":    "#1B1713",   # cards, inputs
    "surface-2":  "#241D16",   # raised / hover surfaces
    "line":       "rgba(255,255,255,.08)",   # resting hairline borders
    "line-2":     "rgba(255,255,255,.15)",   # interactive / hover borders
    "ink":        "#F5F2EC",   # primary text — warm white
    "ink-2":      "#9A948A",   # secondary text — muted stone
    "ink-3":      "#6E685E",   # tertiary text — metadata only
    "accent":     "#D4A15A",   # amber — the single accent
    "accent-2":   "#F3C77D",   # amber highlight / emphasis
    "on-accent":  "#241706",   # text set on accent fills
    "ok":         "#6ECF8E",   # success — warm green
    "err":        "#E0937E",   # error — warm terracotta

    # ---- Glass / glow (subtle depth) ------------------------------------- #
    "glass-bg":   "rgba(27,23,19,.62)",       # frosted card fill
    "glass-line": "rgba(255,255,255,.10)",    # frosted card border
    "blur":       "blur(18px) saturate(1.25)",
    "glow":       "0 0 0 1px rgba(212,161,90,.32), 0 10px 40px rgba(212,161,90,.16)",
    "accent-soft":"rgba(212,161,90,.12)",     # tint fills for icon chips
    "accent-line":"rgba(212,161,90,.28)",     # amber hairline

    # ---- Elevation ------------------------------------------------------- #
    "shadow-1":   "0 1px 2px rgba(0,0,0,.4), 0 12px 34px rgba(0,0,0,.34)",
    "shadow-2":   "0 2px 6px rgba(0,0,0,.5), 0 28px 70px rgba(0,0,0,.5)",

    # ---- Typography ------------------------------------------------------ #
    # Display: elegant editorial serif (Cormorant/Playfair feel via system
    # serifs, since no webfont is fetched — see load_brand_font_css).
    "font-display": "'Mortane','Cormorant Garamond','Playfair Display',"
                    "'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif",
    "font-body": "-apple-system,system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif",
    "text-display": "clamp(2.8rem, 5.4vw, 4.4rem)",
    "text-h1":      "clamp(2.2rem, 3.4vw, 3.1rem)",   # dashboard page titles
    "text-stat":    "2.5rem",                          # stat-card values
    "text-h2":      "1.5rem",
    "text-h3":      "1.22rem",
    "text-body":    "0.97rem",
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

    # ---- Radius (premium 20–28px on the big surfaces) -------------------- #
    "r-sm": "12px",
    "r-md": "16px",
    "r-lg": "20px",
    "r-xl": "26px",

    # ---- Motion ---------------------------------------------------------- #
    "t-fast": "150ms",
    "t-base": "220ms",
    "ease":   "cubic-bezier(.33,.9,.35,1)",
}


def css_variables() -> str:
    """Render the tokens as a ``:root { … }`` CSS block."""
    body = "".join(f"--{name}:{value};" for name, value in TOKENS.items())
    return f":root{{{body}}}"
