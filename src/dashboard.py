"""
BugVertex AI dashboard (blueprint theme).

Main flow (top of the page):  paste buggy code + tests -> error -> root cause -> fix -> proof.
Tabs below:  How it works | Proof (benchmark) | Search past bugs | Routing.

Run from the Engine folder:
    python -m streamlit run src\\dashboard.py
"""

import json
import os
import re
from html import escape
from pathlib import Path

import streamlit as st

import core
import patcher
import fx

BENCH_DIR = Path(core.BASE_DIR) / "benchmark"
BUGS_DIR = BENCH_DIR / "bugs"
EVAL_FILE = BENCH_DIR / "results" / "patch_eval.json"
NONE_CHOICE = "(none)"

# ---------------------------------------------------------
# Blueprint styling
# ---------------------------------------------------------
BLUEPRINT_CSS = """
<style>
:root {
  --bp-bg: #F4F7FB; --bp-panel: rgba(255,255,255,0.92);
  --bp-line: rgba(31,95,191,0.07); --bp-major: rgba(31,95,191,0.16);
  --bp-ink: #1B2A41; --bp-dim: #566780; --bp-cyan: #1F5FBF;
  --bp-ok: #17784B; --bp-bad: #C03030; --bp-amber: #8F5F0A;
}
[data-testid="stAppViewContainer"] {
  background-color: var(--bp-bg);
  background-image:
    linear-gradient(var(--bp-major) 1px, transparent 1px),
    linear-gradient(90deg, var(--bp-major) 1px, transparent 1px),
    linear-gradient(var(--bp-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--bp-line) 1px, transparent 1px);
  background-size: 120px 120px, 120px 120px, 24px 24px, 24px 24px;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: #EAF0F9;
  border-right: 1px solid rgba(31,95,191,0.18);
}
h1, h2, h3 { letter-spacing: 0.04em; }
h2, h3 { color: var(--bp-cyan) !important; border-bottom: 1px dashed var(--bp-major); padding-bottom: 4px; }
button[data-baseweb="tab"] { text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.8rem; }
.stButton > button {
  border-radius: 0; border: 1px solid var(--bp-cyan); background: rgba(31,95,191,0.08);
  color: var(--bp-cyan); text-transform: uppercase; letter-spacing: 0.1em;
}
.stButton > button:hover { background: #1F5FBF; color: #FFFFFF; border-color: #1F5FBF; }
textarea, [data-baseweb="textarea"], [data-baseweb="select"] > div {
  border-radius: 0 !important; background: rgba(255,255,255,0.95) !important;
}
[data-testid="stMetric"] {
  border: 1px solid var(--bp-major); background: var(--bp-panel); padding: 10px 14px; border-radius: 0;
}
[data-testid="stAlert"] { border-radius: 0; }
[data-testid="stExpander"] { border-radius: 0; border: 1px dashed var(--bp-major); }

.bp-sheet { position: relative; border: 1px solid var(--bp-major); background: var(--bp-panel);
  padding: 12px 16px; margin: 10px 0; font-family: ui-monospace, Consolas, monospace; }
.bp-sheet::before, .bp-sheet::after { content: ""; position: absolute; width: 12px; height: 12px;
  border: 2px solid var(--bp-cyan); }
.bp-sheet::before { top: -2px; left: -2px; border-right: none; border-bottom: none; }
.bp-sheet::after { bottom: -2px; right: -2px; border-left: none; border-top: none; }
.bp-head { display: flex; justify-content: space-between; border-bottom: 1px dashed var(--bp-major);
  padding-bottom: 6px; margin-bottom: 8px; color: var(--bp-dim); font-size: 0.72rem;
  letter-spacing: 0.14em; text-transform: uppercase; }
.bp-note { color: var(--bp-amber); font-size: 0.8rem; border-left: 2px solid var(--bp-amber);
  padding: 2px 0 2px 10px; margin: 8px 0; font-family: ui-monospace, Consolas, monospace; }
.bp-note b { letter-spacing: 0.1em; }

.bp-diff { overflow-x: auto; font-size: 0.82rem; line-height: 1.55; }
.bp-dimline { color: var(--bp-cyan); font-size: 0.74rem; letter-spacing: 0.08em; margin: 8px 0 4px 0;
  border-top: 1px dashed var(--bp-cyan); border-bottom: 1px dashed var(--bp-cyan); padding: 2px 0; text-align: center; }
.bp-row { display: grid; grid-template-columns: 38px 46px 1fr 40px; align-items: baseline; }
.bp-ln { color: var(--bp-dim); text-align: right; padding-right: 10px; }
.bp-tag { color: var(--bp-dim); font-size: 0.68rem; letter-spacing: 0.1em; }
.bp-code { white-space: pre; }
.bp-mark { color: var(--bp-amber); font-weight: 700; text-align: center; }
.bp-add { background: rgba(23,120,75,0.10); }
.bp-add .bp-code, .bp-add .bp-tag { color: #17784B; }
.bp-del { background: rgba(192,48,48,0.10); }
.bp-del .bp-code { color: #C03030; text-decoration: line-through; text-decoration-color: rgba(192,48,48,0.7); }
.bp-del .bp-tag { color: #C03030; }
.bp-legend { color: var(--bp-dim); font-size: 0.7rem; letter-spacing: 0.08em; margin-top: 10px; }

@keyframes scan { 0% { transform: translateY(-220px); } 100% { transform: translateY(110vh); } }
@keyframes dashflow { to { stroke-dashoffset: -24; } }
@keyframes pulse { 0%, 100% { filter: drop-shadow(0 0 1px rgba(31,95,191,0.09)); } 50% { filter: drop-shadow(0 0 7px rgba(31,95,191,0.43)); } }
@keyframes ring { from { stroke-dasharray: 0 189; } }
@keyframes fadein { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: none; } }
@keyframes blink { 50% { opacity: 0; } }
@keyframes stamp { 0% { transform: scale(2.6) rotate(-14deg); opacity: 0; } 55% { transform: scale(.94) rotate(-6deg); opacity: 1; } 75% { transform: scale(1.04) rotate(-6deg); } 100% { transform: scale(1) rotate(-6deg); opacity: 1; } }
@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes glowbad { 0%, 100% { box-shadow: 0 0 0 rgba(192,48,48,0.0); } 50% { box-shadow: 0 0 14px rgba(192,48,48,0.25); } }

[data-testid="stMainBlockContainer"] { position: relative; z-index: 1; }

.bp-stats { display: grid; grid-template-columns: repeat(4, 1fr); }
.bp-stat { display: flex; align-items: center; gap: 14px; padding: 14px 16px; border-right: 1px solid var(--bp-major); }
.bp-stat:last-child { border-right: none; }
.bp-stat svg { flex: none; }
.bp-stat-val { font-size: 1.9rem; font-weight: 700; color: #0F2A4A; line-height: 1; }
.bp-stat-lab { color: var(--bp-dim); font-size: .66rem; letter-spacing: .16em; text-transform: uppercase; margin-top: 4px; }
.bp-stat-sub { color: var(--bp-cyan); font-size: .75rem; }

.bp-flow .flow { stroke-dasharray: 6 6; animation: dashflow .9s linear infinite; }
.bp-flow .node { animation: pulse 3.2s ease-in-out infinite; }

.bp-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 10px 0 16px 0; }
.bp-card { border: 1px solid var(--bp-major); padding: 14px 16px; background: linear-gradient(160deg, rgba(236,243,252,0.94), rgba(255,255,255,0.92));
  transition: transform .2s, box-shadow .2s, border-color .2s; animation: rise .6s ease-out both; }
.bp-card:hover { transform: translateY(-4px); border-color: var(--bp-cyan); box-shadow: 0 6px 22px rgba(31,95,191,0.11); }
.bp-card-num { color: var(--bp-cyan); font-size: 1.6rem; font-weight: 700; letter-spacing: .1em; }
.bp-card-title { color: #0F2A4A; letter-spacing: .12em; font-size: .85rem; margin: 4px 0 6px 0; }
.bp-card-text { color: var(--bp-dim); font-size: .78rem; line-height: 1.5; }

.bp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 10px 0; }
.bp-tile { position: relative; border: 1px solid var(--bp-ok); background: rgba(23,120,75,.07); padding: 10px 12px;
  transition: transform .2s, box-shadow .2s; animation: rise .5s ease-out both; font-family: ui-monospace, Consolas, monospace; }
.bp-tile:hover { transform: translateY(-3px) scale(1.03); box-shadow: 0 0 16px rgba(23,120,75,0.2); }
.bp-tile.bad { border-color: var(--bp-bad); background: rgba(192,48,48,.09); animation: rise .5s ease-out both, glowbad 2.4s ease-in-out infinite; }
.bp-tile.bad:hover { box-shadow: 0 0 18px rgba(192,48,48,0.27); }
.bp-tile b { display: block; color: #0F2A4A; font-size: 1.15rem; letter-spacing: .08em; }
.bp-tile span { display: block; color: var(--bp-dim); font-size: .68rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bp-tile i { position: absolute; top: 8px; right: 10px; font-style: normal; font-size: .7rem; color: var(--bp-amber); }
.bp-tile em { position: absolute; bottom: 8px; right: 10px; font-style: normal; font-size: .66rem; letter-spacing: .1em; color: var(--bp-ok); }
.bp-tile.bad em { color: var(--bp-bad); }

.bp-stamp { display: inline-block; margin: 8px 0 4px 8px; padding: 6px 22px; border: 4px solid var(--bp-ok); color: var(--bp-ok);
  font-size: 1.9rem; font-weight: 800; letter-spacing: .24em; transform: rotate(-6deg); animation: stamp .7s ease-out both;
   box-shadow: 0 0 18px rgba(23,120,75,0.16), inset 0 0 12px rgba(23,120,75,0.09);
  font-family: ui-monospace, Consolas, monospace; background: rgba(23,120,75,.06); }
.bp-stamp.bad { border-color: var(--bp-bad); color: var(--bp-bad); 
  box-shadow: 0 0 18px rgba(192,48,48,0.16), inset 0 0 12px rgba(192,48,48,0.09); background: rgba(192,48,48,.06); }
.bp-stamp.neutral { border-color: var(--bp-cyan); color: var(--bp-cyan);  box-shadow: none; background: none; }
.bp-row { animation: fadein .45s ease-out both; }
.stButton > button { transition: box-shadow .2s, background .2s; box-shadow: 0 0 0 rgba(31,95,191,0.0); }
.stButton > button:hover { box-shadow: 0 0 16px rgba(31,95,191,0.25); }
button[data-baseweb="tab"][aria-selected="true"] {  }
@media (max-width: 900px) { .bp-hero-top, .bp-stats, .bp-cards { grid-template-columns: 1fr 1fr; } .bp-hero-name { font-size: 1.6rem; } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

.bv-box p, .bv-rc, .bp-card-text, .bp-note, .bv-proof-big, .bv-proof-sub, .bv-tag, .bv-who {
  font-family: "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif; }
.bv-box p, .bv-rc { font-size: .95rem; }
.bv-tag { font-size: 1.15rem; }
.bp-note { font-size: .88rem; }

[data-testid="stSidebar"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] li,
[data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: var(--bp-ink); }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] small { color: var(--bp-dim); }
[data-testid="stMarkdownContainer"] code, [data-testid="stSidebar"] code {
  background: rgba(31, 95, 191, 0.10) !important; color: #174A9C !important; }
[data-baseweb="select"] > div { background: #FFFFFF !important; color: var(--bp-ink) !important; }
[data-baseweb="select"] span, [data-baseweb="select"] div { color: var(--bp-ink); }
[data-baseweb="popover"] li, [data-baseweb="menu"] li { color: var(--bp-ink); }
textarea { color: var(--bp-ink) !important; }
@keyframes linkflow { to { background-position: 12px 0; } }
.bv-hero { position: relative; border: 2px solid var(--bp-cyan); padding: 20px 24px 16px; margin: 2px 0 14px 0;
  background: linear-gradient(135deg, rgba(236,243,252,0.94), rgba(255,255,255,0.95));
  box-shadow: 0 0 28px rgba(31,95,191,0.09), inset 0 0 40px rgba(31,95,191,0.02);
  font-family: ui-monospace, Consolas, monospace; animation: rise .7s ease-out both; }
.bv-name { font-size: 2.4rem; font-weight: 800; letter-spacing: .18em; line-height: 1.1;
  background: linear-gradient(90deg, #0F2A4A, #1F5FBF 55%, #17784B); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.bv-tag { color: var(--bp-ink); font-size: 1.1rem; margin: 6px 0 16px 0; }
.bv-two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.bv-box { border: 1px solid var(--bp-major); padding: 12px 16px; background: rgba(255,255,255,0.75); }
.bv-box.prob { border-left: 3px solid var(--bp-bad); }
.bv-box.ans { border-left: 3px solid var(--bp-ok); }
.bv-box-h { letter-spacing: .18em; font-size: .7rem; margin-bottom: 6px; }
.bv-box.prob .bv-box-h { color: var(--bp-bad); }
.bv-box.ans .bv-box-h { color: var(--bp-ok); }
.bv-box p { margin: 0; color: var(--bp-ink); font-size: .88rem; line-height: 1.6; }
.bv-who { margin-top: 12px; color: var(--bp-dim); font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; }
.bv-who b { color: var(--bp-cyan); font-weight: 600; }

.bv-path { display: grid; grid-template-columns: 1fr 34px 1fr 34px 1fr; align-items: center; margin: 0 0 12px 0; }
.bv-pstep { border: 1px solid var(--bp-cyan); background: rgba(31,95,191,.07); padding: 10px 14px;
  font-family: ui-monospace, Consolas, monospace; animation: rise .6s ease-out both; }
.bv-pstep b { display: block; color: var(--bp-cyan); font-size: 1.5rem; line-height: 1.1; }
.bv-pstep span { color: #0F2A4A; font-size: .78rem; letter-spacing: .1em; }
.bv-arrow { text-align: center; color: var(--bp-cyan); font-size: 1.3rem; animation: fx-flicker 1.6s ease-in-out infinite; }

.bv-pipe { display: flex; align-items: stretch; margin: 12px 0 6px 0; font-family: ui-monospace, Consolas, monospace; }
.bv-node { flex: 1; border: 1px solid var(--bp-major); padding: 10px 12px; background: rgba(255,255,255,0.92); }
.bv-node small { display: block; color: var(--bp-dim); letter-spacing: .14em; font-size: .62rem; }
.bv-node div { color: #0F2A4A; font-size: .8rem; letter-spacing: .08em; margin-top: 2px; }
.bv-node.done { border-color: var(--bp-ok); background: rgba(23,120,75,.08); }
.bv-node.done small { color: var(--bp-ok); }
.bv-node.fail { border-color: var(--bp-bad); background: rgba(192,48,48,.09); }
.bv-node.fail small { color: var(--bp-bad); }
.bv-node.skip { border-style: dashed; opacity: .7; }
.bv-link { flex: none; width: 30px; align-self: center; height: 2px; background-size: 12px 2px;
  background-image: repeating-linear-gradient(90deg, #1F5FBF 0 6px, transparent 6px 12px); animation: linkflow .8s linear infinite; }

.bv-sec { display: flex; align-items: baseline; gap: 12px; margin: 22px 0 8px 0; padding-bottom: 6px;
  border-bottom: 1px dashed var(--bp-major); font-family: ui-monospace, Consolas, monospace; }
.bv-sec b { color: var(--bp-cyan); font-size: 1.5rem; }
.bv-sec span { color: #0F2A4A; letter-spacing: .16em; font-size: .9rem; }
.bv-sec i { color: var(--bp-dim); font-style: normal; font-size: .74rem; margin-left: auto; }
.bv-rc { border: 1px solid var(--bp-cyan); border-left: 4px solid var(--bp-cyan); padding: 12px 16px;
  background: rgba(31,95,191,.06); color: var(--bp-ink); font-size: .92rem; line-height: 1.6;
  font-family: ui-monospace, Consolas, monospace; }
.bv-proof { display: flex; align-items: center; gap: 18px; padding: 14px 18px; border: 1px solid var(--bp-ok);
  background: rgba(23,120,75,.07); margin: 10px 0; font-family: ui-monospace, Consolas, monospace; }
.bv-proof-big { font-size: 1.3rem; color: #0F2A4A; line-height: 1.4; }
.bv-proof-sub { color: var(--bp-dim); font-size: .82rem; margin-top: 4px; }
@media (max-width: 900px) {
  .bv-two, .bv-path { grid-template-columns: 1fr; } .bv-arrow { display: none; }
  .bv-pipe { flex-direction: column; } .bv-link { width: 2px; height: 16px; background-image: repeating-linear-gradient(180deg, #1F5FBF 0 6px, transparent 6px 12px); }
}
</style>
"""

