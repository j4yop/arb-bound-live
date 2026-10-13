# arb-bound-live

**Live MCX gold data through [TinyFish](https://tinyfish.ai), judged against a structural
arbitrage bound.**

*Hack in Hills '26 · TinyFish Builder Challenge*

**Live:** <https://j4yop.github.io/arb-bound-live/> &nbsp;·&nbsp; **API:** `/health` `/scan` `/circulars`

---

## The question

MCX lists one metal as four physically-delivered futures: `GOLDM`, `GOLDGUINEA`, `GOLDPETAL`,
`GOLDTEN`. A trader sees four prices and a spread, and concludes the spread is available. Three
things make that wrong:

1. **Delivery is compulsory.** You cannot short into compulsory delivery with a laptop.
2. **Fabrication cost is fixed *per bar*.** So the per-gram overhead scales **inversely with bar
   size**. A 1 g bar and an 8 g bar do not carry the same premium per gram — and that difference
   is a *cost*, not a dislocation.
3. **The contracts are not the same thing.** `GOLDM` is 995 purity settling `Rate × 999/995`, and
   quotes duty-inclusive Ex-Ahmedabad. The rest are 999 retail bars quoting Ex-Mumbai.

The observable gap is therefore a mixture of a contractual wedge, a physical conversion cost, and
possibly a real dislocation. **The prices alone cannot separate them.**

## The bound

The tradeable band is **structural, and fitted to nothing**:

| Component | Source | Type |
|---|---|---|
| Fabrication overhead difference | `mint_cost_per_bar × (1/small_grams − 1/large_grams)` | Assumption, ₹20–60/bar, swept |
| Purity / duty quote-basis wedge | MCX contract specifications | Sourced mechanism, 0–400 bps range |
| Statutory friction + slippage | brokerage, GST/CTT, stamp duty, exchange fees | Sourced, 4–35 bps per leg |

Fitting nothing to the price series is the whole point: **a bound fitted to the data cannot
disagree with the data.** On top of that, fabrication is *one-way* — small bars are always dearer
per gram — so only one direction of each gap is tradeable. Taking an absolute value would treat
both directions as exploitable and manufacture hundreds of false breaches.

## Why TinyFish is the point of this repo

The data is free and public, but **`mcxindia.com` returns HTTP 403 (Akamai Access Denied) from a
datacentre IP.** `curl` on the same URL gets a block page; the project's own machine could never
fetch MCX data at all, and one research question had to be closed via a third-party mirror because
the exchange's circular archive was unreachable.

TinyFish's Fetch and Agent APIs run a *real browser* with built-in stealth and rotating proxies,
and they get through. Verified 2026-10-13:

| Gate | Target | Result |
|---|---|---|
| G1 | live bhavcopy | **PASS** — 4.9 MB of real dated JSON, all gold contracts, on the exact URL `curl` is blocked on |
| G3 | circular archive listing | **PASS** — real rows, no block |
| G4 | **Agent** applies the archive date filter | **PASS, decisive** — 115 steps, **204 circulars** for Oct–Dec 2024 across all 14 pages |

The G4 result is the archive this project's parent could not reach *at all*, and it settled an open
research question that had been closed with a mirror instead. See [`docs/TINYFISH.md`](docs/TINYFISH.md).

**One honest limit:** `?date=` on the bhavcopy URL is ignored, so this is a **daily ingest, not a
historical backfill**. Fetch is also not perfectly stable on that endpoint — it sometimes returns an
HTML shell — so `fetch_bhavcopy` retries and recovers the payload.

## Run it

```bash
cp .env.example .env      # then paste your key from agent.tinyfish.ai/api-keys
pip install -e ".[server,dev]"

python -m mcx_live wallet                                  # balance + rates
python -m mcx_live live                                     # fetch, parse, bound, verdict
python -m mcx_live circulars 01/10/2024 31/12/2024          # the dated archive

uvicorn mcx_live.server:app --reload                       # /health  /scan  /circulars
bash scripts/smoke_live.sh                                 # end-to-end, prints a table
python scripts/build_dashboard.py                          # regenerate docs/index.html
```

The key lives in `.env` only. `tests/test_claims.py` **fails the build** if a live key is ever
tracked, and if `.env`, `.env.local` or `opencode.json` are not gitignored.

## Architecture

```
                     mcxlive.plane        <-- the ONLY module that touches the network
                     (TinyFish Fetch/Search/Agent, X-API-Key from env)
                                       |
                     mcx_live.ingest     <-- pure: page text in, tidy frame out
                     (DateDisplay wins; OPTFUT dropped)
                                       |
                     mcx_live.analysis   <-- the structural bound, fitted to nothing
                     (matched basis, one-way direction)
                                       |
                     mcx_live.cli / server  <-- one definition of "the verdict"
```

`cli.build_report` and `server.run_scan` call the same function, so a test asserts the two agree.
`plane` is the only module importing `urllib`, and a test asserts that too — which is what makes it
safe to attach network access to a finished analysis.

## What it found

Running the live data through the ingest layer **exposed a real date bug**. The API payload carries
both `Date` (`10/12/2026`, MM/DD/YYYY) and `DateDisplay` (`12 Oct 2026`). A parser that tries
`DD/MM/YYYY` first resolves the ambiguous slash date the wrong way and **silently moves every row
by two months**. The fix prefers the unambiguous `DateDisplay`; `tests/test_ingest.py` holds the
regression.

## Repo layout

| Path | What it is |
|---|---|
| `mcx_live/` | `contracts` (the facts), `ingest` (parsing), `analysis` (the bound), `plane` (network), `cli`, `server` |
| `tests/` | 44 tests, all offline; the claims suite guards the published evidence and the secrets |
| `docs/TINYFISH.md` | the full plan, the gate results, and every honest limit found while building |
| `data/mcx_circulars_oct_dec_2024.json` | the archived 204-circular Agent run, with its run id |
| `scripts/` | `smoke_live.sh` (end-to-end), `build_dashboard.py` (regenerates the page from scans), `read_circular766.sh` (one in-window circular read via Agent) |

## Definition of done

- [x] Real MCX data, no API key invented, no synthetic rows
- [x] Input → output CLI, deterministic
- [x] Structural bound with sourced facts and ranged assumptions
- [x] Maturity-matched basis, offset expiry calendars handled
- [x] One-way direction: only the tradeable side counts
- [x] The plane is the only network code, proven by a test
- [x] The CLI and the server share one verdict function
- [x] No live key can be committed, proven by a test
- [x] The gate results and their limits are published, not smoothed over

---

Built for the TinyFish Builder Challenge. MIT licensed.
