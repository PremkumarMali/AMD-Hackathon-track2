"""Interactive captioned video player with YouTube-style timed subtitles.

The selected voice's caption is segmented into short cues and shown in a
boxed subtitle at the bottom of the frame, synced to playback time — it
reads like YouTube captions rather than a static overlay. The four voice
buttons swap the cue track *client-side* via JavaScript, so switching
styles never triggers a Streamlit rerun — the video keeps playing while
the user flips between voices.

The clip is inlined as a base64 data URI so no static-file server is needed.
That's fine for the short clips this app targets; ``can_inline()`` guards
against inlining very large files (the app falls back to a simpler player).
"""

from __future__ import annotations

import base64
import json

import streamlit.components.v1 as components

from components.theme import css_variables
from utils.helpers import load_brand_font_css

# Clips up to this size are embedded for the rich overlay player.
MAX_INLINE_MB = 60


def can_inline(size_bytes: int) -> bool:
    """True if the clip is small enough to embed for the overlay player."""
    return size_bytes <= MAX_INLINE_MB * 1024 * 1024


# Raw string: the template contains JS regex escapes (e.g. /\s+/) that must
# reach the browser verbatim, not be interpreted as Python escapes.
_TEMPLATE = r"""
<style>
  /*FONT*/
  /*TOKENS*/
  * { box-sizing:border-box; }
  body { margin:0; background:transparent; font-family:var(--font-body); color:var(--ink); }

  .wrap { display:grid; grid-template-columns: minmax(0,1.7fr) minmax(250px,1fr);
          gap:var(--s-5); align-items:start; }
  @media (max-width:820px){ .wrap{ grid-template-columns:1fr; } }

  .stage { position:relative; border-radius:var(--r-lg); overflow:hidden; background:#000;
           border:1px solid var(--line); box-shadow:var(--shadow-2); }
  .stage video { width:100%; max-height:520px; display:block; background:#000; }

  /* YouTube-style subtitle: boxed line, bottom center, only while a cue
     is active. The voice chip floats top-left so the subtitle stays clean. */
  .cap { position:absolute; left:0; right:0; bottom:20px; display:flex;
         justify-content:center; padding:0 24px; pointer-events:none; }
  .cap .txt { display:inline-block; max-width:86%; text-align:center;
              background:rgba(0,0,0,.72); color:#fff; padding:7px 14px 8px;
              border-radius:8px; font-family:var(--font-body);
              font-size:clamp(.95rem,1.7vw,1.3rem); line-height:1.45;
              transition: opacity var(--t-fast) var(--ease); }
  .cap .txt:empty { opacity:0; }
  .voice { position:absolute; top:12px; left:12px; font-weight:600;
           font-size:.64rem; letter-spacing:.18em; text-transform:uppercase;
           color:#fff; background:rgba(0,0,0,.55); padding:5px 11px;
           border-radius:999px; pointer-events:none; }

  .side h4 { font-family:var(--font-display); font-weight:400; font-size:var(--text-h3);
             color:var(--ink); margin:2px 0 14px; }
  .pick { display:flex; flex-direction:column; gap:10px; }
  .pick button { display:flex; align-items:center; gap:11px; text-align:left; cursor:pointer;
                 width:100%; font-weight:500; font-size:.96rem; color:var(--ink);
                 padding:14px 16px; border-radius:var(--r-md); border:1px solid var(--line);
                 background:var(--surface); font-family:var(--font-body);
                 transition: border-color var(--t-fast) var(--ease),
                             background var(--t-fast) var(--ease); }
  .pick button:hover { border-color:var(--line-2); background:var(--surface-2); }
  .pick button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  .pick button.active { border-color:var(--vc); background:var(--surface-2); }
  .pick button.active .nm { color:var(--vc); }
  .pick button .dot { width:9px; height:9px; border-radius:50%; flex:none;
                      background:var(--vc); }
  .hint { color:var(--ink-3); font-size:.78rem; font-style:italic; margin-top:14px; }
  @media (prefers-reduced-motion: reduce) {
    * { animation:none !important; transition:none !important; }
  }
</style>

<div class="wrap">
  <div class="stage">
    <video src="__SRC__" controls autoplay muted loop playsinline></video>
    <div class="voice" id="lab"></div>
    <div class="cap"><div class="txt" id="txt"></div></div>
  </div>
  <div class="side">
    <h4>Choose a voice</h4>
    <div class="pick" id="pick"></div>
    <div class="hint">Captions appear as the clip plays — switch voices anytime.</div>
  </div>
</div>

<script>
  var DATA = __DATA__;
  var lab = document.getElementById('lab');
  var txt = document.getElementById('txt');
  var pick = document.getElementById('pick');
  var video = document.querySelector('video');

  // --- Subtitle cues -------------------------------------------------- //
  // The engine writes one caption per voice for the whole clip; to read
  // like YouTube subtitles it is segmented into cues sized for ~3s each
  // (never fewer than 4 words per cue) and spread across the duration.
  var cues = null;   // null -> no timing available, show full text statically

  function buildCues(caption){
    var dur = video.duration;
    var words = caption.split(/\s+/).filter(Boolean);
    if (!isFinite(dur) || dur <= 0 || words.length === 0) {
      cues = null;
      txt.textContent = caption;   // graceful fallback: static caption
      return;
    }
    var target = Math.max(1, Math.round(dur / 3));          // ~3s per cue
    var n = Math.min(target, Math.ceil(words.length / 4));  // >=4 words each
    var per = Math.ceil(words.length / n);
    var parts = [];
    for (var i = 0; i < words.length; i += per) {
      parts.push(words.slice(i, i + per).join(' '));
    }
    var span = dur / parts.length;
    cues = parts.map(function(p, i){
      return { start: i * span, end: (i + 1) * span, text: p };
    });
    tick();
  }

  function tick(){
    if (!cues) return;
    var t = video.currentTime;
    var hit = '';
    for (var i = 0; i < cues.length; i++) {
      if (t >= cues[i].start && t < cues[i].end) { hit = cues[i].text; break; }
    }
    if (txt.textContent !== hit) txt.textContent = hit;
  }

  video.addEventListener('timeupdate', tick);
  video.addEventListener('seeked', tick);

  // --- Voice switching (client-side, playback never interrupted) ------ //
  var current = 0;

  function render(i){
    current = i;
    var d = DATA[i];
    lab.textContent = d.title;
    buildCues(d.caption);
    Array.prototype.forEach.call(pick.children, function(b, idx){
      b.classList.toggle('active', idx === i);
    });
  }

  // Duration is often unknown until metadata loads — rebuild then.
  video.addEventListener('loadedmetadata', function(){ render(current); });

  DATA.forEach(function(d, i){
    var b = document.createElement('button');
    b.style.setProperty('--vc', d.accent);  // voice color; CSS handles states
    var dot = document.createElement('span');
    dot.className = 'dot';
    var nm = document.createElement('span');
    nm.className = 'nm'; nm.textContent = d.title;
    b.appendChild(dot);
    b.appendChild(nm);
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
        .replace("/*TOKENS*/", css_variables())
        .replace("__SRC__", src)
        .replace("__DATA__", payload)
    )
    components.html(html, height=height, scrolling=False)
