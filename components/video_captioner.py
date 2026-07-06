"""Interactive captioned video player.

Plays the uploaded clip with the selected caption overlaid at the bottom
(like a subtitle). The four voice buttons swap the caption *client-side*
via JavaScript, so switching styles never triggers a Streamlit rerun — the
video keeps playing while the user flips between voices.

The clip is inlined as a base64 data URI so no static-file server is needed.
That's fine for the short clips this app targets; ``can_inline()`` guards
against inlining very large files (the app falls back to a simpler player).
"""

from __future__ import annotations

import base64
import json

import streamlit.components.v1 as components

from utils.helpers import load_brand_font_css

# Clips up to this size are embedded for the rich overlay player.
MAX_INLINE_MB = 60


def can_inline(size_bytes: int) -> bool:
    """True if the clip is small enough to embed for the overlay player."""
    return size_bytes <= MAX_INLINE_MB * 1024 * 1024


_TEMPLATE = """
<style>
  /*FONT*/
  :root {
    --ink:#1c1815; --muted:#857a6c; --line:#e7ded0; --surface:#fffdf8; --accent:#b45309;
    --ui:-apple-system,system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    --disp:'Mortane','Playfair Display',Georgia,'Times New Roman',serif;
  }
  @media (prefers-color-scheme:dark){
    :root{ --ink:#f3ece0; --muted:#a89c8b; --line:#342b20; --surface:#211b14; --accent:#e0913f; }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:transparent; font-family:var(--ui); }

  .wrap { display:grid; grid-template-columns: minmax(0,1.7fr) minmax(250px,1fr);
          gap:24px; align-items:start; }
  @media (max-width:820px){ .wrap{ grid-template-columns:1fr; } }

  .stage { position:relative; border-radius:16px; overflow:hidden; background:#000;
           box-shadow:0 18px 50px rgba(0,0,0,.38); }
  .stage video { width:100%; max-height:520px; display:block; background:#000; }

  .cap { position:absolute; left:0; right:0; bottom:0; padding:60px 30px 26px;
         background:linear-gradient(to top, rgba(0,0,0,.9) 0%, rgba(0,0,0,.5) 45%, rgba(0,0,0,0) 100%);
         pointer-events:none; }
  .cap .lab { font-weight:600; font-size:.7rem; letter-spacing:.2em; text-transform:uppercase;
              margin-bottom:9px; }
  .cap .txt { font-family:var(--disp); font-size:clamp(1.1rem,1.9vw,1.65rem); line-height:1.38;
              color:#fff; text-shadow:0 2px 12px rgba(0,0,0,.75); }

  .side h4 { font-family:var(--disp); font-weight:400; font-size:1.2rem; color:var(--ink);
             margin:2px 0 14px; }
  .pick { display:flex; flex-direction:column; gap:10px; }
  .pick button { display:flex; align-items:center; gap:11px; text-align:left; cursor:pointer;
                 width:100%; font-weight:500; font-size:.96rem; color:var(--ink);
                 padding:14px 16px; border-radius:12px; border:1px solid var(--line);
                 background:var(--surface); transition:.15s ease; font-family:var(--ui); }
  .pick button:hover { border-color:var(--muted); }
  .pick button.active { color:#fff; border-color:transparent; }
  .pick button .dot { width:9px; height:9px; border-radius:50%; flex:none; }
  .pick button.active .dot { background:#fff !important; }
  .hint { color:var(--muted); font-size:.78rem; font-style:italic; margin-top:14px; }
</style>

<div class="wrap">
  <div class="stage">
    <video src="__SRC__" controls autoplay muted loop playsinline></video>
    <div class="cap"><div class="lab" id="lab"></div><div class="txt" id="txt"></div></div>
  </div>
  <div class="side">
    <h4>Choose a voice</h4>
    <div class="pick" id="pick"></div>
    <div class="hint">The clip keeps playing as you switch voices.</div>
  </div>
</div>

<script>
  var DATA = __DATA__;
  var lab = document.getElementById('lab');
  var txt = document.getElementById('txt');
  var pick = document.getElementById('pick');

  function render(i){
    var d = DATA[i];
    lab.textContent = d.title; lab.style.color = d.accent;
    txt.textContent = d.caption;
    Array.prototype.forEach.call(pick.children, function(b, idx){
      var on = idx === i;
      b.classList.toggle('active', on);
      b.style.background = on ? d.accent : '';
    });
  }

  DATA.forEach(function(d, i){
    var b = document.createElement('button');
    var dot = document.createElement('span');
    dot.className = 'dot'; dot.style.background = d.accent;
    b.appendChild(dot);
    b.appendChild(document.createTextNode(d.title));
    b.addEventListener('click', function(){ render(i); });
    pick.appendChild(b);
  });
  render(0);
</script>
"""


def render_captioned_player(
    video_bytes: bytes,
    mime: str,
    captions: dict[str, str],
    styles: list[dict],
    height: int = 600,
) -> None:
    """Render the video with a client-side switchable caption overlay."""
    src = f"data:{mime or 'video/mp4'};base64,{base64.b64encode(video_bytes).decode('ascii')}"
    data = [
        {
            "key": s["key"],
            "title": s["title"],
            "accent": s["accent"],
            "caption": captions.get(s["key"], ""),
        }
        for s in styles
    ]
    payload = json.dumps(data).replace("</", "<\\/")  # safe inside <script>

    html = (
        _TEMPLATE
        .replace("/*FONT*/", load_brand_font_css("Mortane"))
        .replace("__SRC__", src)
        .replace("__DATA__", payload)
    )
    components.html(html, height=height, scrolling=False)