st.set_page_config(page_title="BugVertex AI", page_icon="🐞", layout="wide")
st.markdown(BLUEPRINT_CSS, unsafe_allow_html=True)
st.markdown(fx.FX_CSS, unsafe_allow_html=True)


def sheet_head(number, title, note=""):
    st.html(
        f'<div class="bp-head"><span>SHEET {number} OF 4 &mdash; {escape(title)}</span>'
        f"<span>{escape(note)}</span></div>"
    )


def note_html(label, text):
    return f'<div class="bp-note"><b>{escape(label)}:</b> {escape(text)}</div>'


def render_diff_html(diff, left="buggy.py", right="patched.py"):
    """Draw a unified diff as an engineering-drawing style sheet."""
    if not diff:
        return ""
    rows, old_ln, new_ln, marker, in_change, detail = [], 0, 0, 0, False, 0

    def row(cls, ln, tag, text, mark=""):
        delay = 0.12 * len(rows)
        return (f'<div class="bp-row {cls}" style="animation-delay:{delay:.2f}s"><span class="bp-ln">{ln}</span>'
                f'<span class="bp-tag">{tag}</span>'
                f'<span class="bp-code">{escape(text) if text else "&nbsp;"}</span>'
                f'<span class="bp-mark">{mark}</span></div>')

    for raw in diff.splitlines():
        if raw.startswith(("---", "+++", "\\")):
            continue
        if raw.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", raw)
            if m:
                old_ln, new_ln = int(m.group(1)), int(m.group(3))
                o_len, n_len = int(m.group(2) or 1), int(m.group(4) or 1)
                detail += 1
                label = chr(64 + min(detail, 26))
                rows.append(
                    f'<div class="bp-dimline">&#9668;&mdash; DETAIL {label}: {escape(left)} '
                    f"L{old_ln}-{old_ln + o_len - 1} &rarr; {escape(right)} "
                    f"L{new_ln}-{new_ln + n_len - 1} &mdash;&#9658;</div>"
                )
            in_change = False
            continue
        sign, text = raw[:1], raw[1:]
        if sign == "-":
            mark = ""
            if not in_change:
                marker += 1
                mark = f"&#9651;{marker}"
            rows.append(row("bp-del", old_ln, "DEL", text, mark))
            old_ln += 1
            in_change = True
        elif sign == "+":
            mark = ""
            if not in_change:
                marker += 1
                mark = f"&#9651;{marker}"
            rows.append(row("bp-add", new_ln, "ADD", text, mark))
            new_ln += 1
            in_change = True
        else:
            rows.append(row("", new_ln, "", text))
            old_ln += 1
            new_ln += 1
            in_change = False

    return (
        '<div class="bp-sheet"><div class="bp-head"><span>PATCH DRAWING &mdash; '
        f"{escape(left)} &rarr; {escape(right)}</span><span>REVISION MARKS: {marker}</span></div>"
        f'<div class="bp-diff">{"".join(rows)}</div>'
        '<div class="bp-legend">&#9651;n = revision mark &nbsp;|&nbsp; DEL = line removed '
        "&nbsp;|&nbsp; ADD = line added</div></div>"
    )


