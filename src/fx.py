"""
Visual effects for the BugVertex dashboard: status ticker, benchmark radar, terminal replay.
Pure HTML/CSS/SVG (no JavaScript). The radar sweep is decorative; its blips are the
real benchmark results.
"""
import math
from html import escape

FX_CSS = """
<style>
@keyframes fx-marquee { from { transform: translateX(0); } to { transform: translateX(-100%); } }
@keyframes fx-spin { to { transform: rotate(360deg); } }
@keyframes fx-blip { 0% { opacity: 1; } 55% { opacity: .30; } 100% { opacity: .30; } }
@keyframes fx-ping { 0% { transform: scale(1); opacity: .9; } 100% { transform: scale(3); opacity: 0; } }
@keyframes fx-type { from { width: 0; } to { width: 100%; } }
@keyframes fx-cur { 50% { opacity: 0; } }
@keyframes fx-flicker { 0%, 100% { opacity: 1; } 50% { opacity: .55; } }

.fx-ticker { overflow: hidden; white-space: nowrap; border: 1px solid var(--bp-major); margin: 0 0 12px 0;
  background: rgba(255,255,255,0.92); font-family: ui-monospace, Consolas, monospace; font-size: .74rem;
  letter-spacing: .12em; color: var(--bp-dim); padding: 6px 0; }
.fx-ticker-track { display: inline-block; padding-left: 100%; animation: fx-marquee 34s linear infinite; }
.fx-ticker b { color: var(--bp-cyan); font-weight: 600; }
.fx-ticker i { color: var(--bp-ok); font-style: normal; animation: fx-flicker 2s ease-in-out infinite; }
.fx-ticker u { color: var(--bp-bad); text-decoration: none; }
.fx-ticker span { margin-right: 46px; }

.fx-panel { display: grid; grid-template-columns: 260px 1fr; gap: 22px; align-items: center; position: relative;
  border: 1px solid var(--bp-major); margin: 0 0 18px 0; padding: 14px 20px;
  background: linear-gradient(135deg, rgba(236,243,252,0.94), rgba(255,255,255,0.92));
  font-family: ui-monospace, Consolas, monospace; }
.fx-panel::before { content: ""; position: absolute; top: -2px; left: -2px; width: 12px; height: 12px;
  border: 2px solid var(--bp-cyan); border-right: none; border-bottom: none; }
.fx-panel::after { content: ""; position: absolute; bottom: -2px; right: -2px; width: 12px; height: 12px;
  border: 2px solid var(--bp-cyan); border-left: none; border-top: none; }
.fx-radar { width: 240px; height: 240px; }
.fx-sweep { transform-origin: 120px 120px; transform-box: view-box; animation: fx-spin 4s linear infinite; }
.fx-blip { animation: fx-blip 4s linear infinite; }
.fx-ring { transform-box: fill-box; transform-origin: center; animation: fx-ping 2.2s ease-out infinite; }
.fx-title { color: var(--bp-cyan); letter-spacing: .2em; font-size: .78rem; margin-bottom: 6px; }
.fx-big { font-size: 1.5rem; color: #0F2A4A; letter-spacing: .06em; margin-bottom: 10px; }
.fx-legend { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; font-size: .82rem; color: var(--bp-ink); }
.fx-legend span { color: var(--bp-dim); letter-spacing: .1em; font-size: .7rem; }
.fx-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 8px; }
.fx-fine { color: var(--bp-dim); font-size: .7rem; margin-top: 12px; line-height: 1.5; }

.fx-term { background: #0F1B2D; border: 1px solid #2A3B57; border-radius: 6px; margin: 10px 0 6px 0; overflow: hidden;
  font-family: ui-monospace, Consolas, monospace; font-size: .84rem; }
.fx-term-bar { display: flex; align-items: center; gap: 6px; padding: 7px 12px; background: #19293F;
  border-bottom: 1px solid #2A3B57; color: #9FB4D3; font-size: .68rem; letter-spacing: .14em; }
.fx-term-bar em { width: 9px; height: 9px; border-radius: 50%; display: inline-block; font-style: normal; }
.fx-term-body { padding: 12px 14px; }
.fx-line { display: block; overflow: hidden; white-space: nowrap; width: 0; color: #DCE8F7; line-height: 1.7;
  animation: fx-type .9s steps(60) forwards; }
.fx-term .fx-ok { color: #6EE7A8; }
.fx-term .fx-bad { color: #FF8F8F; }
.fx-term .fx-dim { color: #9FB4D3; }
.fx-end::after { content: "\\2588"; color: #8CC8FF; margin-left: 4px; animation: fx-cur 1s steps(2) infinite; }
@media (max-width: 900px) { .fx-panel { grid-template-columns: 1fr; justify-items: center; } }
@media (prefers-reduced-motion: reduce) { .fx-line { width: 100% !important; } }
</style>
"""


