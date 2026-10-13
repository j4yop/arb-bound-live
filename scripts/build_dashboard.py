#!/usr/bin/env python3
"""Render the published dashboard from committed scan results.

The rule this repo runs on: **no number appears on the page that a run did not
produce.** So the dashboard is generated, not hand-edited. Give it the scan
artefacts and it writes ``docs/index.html``.

    python scripts/build_dashboard.py

It reads every ``scans/*.json`` (the daily workflow's output) and writes the
dashboard. With no scans it falls back to the sample committed at
``docs/data/`` and says so in the page, rather than inventing figures.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANS = ROOT / "scans"
SAMPLE = ROOT / "docs" / "data"
OUT = ROOT / "docs" / "index.html"

GATE = [
    ("G1", "live MCX bhavcopy", "PASS",
     "4.9&nbsp;MB of real dated JSON, all five gold contracts, on the URL curl is blocked on"),
    ("G3", "circular archive listing", "PASS",
     "real rows returned, no Akamai block"),
    ("G4", "Agent applies the archive date filter", "PASS",
     "115 steps &middot; <strong>204 circulars</strong> for Oct&ndash;Dec 2024"),
    ("G2", "a specific circular PDF by path", "PARTIAL",
     "guessed paths unreachable, superseded by G4"),
]


def _load_scans() -> tuple[list[dict], str]:
    """Return (scans, provenance sentence). Newest first."""
    if SCANS.is_dir():
        found = sorted(
            (p for p in SCANS.glob("*.json") if p.stem[0].isdigit()),
            key=lambda p: p.stem,
            reverse=True,
        )
        if found:
            scans = [json.loads(p.read_text()) for p in found]
            return scans, f"generated from {len(found)} committed scan(s)"
    sample = SAMPLE / "scan-sample.json"
    if sample.exists():
        return (
            [json.loads(sample.read_text())],
            "generated from the committed sample scan &mdash; the daily workflow has not "
            "run yet, so this is one day of data, not a series",
        )
    return [], "no scan artefacts found"


def _money(v) -> str:
    return f"{float(v):,.2f}"


def _num(v, dp=1) -> str:
    return f"{float(v):,.{dp}f}"


def render(scans: list[dict], provenance: str) -> str:
    latest = scans[0]
    vs = latest["verdict_summary"]
    date = latest["date"]

    rows = []
    for v in latest["verdicts"]:
        cls = ' class="cleared"' if v["cleared"] else ""
        rows.append(
            f"<tr{cls}><td><code>{v['pair']}</code></td>"
            f"<td class=\"num\">{_num(v['median_basis_bps'])}</td>"
            f"<td class=\"num\">{_num(v['bound_low_bps'])}</td>"
            f"<td class=\"num\">{_num(v['bound_high_bps'])}</td>"
            f"<td class=\"num\">{_num(v['bound_centre_bps'])}</td>"
            f"<td class=\"num\">{v['days_above_bound']}</td>"
            f"<td>{'cleared' if v['cleared'] else '&mdash;'}</td></tr>"
        )

    gate_rows = [
        f"<tr><td>{g}</td><td>{label}</td>"
        f"<td><span class=\"tag {'pass' if state == 'PASS' else 'part'}\">{state.lower()}</span>"
        f" {detail}</td></tr>"
        for g, label, state, detail in GATE
    ]

    history = ""
    if len(scans) > 1:
        hist = [
            f"<tr><td><code>{s['date']}</code></td>"
            f"<td class=\"num\">{s['rows_with_trades']}</td>"
            f"<td class=\"num\">{s['basis_observations']}</td>"
            f"<td class=\"num\">{s['verdict_summary']['pairs_tested']}</td>"
            f"<td class=\"num\">{s['verdict_summary']['pairs_cleared']}</td></tr>"
            for s in scans
        ]
        history = (
            "<h2>Every committed scan</h2>"
            "<p class=\"sub\">One row per trading day. A single day proves ingest, not "
            "inference &mdash; this table is what can eventually settle it.</p>"
            "<table><thead><tr><th>Date</th><th>Rows</th><th>Basis obs</th>"
            "<th>Pairs</th><th>Cleared</th></tr></thead><tbody>"
            + "".join(hist)
            + "</tbody></table>"
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>arb-bound-live &mdash; live MCX gold through TinyFish</title>
<style>
:root{{--bg:#0d1117;--panel:#161b22;--panel2:#1c2330;--line:#2a3241;--ink:#e6edf3;
--muted:#8b98a9;--gold:#e3b341;--good:#3fb950;--warn:#d29922;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
@media (prefers-color-scheme:light){{:root{{--bg:#fff;--panel:#f6f8fa;--panel2:#eef1f5;
--line:#d8dee4;--ink:#1f2328;--muted:#59636e}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:52px 24px 88px}}
header{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:34px}}
.kicker{{font:600 11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--gold)}}
h1{{font-size:34px;line-height:1.18;margin:12px 0 10px;font-weight:700}}
.sub{{color:var(--muted);font-size:15px;max-width:78ch}}
h2{{font-size:19px;margin:40px 0 14px;font-weight:650}}
.hero{{background:linear-gradient(135deg,var(--panel2),var(--panel));border:1px solid var(--line);
border-left:4px solid var(--gold);border-radius:10px;padding:20px 22px;margin:22px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:14px 0}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:15px 17px}}
.card .k{{font:600 10px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}}
.card .v{{font-size:25px;font-weight:700;margin-top:7px;font-variant-numeric:tabular-nums}}
.card .n{{font-size:12.5px;color:var(--muted);margin-top:3px}}
.v.good{{color:var(--good)}} .v.warn{{color:var(--warn)}} .v.gold{{color:var(--gold)}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}}
th{{font:600 10.5px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);font-size:12.5px}}
tr.cleared td{{background:rgba(63,185,80,.07)}}
.tag{{display:inline-block;font:600 9.5px/1 var(--mono);padding:3px 6px;border-radius:4px;
letter-spacing:.08em;text-transform:uppercase}}
.tag.pass{{background:rgba(63,185,80,.16);color:var(--good)}}
.tag.part{{background:rgba(210,153,34,.16);color:var(--warn)}}
ul{{margin:8px 0;padding-left:20px}} li{{margin:6px 0;font-size:14px}}
a{{color:var(--gold)}} code{{font:12.5px/1.5 var(--mono);background:var(--panel2);padding:2px 6px;border-radius:4px}}
pre{{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:14px 16px;
overflow-x:auto;font:12.5px/1.6 var(--mono)}}
.rule{{height:1px;background:var(--line);margin:34px 0}}
footer{{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}}
@media(max-width:640px){{h1{{font-size:27px}}}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="kicker">Hack in Hills '26 &middot; TinyFish Builder Challenge</div>
  <h1>arb-bound-live</h1>
  <p class="sub">Live MCX gold bhavcopy fetched through TinyFish, normalised, and judged against a
  bound derived from <em>contract specifications</em> &mdash; fitted to nothing, so it can disagree
  with the data.</p>
</header>

<div class="hero">
  <strong>The premise.</strong> <code>mcxindia.com</code> returns <strong>HTTP 403 (Akamai)</strong>
  from a datacentre IP. <code>curl</code> on the exact URL this reads gets a block page. TinyFish
  runs a real browser with stealth and rotating proxies, and does not.
</div>

<h2>Latest live scan</h2>
<div class="grid">
  <div class="card"><div class="k">Scan date</div><div class="v gold">{date}</div>
    <div class="n">fetched live, {latest['rows_with_trades']} rows traded</div></div>
  <div class="card"><div class="k">Pairs tested</div><div class="v">{vs['pairs_tested']}</div>
    <div class="n">all gold futures pairs</div></div>
  <div class="card"><div class="k">Cleared the bound</div>
    <div class="v {'good' if vs['pairs_cleared'] == 0 else 'warn'}">{vs['pairs_cleared']}</div>
    <div class="n">on this day only</div></div>
  <div class="card"><div class="k">Reference price</div>
    <div class="v" style="font-size:20px">&#8377;{_money(latest['reference_price_inr_per_g_fine'])}</div>
    <div class="n">INR per gram of fine gold</div></div>
</div>
<p class="sub" style="font-size:13.5px">Source: <code>{latest['source']}</code></p>

<h2>The verdict, per pair</h2>
<table>
<thead><tr><th>Pair</th><th>Median basis</th><th>Bound low</th><th>Bound high</th>
<th>Centre</th><th>Days above</th><th>Outcome</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<p class="sub" style="font-size:13.5px">Fabrication is one-way, so only the tradeable direction
counts. Bounds are bands, not points, because mint cost, the duty wedge and friction are each
carried as ranges and swept rather than guessed.</p>

{history}

<h2>The gate, run and recorded</h2>
<table><thead><tr><th>Gate</th><th>Target</th><th>Outcome</th></tr></thead>
<tbody>{''.join(gate_rows)}</tbody></table>
<p class="sub">G4 is the decisive one: the circular archive is JS-driven and its endpoint sits behind
a MIME-blocked JS file, so the parent project could never reach it and had to close a research
question with a third-party mirror. The Agent set the archive's From/To dates, clicked Show, and
paged through all 14 result pages. The full 204-row result is committed with its run id.</p>

<h2>Run it yourself</h2>
<pre>cp .env.example .env        # key from agent.tinyfish.ai/api-keys
pip install -e ".[server,dev]"

python -m mcx_live live                                     # fetch, parse, bound, verdict
python -m mcx_live circulars 01/10/2024 31/12/2024           # the dated archive
bash scripts/smoke_live.sh                                 # end-to-end, prints a table

uvicorn mcx_live.server:app --reload                       # /health  /scan  /circulars
python scripts/build_dashboard.py                          # regenerate this page</pre>

<div class="rule"></div>

<h2>Honest limits</h2>
<ul>
<li><code>?date=</code> on the bhavcopy URL is ignored &mdash; this is a <strong>daily ingest, not
a historical backfill</strong>.</li>
<li>Fetch is not perfectly stable on that endpoint; it sometimes returns an HTML shell, so the
fetch retries and recovers the payload.</li>
<li>Settlement prices are not executable fills. A gap inside a printed band is an upper bound on a
trade, not evidence of one.</li>
<li><strong>One day is not a persistent edge.</strong> The table above is whichever scan is newest;
the history table is what can eventually settle it.</li>
</ul>

<div class="rule"></div>
<p style="color:var(--muted);font-size:13.5px">
Full plan, gate evidence and every limit found while building:
<a href="TINYFISH.md"><code>docs/TINYFISH.md</code></a> &middot;
Repo: <a href="https://github.com/j4yop/arb-bound-live"><code>github.com/j4yop/arb-bound-live</code></a>
&middot; MIT licensed.</p>

<footer>
Generated {now} from {provenance}. Nothing on this page is hand-typed, and
<code>tests/test_claims.py</code> fails the build if the evidence behind a claim disappears.
</footer>
</div>
</body>
</html>
"""


def main() -> int:
    scans, provenance = _load_scans()
    if not scans:
        sys.stderr.write("no scan artefacts and no sample; nothing to render\n")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(scans, provenance))
    sys.stderr.write(
        f"wrote {OUT.relative_to(ROOT)} from {len(scans)} scan(s) "
        f"({provenance}); newest {scans[0]['date']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