def flow_svg(verdict=None):
    """The repair loop as an animated flow diagram. The final box shows the latest verdict."""
    if verdict == "verified":
        end_label, end_stroke, end_fill = "VERIFIED", "#17784B", "rgba(23,120,75,0.20)"
    elif verdict == "not_verified":
        end_label, end_stroke, end_fill = "NOT VERIFIED", "#C03030", "rgba(192,48,48,0.20)"
    else:
        end_label, end_stroke, end_fill = "VERDICT", "#1F5FBF", "none"

    boxes = [
        (10, ["BUGGY CODE", "+ TESTS"], "#1F5FBF", "none"),
        (200, ["RUN TESTS", "(EXPECT FAIL)"], "#1F5FBF", "none"),
        (390, ["LLM PROPOSES", "FULL FIX"], "#1F5FBF", "none"),
        (580, ["RUN TESTS", "ON THE FIX"], "#1F5FBF", "none"),
        (770, [end_label], end_stroke, end_fill),
    ]
    parts = [
        '<svg viewBox="0 0 920 180" width="100%" xmlns="http://www.w3.org/2000/svg" '
        'font-family="ui-monospace, Consolas, monospace">',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'fill="#1F5FBF"/></marker></defs>',
    ]
    for i, (x, lines, stroke, fill) in enumerate(boxes, start=1):
        parts.append(f'<rect class="node" style="animation-delay:{i * 0.45:.2f}s" x="{x}" y="30" '
                     f'width="140" height="56" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        parts.append(f'<text x="{x + 4}" y="24" fill="#566780" font-size="10">[{i}]</text>')
        if len(lines) == 2:
            parts.append(f'<text x="{x + 70}" y="54" fill="#1B2A41" font-size="12" '
                         f'text-anchor="middle">{escape(lines[0])}</text>')
            parts.append(f'<text x="{x + 70}" y="72" fill="#1B2A41" font-size="12" '
                         f'text-anchor="middle">{escape(lines[1])}</text>')
        else:
            parts.append(f'<text x="{x + 70}" y="63" fill="{stroke}" font-size="14" '
                         f'font-weight="700" text-anchor="middle">{escape(lines[0])}</text>')
    for x in (150, 340, 530, 720):
        parts.append(f'<line class="flow" x1="{x}" y1="58" x2="{x + 48}" y2="58" stroke="#1F5FBF" '
                     'stroke-width="2" marker-end="url(#arr)"/>')
    parts.append('<text x="745" y="50" fill="#17784B" font-size="10" text-anchor="middle">PASS</text>')
    parts.append('<path class="flow" d="M650,88 V142 H460 V90" fill="none" stroke="#8F5F0A" stroke-width="2" '
                 'marker-end="url(#arr)"/>')
    parts.append('<text x="555" y="136" fill="#8F5F0A" font-size="10" text-anchor="middle">'
                 "FAIL: RETRY WITH FEEDBACK (MAX 3)</text>")
    parts.append('<text x="10" y="172" fill="#566780" font-size="10">FIG. 1 &#8212; BOUNDED REPAIR '
                 "LOOP. THE MODEL NEVER SEES THE KNOWN FIX.</text>")
    parts.append("</svg>")
    return '<div class="bp-sheet bp-flow">' + "".join(parts) + "</div>"


def load_eval():
    if EVAL_FILE.exists():
        try:
            return json.loads(EVAL_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None


def ring_svg(frac, color):
    """A progress ring that animates from empty to `frac` (0 to 1)."""
    frac = max(0.0, min(1.0, frac))
    return (
        '<svg width="76" height="76" viewBox="0 0 76 76" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="38" cy="38" r="30" fill="none" stroke="rgba(31,95,191,0.15)" stroke-width="7"/>'
        f'<circle cx="38" cy="38" r="30" fill="none" stroke="{color}" stroke-width="7" '
        f'stroke-linecap="round" transform="rotate(-90 38 38)" '
        f'style="stroke-dasharray:{frac * 188.5:.1f} 188.5;animation:ring 1.6s ease-out both"/>'
        "</svg>"
    )


def hero_html():
    return (
        '<div class="bv-hero"><div class="bv-name">BUGVERTEX AI</div>'
        '<div class="bv-tag bp-cursor">Find the bug. Write the fix. Prove it works</div>'
        '<div class="bv-two">'
        '<div class="bv-box prob"><div class="bv-box-h">THE PROBLEM</div>'
        "<p>Debugging eats hours. AI assistants can suggest fixes that look right but are wrong, "
        "and developers still have to check every one by hand.</p></div>"
        '<div class="bv-box ans"><div class="bv-box-h">OUR ANSWER</div>'
        "<p>BugVertex reads the error your tests find, explains the root cause using similar past bugs, "
        "writes a fix, then runs your tests on it in a sandbox. Only fixes that pass are marked VERIFIED.</p></div>"
        "</div>"
        '<div class="bv-who">Built for: <b>developers</b> &middot; <b>QA engineers</b> &middot; '
        "<b>students learning to debug</b></div></div>"
    )


def path_ribbon_html():
    steps = [("1", "PASTE YOUR BUGGY CODE"), ("2", "ADD TESTS THAT DEFINE CORRECT"), ("3", "CLICK FIND AND FIX")]
    parts = []
    for i, (n, t) in enumerate(steps):
        parts.append(f'<div class="bv-pstep" style="animation-delay:{i * 0.15:.2f}s"><b>{n}</b><span>{t}</span></div>')
        if i < 2:
            parts.append('<div class="bv-arrow">&#9658;</div>')
    return f'<div class="bv-path">{"".join(parts)}</div>'


def section_label_html(num, title, sub=""):
    return (f'<div class="bv-sec"><b>{escape(str(num))}</b><span>{escape(title)}</span>'
            f"<i>{escape(sub)}</i></div>")


def pipeline_html(run):
    """Four-stage progress strip: error -> root cause -> fix -> proof."""
    states = ["idle"] * 4
    sub = ["waiting", "waiting", "waiting", "waiting"]
    if run:
        res, rag = run["patch"], run["rag"]
        verdict = res["verdict"]
        if verdict == "no_bug_found":
            states[0], sub[0] = "done", "no error: tests pass"
        else:
            states[0], sub[0] = "done", "tests failed"
            if rag is None:
                states[1], sub[1] = "skip", "switched off"
            elif rag.get("error"):
                states[1], sub[1] = "skip", "unavailable"
            else:
                states[1], sub[1] = "done", "explained"
            produced = any(a["status"] in ("passed", "failed", "error") for a in res["attempts"])
            states[2], sub[2] = ("done", "fix written") if produced else ("fail", "no fix produced")
            if verdict == "verified":
                states[3], sub[3] = "done", "VERIFIED"
            else:
                states[3], sub[3] = "fail", "NOT VERIFIED"
    names = ["ERROR FOUND", "ROOT CAUSE", "FIX WRITTEN", "PROVEN BY TESTS"]
    out = []
    for i in range(4):
        out.append(f'<div class="bv-node {states[i]}"><small>{i + 1}</small><div>{names[i]}</div>'
                   f'<small style="margin-top:4px">{escape(sub[i])}</small></div>')
        if i < 3:
            out.append('<div class="bv-link"></div>')
    return f'<div class="bv-pipe">{"".join(out)}</div>'


def root_cause_html(text):
    return f'<div class="bv-rc">{escape(str(text))}</div>'


def proof_html(data):
    total, ver, first = data["total"], data["verified"], data["verified_first_try"]
    recovered = ver - first
    sub = f"{first} were right on the first attempt"
    sub += f"; the retry loop recovered {recovered} more. " if recovered > 0 else ". "
    sub += "Every fix was checked by actually running tests."
    return (
        f'<div class="bv-proof">{ring_svg(ver / total, "#17784B")}<div>'
        f'<div class="bv-proof-big">Fixed and verified <b>{ver} of {total}</b> benchmark bugs '
        f"({ver / total * 100:.0f}%)</div>"
        f'<div class="bv-proof-sub">{escape(sub)}</div></div></div>'
    )


def how_cards_html():
    cards = [
        ("01", "EMBED + RETRIEVE", "Your bug is turned into a vector and matched against thousands of real historical fixes."),
        ("02", "CONFIDENCE GATE", "If the best match scores below the gate, BugVertex ignores it instead of grounding on bad evidence."),
        ("03", "GROUNDED ANSWER", "The model explains the root cause and fix, citing the examples it actually used."),
    ]
    items = "".join(
        f'<div class="bp-card" style="animation-delay:{i * 0.12:.2f}s"><div class="bp-card-num">{n}</div>'
        f'<div class="bp-card-title">{escape(t)}</div><div class="bp-card-text">{escape(x)}</div></div>'
        for i, (n, t, x) in enumerate(cards)
    )
    return f'<div class="bp-cards">{items}</div>'


def bug_grid_html(results):
    tiles = []
    for i, r in enumerate(results):
        ok = r["verdict"] == "verified"
        retry = f'<i>&#8635;{r["attempts_used"]}</i>' if r["attempts_used"] > 1 else ""
        tiles.append(
            f'<div class="bp-tile {"" if ok else "bad"}" style="animation-delay:{i * 0.04:.2f}s">'
            f'{retry}<b>{escape(r["id"].replace("bug_", ""))}</b>'
            f'<span>{escape(r["bug_type"])}</span><em>{"VERIFIED" if ok else "FAILED"}</em></div>'
        )
    return f'<div class="bp-grid">{"".join(tiles)}</div>'


def stamp_html(verdict):
    if verdict == "verified":
        return '<div class="bp-stamp">VERIFIED</div>'
    if verdict == "not_verified":
        return '<div class="bp-stamp bad">NOT VERIFIED</div>'
    return '<div class="bp-stamp neutral">NO BUG FOUND</div>'


# ---------------------------------------------------------
# Sidebar: configuration and loaded index
# ---------------------------------------------------------
with st.sidebar:
    st.header("BugVertex AI")
    st.caption("Bug investigation with sandbox-verified patches")

    st.subheader("Models")
    st.markdown(
        f"- **Embedding:** `{core.EMBEDDING_MODEL}`\n"
        f"- **Generation:** `{core.CHAT_MODEL}`\n"
        f"- **Rerank:** `{core.RERANK_MODEL}`"
    )

    st.subheader("Retrieval")
    try:
        path, ntotal, dim = core.index_info()
        st.markdown(
            f"- **Index:** `{os.path.relpath(path, core.BASE_DIR)}`\n"
            f"- **Vectors:** {ntotal:,} (dim {dim})\n"
            f"- **Top-K:** {core.TOP_K}\n"
            f"- **Confidence gate:** {core.CONFIDENCE_THRESHOLD}"
        )
    except Exception as e:
        st.error(f"Could not load index: {e}")

    st.divider()
    st.caption(
        "Extends the open-source, MIT-licensed RootCause project by Saksham Katna. "
        "Retrieval and the confidence gate are inherited; the benchmark, sandbox and "
        "patch verifier are new."
    )

st.html(hero_html())
st.html(path_ribbon_html())


# ---------------------------------------------------------
# Main flow: paste code + tests -> error -> root cause -> fix -> proof
# ---------------------------------------------------------
def _example_ids():
    if not BUGS_DIR.exists():
        return []
    return sorted(p.name for p in BUGS_DIR.iterdir() if p.is_dir())


def _load_example():
    choice = st.session_state.get("example_choice")
    if choice and choice != NONE_CHOICE:
        d = BUGS_DIR / choice
        st.session_state["patch_code"] = (d / "buggy.py").read_text(encoding="utf-8")
        st.session_state["patch_tests"] = (d / "test_bug.py").read_text(encoding="utf-8")
        st.session_state.pop("run", None)


def _run_pipeline(code, tests, want_rag):
    res = patcher.verify_patch(code, tests)
    rag = None
    if want_rag and res["verdict"] != "no_bug_found":
        query = ("Error found by the tests:\n" + res.get("baseline", "")[-700:]
                 + "\n\nCode:\n" + code[:1200])
        try:
            out = core.analyze_bug(query)
            try:
                parsed = json.loads(out["answer"])
            except (json.JSONDecodeError, TypeError):
                parsed = None
            rag = {"parsed": parsed, "raw": out["answer"], "score": out["top_score"],
                   "use_rag": out["use_rag"], "threshold": out["confidence_threshold"],
                   "retrieved": out["retrieved"], "error": None}
        except Exception as e:
            rag = {"error": str(e)[:200]}
    return {"patch": res, "rag": rag, "baseline": res.get("baseline", "")}


def render_run(run):
    res, rag, verdict = run["patch"], run["rag"], run["patch"]["verdict"]
    st.html(pipeline_html(run))

    st.html(section_label_html("1", "THE ERROR", "what your tests found wrong"))
    if verdict == "no_bug_found":
        st.success("Your tests already pass on this code, so there is no error to fix. "
                   "Try tests that fail, or load an example bug.")
        return
    st.code(run["baseline"][-1800:] or "(no output captured)", language="text")
    st.caption("This is the failure the AI has to fix: your tests failed on the original code.")

    st.html(section_label_html("2", "ROOT CAUSE", "why it happens, backed by similar past bugs"))
    if rag is None:
        st.caption("Skipped: the root-cause explanation was switched off.")
    elif rag.get("error"):
        st.caption(f"The root-cause explanation was unavailable: {rag['error']}")
    else:
        parsed = rag["parsed"]
        text = parsed.get("root_cause") if isinstance(parsed, dict) else None
        st.html(root_cause_html(text or rag["raw"]))
        if rag["use_rag"]:
            st.caption(f"Grounded on similar past bug fixes (best match {rag['score']:.2f}, "
                       f"above the {rag['threshold']} confidence gate).")
        else:
            st.caption(f"No close match in past bugs (best {rag['score']:.2f}, below the "
                       f"{rag['threshold']} gate), so this explanation comes from reasoning alone.")
        if rag["retrieved"]:
            with st.expander("Similar past bug fixes that were found"):
                st.dataframe(
                    [{"score": round(r["score"], 3), "bug_type": r["bug_type"],
                      "issue": r["issue"], "fix": r["fix"]} for r in rag["retrieved"]],
                    width="stretch", hide_index=True,
                )

    st.html(section_label_html("3", "THE FIX", "what the AI changed"))
    if res["diff"]:
        st.html(render_diff_html(res["diff"]))
        st.markdown("#### Patched code")
        st.code(res["patch"], language="python")
    else:
        st.caption("The AI could not produce a fix that passes your tests, so no patch is shown.")

    st.html(section_label_html("4", "PROOF", "the fix is run against your tests in a sandbox"))
    st.html(stamp_html(verdict))
    st.html(fx.terminal_html(res))
    if res["attempts"]:
        with st.expander("Attempt details"):
            st.dataframe(
                [{"attempt": a["attempt"], "result": a["status"], "detail": a.get("detail", "")}
                 for a in res["attempts"]],
                width="stretch", hide_index=True,
            )
    st.html(note_html(
        "NOTE",
        "Verified means the patch passes your tests in the sandbox. It does not prove the code "
        "is correct in every situation, so review a patch before using it.",
    ))


st.html(section_label_html("▶", "TRY IT NOW", "no code handy? load an example bug first"))
st.selectbox("New here? Load an example bug", [NONE_CHOICE] + _example_ids(),
             key="example_choice", on_change=_load_example)

col_code, col_tests = st.columns(2)
code = col_code.text_area("1. Paste your buggy code (saved as buggy.py)", height=250, key="patch_code",
                          placeholder="def get_user_name(user):\n    return user.get(\"name\").strip()")
tests = col_tests.text_area("2. Add tests that describe correct behavior (they must import from buggy)",
                            height=250, key="patch_tests",
                            placeholder="from buggy import get_user_name\n\ndef test_none_user():\n    assert get_user_name(None) == \"\"")
want_rag = st.checkbox("Also explain the root cause using similar past bugs", value=True, key="want_rag")
st.html(note_html(
    "WARNING",
    "Code and tests run on this computer in a temporary folder with a time limit and without your "
    "API keys. This is not a security boundary, so only run code you trust.",
))

if st.button("3. Find the bug and fix it", type="primary"):
    if not code.strip() or not tests.strip():
        st.warning("Please paste your buggy code and your tests first (or load an example above).")
    else:
        with st.spinner("Running your tests, asking the model for a fix, and verifying it..."):
            try:
                st.session_state["run"] = _run_pipeline(code, tests, want_rag)
            except Exception as e:
                st.error(f"Something went wrong: {e}")

current_run = st.session_state.get("run")
if current_run:
    render_run(current_run)
else:
    st.html(pipeline_html(None))
    st.caption("Your results will appear here: the error found, the root cause, the fix, and the proof.")

st.divider()
tab_how, tab_proof, tab_search, tab_routing = st.tabs(
    ["How it works", "Proof", "Search past bugs", "Routing"]
)

# ---------------------------------------------------------
# Sheet 1: How it works
# ---------------------------------------------------------
with tab_how:
    sheet_head(1, "How it works", "from error to verified fix")
    last = (current_run or {}).get("patch", {}).get("verdict")
    st.html(flow_svg(last))
    st.markdown("**Where the root-cause evidence comes from**")
    st.html(how_cards_html())
    st.markdown(
        "**Inherited vs. built.** The retrieval pipeline, confidence gate and original dashboard come "
        "from the open-source RootCause project (MIT). The benchmark, sandbox runner, patch verifier, "
        "retry loop and this interface were built for BugVertex AI."
    )
    st.html(note_html(
        "LIMITATIONS",
        "The sandbox is a separate process with a time limit, not a security boundary. The AI sees "
        "your tests, so verified means the patch passes them, not that it is correct in every case.",
    ))

# ---------------------------------------------------------
# Sheet 2: Proof (benchmark)
# ---------------------------------------------------------
with tab_proof:
    sheet_head(2, "Proof", "tested on 20 hand-written bugs")
    data = load_eval()
    if not data:
        st.info("No results yet. Run:  python scripts\\run_patch_eval.py")
    else:
        st.html(proof_html(data))
        st.html(fx.radar_panel_html(data))
        st.markdown("**Every benchmark bug** (green = verified, red = not verified, arrow = needed a retry)")
        st.html(bug_grid_html(data["results"]))
        st.caption(f"Model: {data['model']}  |  last run: {data['date']}")
        with st.expander("Full results table"):
            st.dataframe(
                [{"bug": r["id"], "type": r["bug_type"], "verdict": r["verdict"],
                  "attempts": r["attempts_used"]} for r in data["results"]],
                width="stretch", hide_index=True,
            )
        if "bug_018" in [r["id"] for r in data["results"] if r["verdict"] != "verified"]:
            with st.expander("The one miss: why did bug_018 fail?"):
                st.write(
                    "The bug is a missing timeout. The model kept writing `timeout=None`, "
                    "which looks like a timeout but means no timeout. The test checks that a "
                    "real timeout value is passed, so it rejected the patch every time. "
                    "This is the reason patches are verified by running tests instead of "
                    "being trusted."
                )
        st.html(note_html(
            "LIMITATIONS",
            "The benchmark is small, hand-written and simple, the model sees the tests, and "
            "results vary slightly between runs. These numbers do not show performance on "
            "real-world codebases.",
        ))

# ---------------------------------------------------------
# Sheet 3: Search past bugs (inherited pipeline)
# ---------------------------------------------------------
INV_EXAMPLES = [
    "(none)",
    "TypeError: 'NoneType' object has no attribute 'get' when a record is missing",
    "My loop skips the last element because the range upper bound is wrong",
    "Calling requests without a timeout and the worker hangs forever on a slow endpoint",
    "User input is interpolated directly into an SQL string, enabling injection",
]


def _load_query():
    choice = st.session_state.get("inv_example")
    if choice and choice != "(none)":
        st.session_state["inv_query"] = choice


with tab_search:
    sheet_head(3, "Search past bugs", "retrieval + confidence gate")
    st.write(
        "Describe a bug or paste a traceback. BugVertex finds similar historical bug fixes, "
        "gates on retrieval confidence, and asks the LLM for a grounded root cause and fix."
    )
    st.selectbox("Try an example bug", INV_EXAMPLES, key="inv_example", on_change=_load_query)
    query = st.text_area(
        "Bug description",
        height=140,
        key="inv_query",
        placeholder="e.g. TypeError: 'NoneType' object has no attribute 'get' when a user "
        "record is missing from the cache",
    )

    if st.button("Analyze", type="primary") and query.strip():
        with st.spinner("Embedding, retrieving, and generating..."):
            try:
                result = core.analyze_bug(query)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

        used = result["use_rag"]
        st.html(note_html(
            "NOTE",
            f"Top retrieval score {result['top_score']:.3f} is "
            f"{'above' if used else 'below'} the {result['confidence_threshold']} gate: "
            f"{'answer grounded on retrieved examples.' if used else 'answering from reasoning only.'}",
        ))
        st.markdown("#### Answer")
        try:
            st.json(json.loads(result["answer"]))
        except (json.JSONDecodeError, TypeError):
            st.code(result["answer"])
        st.markdown("#### Retrieved candidates")
        cand_rows = [{"score": round(r["score"], 3), "bug_type": r["bug_type"],
                      "issue": r["issue"], "fix": r["fix"]} for r in result["retrieved"]]
        if cand_rows:
            st.dataframe(cand_rows, width="stretch", hide_index=True)
        else:
            st.info("No candidates retrieved.")

# ---------------------------------------------------------
# Sheet 4: Routing (inherited)
# ---------------------------------------------------------
PROBE_QUERIES = [
    "TypeError: 'NoneType' object has no attribute 'get' when a record is missing",
    "AttributeError because a dict lookup returned None and I called .strip() on it",
    "TypeError: unsupported operand type(s) for +: 'int' and 'str' from parsed CSV",
    "My loop skips the last element because the range upper bound is wrong",
    "The conditional branch falls through when the coupon is empty, applying the discount twice",
    "Variable defined inside the if-block is referenced outside it and raises NameError",
    "A bare except swallows the real error and the program continues with corrupted state",
    "Calling requests without a timeout and the worker hangs forever on a slow endpoint",
    "Two threads increment the same counter without a lock and the total is wrong",
    "os.path.exists passes but the file is deleted before open() runs",
    "A cache dict grows unbounded because entries are never evicted",
    "User input is interpolated directly into an SQL string, enabling injection",
]

with tab_routing:
    sheet_head(4, "Routing", "confidence gate " + str(core.CONFIDENCE_THRESHOLD))
    st.write(
        f"Every call is routed by the confidence gate. If the top retrieval score is at or "
        f"above **{core.CONFIDENCE_THRESHOLD}**, the answer is grounded on retrieved "
        f"examples; below it, the call is diverted to the LLM and answered from reasoning "
        f"alone. This runs a fixed set of probe queries through the currently loaded index "
        f"(retrieval only, no generation). It is a routing distribution, not an accuracy score."
    )

    if st.button("Run routing analysis"):
        rag = 0
        route_rows = []
        progress = st.progress(0.0, text="Routing probe queries...")
        for i, q in enumerate(PROBE_QUERIES):
            try:
                cands = core.retrieve(q)
            except Exception as e:
                st.error(f"Routing failed: {e}")
                st.stop()
            top = cands[0]["score"] if cands else 0.0
            is_rag = top >= core.CONFIDENCE_THRESHOLD
            rag += is_rag
            route_rows.append({
                "query": q[:55] + ("..." if len(q) > 55 else ""),
                "top_score": round(top, 3),
                "routed_to": "RAG retrieval" if is_rag else "LLM (diverted)",
            })
            progress.progress((i + 1) / len(PROBE_QUERIES))
        progress.empty()

        total = len(PROBE_QUERIES)
        diverted = total - rag
        c1, c2 = st.columns(2)
        c1.metric("RAG-based retrieval", f"{rag}/{total}", f"{rag / total * 100:.0f}%")
        c2.metric("Diverted to LLM", f"{diverted}/{total}", f"{diverted / total * 100:.0f}%")
        st.bar_chart(
            {"RAG-based retrieval": [rag], "Diverted to LLM": [diverted]},
            color=["#2e7d32", "#c62828"],
        )
        st.dataframe(route_rows, width="stretch", hide_index=True)
    else:
        st.caption("Click to route the probe set against the loaded index (embeddings only).")