def ticker_html(data):
    if data:
        items = [
            "<i>&#9679;</i> <b>SANDBOX ONLINE</b>",
            f"<b>{data['verified']}/{data['total']}</b> PATCHES VERIFIED",
            f"<b>{data['verified_first_try']}/{data['total']}</b> FIXED ON FIRST TRY",
            f"MODEL <b>{escape(data['model'])}</b>",
        ]
        bad = [r["id"] for r in data["results"] if r["verdict"] != "verified"]
        for b in bad:
            items.append(f"<u>&#9650; {escape(b)} NOT VERIFIED</u>")
        items.append("EVERY PATCH IS CHECKED BY RUNNING TESTS")
    else:
        items = ["<i>&#9679;</i> <b>SANDBOX ONLINE</b>", "NO BENCHMARK RESULTS YET"]
    body = "".join(f"<span>{x}</span>" for x in items)
    return f'<div class="fx-ticker"><div class="fx-ticker-track">{body}{body}</div></div>'


def radar_svg(results):
    cx = cy = 120
    parts = [
        '<svg class="fx-radar" viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">',
        '<circle cx="120" cy="120" r="115" fill="#0F2A4A" stroke="#1F5FBF" stroke-width="1.5"/>',
    ]
    for r in (28, 57, 86):
        parts.append(f'<circle cx="120" cy="120" r="{r}" fill="none" stroke="rgba(31,95,191,0.22)" '
                     'stroke-width="1" stroke-dasharray="3 4"/>')
    parts.append('<line x1="120" y1="5" x2="120" y2="235" stroke="rgba(31,95,191,0.2)"/>')
    parts.append('<line x1="5" y1="120" x2="235" y2="120" stroke="rgba(31,95,191,0.2)"/>')
    parts.append('<g class="fx-sweep">'
                 '<path d="M120,120 L120,5 A115,115 0 0 0 38.7,38.7 Z" fill="rgba(31,95,191,0.22)"/>'
                 '<path d="M120,120 L120,5 A115,115 0 0 0 78.8,12.8 Z" fill="rgba(31,95,191,0.30)"/>'
                 '<line x1="120" y1="120" x2="120" y2="5" stroke="#1F5FBF" stroke-width="2"/></g>')
    n = max(len(results), 1)
    for i, r in enumerate(results):
        theta = (i * 360.0 / n) + (i % 3) * 6
        radius = 34 + (sum(ord(c) for c in r["bug_type"]) % 72)
        x = cx + radius * math.sin(math.radians(theta))
        y = cy - radius * math.cos(math.radians(theta))
        ok = r["verdict"] == "verified"
        color = "#17784B" if ok else "#C03030"
        delay = (theta % 360) / 360.0 * 4.0
        if not ok:
            parts.append(f'<circle class="fx-ring" cx="{x:.1f}" cy="{y:.1f}" r="4" fill="none" '
                         f'stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<circle class="fx-blip" style="animation-delay:{delay:.2f}s" cx="{x:.1f}" cy="{y:.1f}" '
                     f'r="{3.6 if ok else 5}" fill="{color}"/>')
    parts.append('<circle cx="120" cy="120" r="3" fill="#1F5FBF"/>')
    parts.append("</svg>")
    return "".join(parts)


