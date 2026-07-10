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
import re

import streamlit.components.v1 as components

from components.theme import css_variables
from utils.helpers import load_brand_font_css

# Clips up to this size are embedded for the rich overlay player.
MAX_INLINE_MB = 60


def can_inline(size_bytes: int) -> bool:
    """True if the clip is small enough to embed for the overlay player."""
    return size_bytes <= MAX_INLINE_MB * 1024 * 1024


def split_caption_for_display(
    caption_text: str, min_words: int = 6, max_words: int = 12
) -> list[str]:
    """Split a full caption into readable on-screen chunks.

    Chunks are sentence- and phrase-sized (roughly ``min_words``–``max_words``
    words), broken at sentence ends and punctuation so the video overlay shows
    readable phrases rather than single words. Any 1–2 word fragment is merged
    into its neighbour, so a cue is never a lone word (unless the whole caption
    is that short). The full caption is left untouched everywhere else (e.g. the
    download), so this only affects how captions are *displayed* over the video.

    Returns a list of chunk strings; the client-side player spreads them across
    the clip's duration (each shown for a readable minimum time).
    """
    text = " ".join((caption_text or "").split())  # normalise whitespace
    if not text:
        return []
    chunks: list[str] = []
    for sentence in _split_sentences(text):
        chunks.extend(_split_long_phrase(sentence, min_words, max_words))
    return _merge_tiny(chunks)


def _split_sentences(text: str) -> list[str]:
    """Split into sentences, keeping terminal punctuation with each."""
    parts = re.findall(r"[^.!?]+[.!?]*", text)
    return [p.strip() for p in parts if p.strip()]


def _split_long_phrase(sentence: str, min_words: int, max_words: int) -> list[str]:
    """Break a long sentence at natural boundaries (commas etc.) into chunks."""
    words = sentence.split()
    if len(words) <= max_words:
        return [sentence]
    chunks: list[str] = []
    cur: list[str] = []
    for w in words:
        cur.append(w)
        at_boundary = bool(re.search(r"[,;:—–-]$", w))
        if (at_boundary and len(cur) >= min_words) or len(cur) >= max_words:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def _merge_tiny(chunks: list[str], tiny: int = 3) -> list[str]:
    """Fold 1–2 word chunks into a neighbour so no cue is a lone fragment."""
    if len(chunks) <= 1:
        return chunks
    out: list[str] = []
    for ch in chunks:
        if out and len(ch.split()) < tiny:
            out[-1] = out[-1] + " " + ch
        else:
            out.append(ch)
    # If the first chunk was tiny it stayed alone — fold it into the next.
    if len(out) > 1 and len(out[0].split()) < tiny:
        out[1] = out[0] + " " + out[1]
        out = out[1:]
    return out