def radar_panel_html(data):
    if not data:
        return ('<div class="fx-panel"><div class="fx-radar"></div><div><div class="fx-title">BENCHMARK RADAR</div>'
                '<div class="fx-fine">No results yet. Run scripts\\run_patch_eval.py to light up the radar.</div></div></div>')
    results = data["results"]
    ok = sum(r["verdict"] == "verified" for r in results)
    bad = len(results) - ok
    retried = sum(r["attempts_used"] > 1 for r in results)
    types = len({r["bug_type"] for r in results})
    return (
        '<div class="fx-panel">' + radar_svg(results) +
        '<div><div class="fx-title">BENCHMARK RADAR</div>'
        f'<div class="fx-big">{ok} OF {len(results)} BUGS CLEARED</div>'
        '<div class="fx-legend">'
        '<span>VERIFIED</span><div><i class="fx-dot" style="background:#17784B"></i>'
        f'{ok} patches passed the tests</div>'
        '<span>FAILED</span><div><i class="fx-dot" style="background:#FF6B6B"></i>'
        f'{bad} not verified</div>'
        f'<span>RETRIES</span><div>{retried} bug(s) needed more than one attempt</div>'
        f'<span>COVERAGE</span><div>{types} different bug types</div></div>'
        '<div class="fx-fine">Each blip is one real benchmark bug from the latest evaluation run. '
        'The rotating sweep is decorative.</div></div></div>'
    )


def terminal_html(res):
    """Replay a patch run as a typed console log, using the real attempt results."""
    lines = []  # (css class, text)
    verdict = res["verdict"]
    if verdict == "no_bug_found":
        lines.append(("", '$ sandbox: run tests on original code ........ <span class="fx-ok">PASS</span>'))
        lines.append(("fx-dim", "> nothing to fix"))
    else:
        lines.append(("", '$ sandbox: run tests on original code ........ <span class="fx-bad">FAIL</span>'))
        total = len(res["attempts"])
        for a in res["attempts"]:
            n, st = a["attempt"], a["status"]
            if st == "llm_error":
                lines.append(("", f'$ llm: propose fix (attempt {n}) ............ <span class="fx-bad">MODEL ERROR</span>'))
                continue
            if st == "no_code":
                lines.append(("", f'$ llm: propose fix (attempt {n}) ............ <span class="fx-bad">NO CODE IN REPLY</span>'))
                continue
            lines.append(("", f'$ llm: propose fix (attempt {n}) ............ <span class="fx-ok">RECEIVED</span>'))
            tag = '<span class="fx-ok">PASS</span>' if st == "passed" else '<span class="fx-bad">FAIL</span>'
            lines.append(("", f"$ sandbox: run tests on the patch ......... {tag}"))
            if st != "passed" and n < total:
                lines.append(("fx-dim", "> still failing: retrying with feedback"))
        if verdict == "verified":
            lines.append(("fx-ok", "> VERDICT: PATCH VERIFIED"))
        else:
            lines.append(("fx-bad", "> VERDICT: NOT VERIFIED"))
    out = []
    for i, (cls, text) in enumerate(lines):
        last = " fx-end" if i == len(lines) - 1 else ""
        out.append(f'<span class="fx-line {cls}{last}" style="animation-delay:{i * 0.85:.2f}s">{text}</span>')
    return ('<div class="fx-term"><div class="fx-term-bar"><em style="background:#FF6B6B"></em>'
            '<em style="background:#FFC857"></em><em style="background:#5CE0A0"></em>'
            '<span style="margin-left:10px">BUGVERTEX SESSION LOG</span></div>'
            f'<div class="fx-term-body">{"".join(out)}</div></div>')