# Raw string: the template contains JS regex escapes (e.g. /\s+/) that must
# reach the browser verbatim, not be interpreted as Python escapes.
_TEMPLATE = r"""
<style>
  /*FONT*/
  /*TOKENS*/
  * { box-sizing:border-box; }
  body { margin:0; background:transparent; font-family:var(--font-body); color:var(--ink); }

  /* Stacked: voice picker on top, video full-width below. */
  .wrap { display:flex; flex-direction:column; gap:var(--s-5); }

  .stage { position:relative; border-radius:var(--r-lg); overflow:hidden; background:#000;
           border:1px solid var(--line); box-shadow:var(--shadow-2); }
  .stage video { width:100%; max-height:560px; display:block; background:#000;
                 object-fit:contain; }

  /* YouTube-style subtitle: boxed line, bottom center, only while a cue
     is active. The voice chip floats top-left so the subtitle stays clean. */
  .cap { position:absolute; left:0; right:0; bottom:20px; display:flex;
         justify-content:center; padding:0 24px; pointer-events:none;
         /* Bespoke travel motion: slower + gentle ease-in-out on both
            directions so the lift/settle feels smooth, not snappy. */
         transition: bottom 480ms cubic-bezier(.4, 0, .2, 1); }
  /* Lift the subtitle clear of the native control bar while it is showing,
     then settle back to the base position when the controls auto-hide. */
  .stage.controls .cap { bottom:58px; }
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

  /* Picker header: title left, hint right on one baseline. */
  .pickhead { display:flex; align-items:baseline; justify-content:space-between;
              gap:var(--s-4); flex-wrap:wrap; margin-bottom:var(--s-3); }
  .pickhead h4 { font-family:var(--font-display); font-weight:400;
                 font-size:var(--text-h3); color:var(--ink); margin:0; }
  .hint { color:var(--ink-3); font-size:.78rem; font-style:italic; }

  /* Voice picker as a horizontal segmented row above the video. */
  .pick { display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; }
  @media (max-width:720px){ .pick { grid-template-columns:repeat(2, 1fr); } }
  @media (max-width:430px){ .pick { grid-template-columns:1fr; } }
  .pick button { display:flex; align-items:center; justify-content:center; gap:10px;
                 cursor:pointer; font-weight:500; font-size:.92rem; color:var(--ink);
                 padding:13px 14px; border-radius:var(--r-md); border:1px solid var(--line);
                 background:var(--surface); font-family:var(--font-body); white-space:nowrap;
                 transition: border-color var(--t-fast) var(--ease),
                             background var(--t-fast) var(--ease); }
  .pick button:hover { border-color:var(--line-2); background:var(--surface-2); }
  .pick button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  .pick button.active { border-color:var(--vc); background:var(--surface-2); }
  .pick button.active .nm { color:var(--vc); }
  .pick button .dot { width:9px; height:9px; border-radius:50%; flex:none;
                      background:var(--vc); }
  @media (prefers-reduced-motion: reduce) {
    * { animation:none !important; transition:none !important; }
  }
</style>

<div class="wrap">
  <div class="side">
    <div class="pickhead">
      <h4>Choose a voice</h4>
      <span class="hint">Captions appear as the clip plays — switch anytime.</span>
    </div>
    <div class="pick" id="pick"></div>
  </div>
  <div class="stage">
    <video src="__SRC__" controls autoplay muted loop playsinline></video>
    <div class="voice" id="lab"></div>
    <div class="cap"><div class="txt" id="txt"></div></div>
  </div>
</div>

<script>
  var DATA = __DATA__;
  var lab = document.getElementById('lab');
  var txt = document.getElementById('txt');
  var pick = document.getElementById('pick');
  var video = document.querySelector('video');
  var stage = document.querySelector('.stage');

  // --- Control-bar awareness ------------------------------------------ //
  // The browser draws its native control bar (scrubber, time) at the very
  // bottom, over the subtitle. There is no event for "controls shown", so
  // we mirror the browser's own logic: show on mouse activity or pause,
  // and auto-hide after a short idle while playing. A CSS class lifts the
  // caption in step, then it settles back down.
  var idle;
  function showControls(){
    stage.classList.add('controls');
    clearTimeout(idle);
    if (!video.paused) idle = setTimeout(hideControls, 2600);
  }
  function hideControls(){
    if (!video.paused) stage.classList.remove('controls');
  }
  stage.addEventListener('mousemove', showControls);
  stage.addEventListener('touchstart', showControls, {passive:true});  // touch devices
  stage.addEventListener('mouseleave', function(){
    clearTimeout(idle);
    if (!video.paused) stage.classList.remove('controls');
  });
  video.addEventListener('pause', showControls);   // controls stay up when paused
  video.addEventListener('play', showControls);    // brief show, then idle-hide

  // --- Subtitle cues -------------------------------------------------- //
  // Each caption arrives already split (server-side) into readable phrase
  // chunks of ~6-12 words. Here we spread those chunks across the clip's
  // duration, keeping each on screen for at least MIN_CUE seconds so they
  // stay readable. If the clip is too short to fit every chunk at that pace,
  // adjacent chunks are merged (a very short clip just shows whole sentences).
  var MIN_CUE = 2.0;   // seconds — minimum time a chunk stays on screen
  var cues = null;     // null -> no timing available, show full text statically

  function buildCues(chunks, fullCaption){
    var dur = video.duration;
    if (!isFinite(dur) || dur <= 0 || !chunks || chunks.length === 0) {
      cues = null;
      txt.textContent = fullCaption || '';   // graceful static fallback
      return;
    }
    var parts = chunks.slice();
    var maxN = Math.max(1, Math.floor(dur / MIN_CUE));  // cues that fit at >=2s
    if (parts.length > maxN) { parts = mergeToCount(parts, maxN); }
    var span = dur / parts.length;
    cues = parts.map(function(p, i){
      return { start: i * span, end: (i + 1) * span, text: p };
    });
    tick();
  }

  // Merge adjacent chunks (shortest pair first) until only `target` remain.
  function mergeToCount(parts, target){
    var out = parts.slice();
    while (out.length > target) {
      var bestI = 0, bestLen = Infinity;
      for (var i = 0; i < out.length - 1; i++) {
        var len = out[i].length + out[i + 1].length;
        if (len < bestLen) { bestLen = len; bestI = i; }
      }
      out[bestI] = out[bestI] + ' ' + out[bestI + 1];
      out.splice(bestI + 1, 1);
    }
    return out;
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
    buildCues(d.chunks, d.caption);
    Array.prototype.forEach.call(pick.children, function(b, idx){
      var on = idx === i;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');  // toggle state for AT
    });
  }

  // Duration is often unknown until metadata loads — rebuild then.
  video.addEventListener('loadedmetadata', function(){ render(current); });

  DATA.forEach(function(d, i){
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-pressed', 'false');  // reflects active voice; set in render()
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

  // --- Fit the iframe to content -------------------------------------- //
  // Streamlit gives the component a fixed height; the stacked layout (picker
  // row + full-width video) is taller and varies with the clip's aspect
  // ratio. The iframe is same-origin (srcdoc), so size it to its content
  // and keep it in sync as the video's dimensions settle.
  function fit(){
    if (window.frameElement) {
      window.frameElement.style.height = (document.documentElement.scrollHeight + 2) + 'px';
    }
  }
  new ResizeObserver(fit).observe(document.body);
  window.addEventListener('load', fit);
  video.addEventListener('loadedmetadata', fit);
</script>
"""


def render_captioned_player(
    video_bytes: bytes,
    mime: str,
    captions: dict[str, str],
    styles: list[dict],
    height: int = 740,
) -> None:
    """Render the video with a client-side switchable caption overlay.

    ``height`` is only the initial iframe height; a script inside the
    component resizes the iframe to fit the stacked layout once it loads.
    """
    src = f"data:{mime or 'video/mp4'};base64,{base64.b64encode(video_bytes).decode('ascii')}"
    data = [
        {
            "key": s["key"],
            "title": s["title"],
            "accent": s["accent"],
            "caption": captions.get(s["key"], ""),
            "chunks": split_caption_for_display(captions.get(s["key"], "")),
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
