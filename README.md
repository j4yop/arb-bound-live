# arb-bound-live

**Live MCX gold data through [TinyFish](https://tinyfish.ai), evaluated in real time against a structural no-arbitrage bound.**

Built for **Hack in Hills '26 · TinyFish Builder Challenge**.

---

## Live Links

- **Production Dashboard:** <https://arb-bound-live.vercel.app/>
- **API Endpoints:** `/health` &nbsp;·&nbsp; `/scan` &nbsp;·&nbsp; `/circulars`

---

## Problem Statement

The Multi Commodity Exchange of India (MCX) lists the same physical underlying commodity—gold—across four separate futures contracts:

| Contract | Lot Size | Quote Base | Purity | Expiry Calendar |
|---|---|---|---|---|
| `GOLDM` | 100 g | per 10 g | **995** | 3rd–5th |
| `GOLDTEN` | 10 g | per 10 g | 999 | 27th–31st |
| `GOLDGUINEA` | 8 g | per 8 g | 999 | 27th–31st |
| `GOLDPETAL` | 1 g | per 1 g | 999 | 27th–31st |

Screen traders observing price spreads across these contracts frequently assume an exploitable arbitrage exists. In reality, three structural barriers prevent riskless extraction:

1. **Compulsory physical delivery:** Closing a cross-contract basis requires taking delivery of physical bars, not simple cash settlement.
2. **Fixed fabrication costs per bar:** Minting, assaying, serialising, and transporting gold bars is fixed per bar, not per gram. Therefore, per-gram overhead scales **inversely with bar size** (`mint_cost_per_bar / bar_grams`). A 1 g bar carries ~8× the per-gram fabrication overhead of an 8 g bar.
3. **Contractual purity and quotation basis wedge:** `GOLDM` is 995-fineness quoted duty-inclusive *Ex-Ahmedabad*, while retail contracts are 999-fineness quoted *Ex-Mumbai*. Delivery rules settle 999 bars into 995 contracts at `Rate × 999/995`.

**The Data Access Challenge:**  
While MCX market data is public, `mcxindia.com` blocks all standard automated access with **HTTP 403 (Akamai Access Denied)** from cloud/datacenter IPs. `curl` and headless scrapers fail instantly, preventing traders and models from ingesting live exchange feeds or auditing regulatory circular archives without dedicated residential browser infrastructure.

---

## Questions Asked & Solutions Delivered

### Q1. How do we ingest live MCX exchange data without getting blocked by Akamai edge defenses?
- **The Problem:** Direct automated HTTP requests from cloud environments fail with HTTP 403 Access Denied.
- **The Solution:** Routed ingestion through the **TinyFish Live Plane** (`mcx_live.plane`), utilizing TinyFish Fetch with residential browser emulation and anti-fingerprinting proxies.
- **The Outcome:** Successfully ingests 4.9 MB of official MCX daily bhavcopy JSON on the exact endpoint blocked to standard `curl`. Resilient retry logic handles occasional partial HTML shells.

### Q2. How do we prevent silent calendar shifts caused by ambiguous exchange date strings?
- **The Problem:** The raw exchange JSON carries two date fields: `Date` (e.g. `10/12/2026`) and `DateDisplay` (e.g. `12 Oct 2026`). Naive parsers attempting `DD/MM/YYYY` resolve slash-delimited dates as December 10 instead of October 12, silently shifting the dataset by 2 months.
- **The Solution:** Pure functional ingest layer (`mcx_live.ingest`) enforces priority on unambiguous `DateDisplay`, stripping ambiguous slash fields and dropping non-spot `OPTFUT` records.
- **The Outcome:** Deterministic parsing verified by regression tests (`tests/test_ingest.py`).

### Q3. Does an observed cross-contract basis represent real mispricing or a structural cost?
- **The Problem:** Traditional statistical models fit curves to historical spreads, confusing structural delivery costs with tradeable alpha.
- **The Solution:** Derived a non-parametric, structural economic bound fitted to **zero price points**:
  $$\text{Bound} = \Delta \text{Fabrication Overhead} + \text{Purity/Duty Wedge} + \text{Statutory Frictions and Slippage}$$
  - **Fabrication Overhead Difference:** `mint_cost_per_bar × (1/small_grams - 1/large_grams)` (₹20–60/bar parameter sweep).
  - **Purity/Duty Wedge:** Contract specifications (0–400 bps range).
  - **Statutory Friction:** Brokerage, GST/CTT, stamp duty, exchange turnover fees (4–35 bps per leg).
  - **One-Way Asymmetry:** Because small bars are physically dearer to fabricate, only the direction where the smaller bar trades rich is tradeable. Evaluating both sides produces hundreds of false breach signals.
- **The Outcome:** Real-time evaluation categorizes live price spreads into structural wedges vs actionable breaches.

### Q4. Did a contract specification change drive the historic basis drift, or was it retail flow?
- **The Problem:** Historical basis series (e.g., November 2024 basis drift) required verifying whether MCX issued regulatory circulars modifying contract specs or delivery centers, but the exchange circular archive was behind the same Akamai block.
- **The Solution:** Deployed **TinyFish Web Agent** across 115 autonomous steps to navigate the official MCX dated circulars portal across all 14 pages for Oct–Dec 2024.
- **The Outcome:** Indexed and verified 204 official circulars. Circular #858 confirmed the April 2025 contract launched under identical terms, proving the basis movement was driven by retail premium compression following the US election macro shock, not regulatory changes.

---

## Project Workflow

```
[MCX India Exchange Endpoint]
               │
               ▼
[1. TinyFish Live Plane]        ──► Stealth browser session bypasses Akamai HTTP 403; fetches bhavcopy JSON
               │
               ▼
[2. Ingest & Sanitisation]      ──► Pure functional parser; prioritises DateDisplay; filters OPTFUT
               │
               ▼
[3. Purity & Unit Normalisation]──► Normalises all quotes to INR per gram of fine gold
               │
               ▼
[4. Maturity Matching]          ──► Pairs nearest expiries across GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL
               │
               ▼
[5. Structural Bound Engine]    ──► Applies non-parametric bound (one-way fabrication + purity + friction)
               │
               ▼
[6. Unified Verdict Generator]  ──► Shared verdict logic classifies quotes: structural wedge vs breach
               │
               ▼
[7. Multi-Target Delivery]      ──► CLI terminal output, FastAPI endpoints (/scan), & Vercel Dashboard
```

---

## Architecture & Codebase Layout

The codebase enforces strict unidirectional dependency flow and network boundary isolation:

```
                     mcx_live.plane        <-- The ONLY module that touches the network
                     (TinyFish Fetch / Agent APIs, API key isolation)
                                       │
                     mcx_live.ingest       <-- Pure functional: raw text in, normalised contracts out
                     (DateDisplay precedence; OPTFUT dropped)
                                       │
                     mcx_live.analysis     <-- Pure mathematical engine: zero-price fitted bound
                     (Matched-maturity basis, one-way asymmetry)
                                       │
                     mcx_live.cli / server <-- Unified consumer: identical scan & report verdicts
```

| Path | Description |
|---|---|
| `mcx_live/plane.py` | Network interface: TinyFish Fetch, Search, and Web Agent wrappers. Guarded by isolation tests. |
| `mcx_live/ingest.py` | Normalisation: converts raw exchange JSON into typed contract records; resolves ambiguous dates. |
| `mcx_live/analysis.py` | Mathematical bound engine: calculates maturity-matched basis against the analytical bound. |
| `mcx_live/contracts.py` | Ground truth contract specifications: lot sizes, purities, delivery mechanisms, quotation bases. |
| `mcx_live/server.py` | FastAPI application exposing `/health`, `/scan`, and `/circulars` endpoints. |
| `mcx_live/cli.py` | Terminal interface sharing the exact same verdict engine with the server. |
| `data/mcx_circulars_oct_dec_2024.json` | Committed evidence of the 204-circular TinyFish Agent archive run. |
| `scripts/` | `smoke_live.sh` (end-to-end live test), `build_dashboard.py` (generates dashboard from scans). |
| `tests/` | 47 offline tests guarding determinism, network isolation, claims evidence, and credentials. |

---

## Tech Stack

- **Live Web Automation:** [TinyFish API](https://tinyfish.ai) (Fetch API for bhavcopy ingestion; Autonomous Web Agent for multi-page circular archive extraction).
- **Core Engine:** Python 3.11+, typed dataclasses, pure functional transformations.
- **Web API & Server:** FastAPI, Uvicorn, ASGI serverless adapter for Vercel.
- **Frontend & Dashboard:** Pure HTML5 + SVG dashboard auto-generated from committed scan JSON (`scripts/build_dashboard.py`).
- **Testing & Safety:** `pytest` (47 unit and integration tests), AST-level credential leak guards, network-import containment verification.
- **Deployment:** Vercel Edge Network (<https://arb-bound-live.vercel.app/>).

---

## Verified Empirical Gates

| Gate | Objective | Result | Committed Evidence |
|---|---|---|---|
| **G1** | Live MCX Bhavcopy Ingestion | **PASS** | 4.9 MB of official JSON containing all gold contracts fetched on the URL `curl` is blocked on |
| **G3** | Circulars Archive Listing | **PASS** | Successfully navigates archive rows without triggering Akamai blocks |
| **G4** | Autonomous Date-Filtered Archive Traversal | **PASS** | TinyFish Agent completed 115 steps across 14 pages, indexing **204 circulars** for Oct–Dec 2024 |

---

## Quick Start

### 1. Environment & Installation
```bash
git clone https://github.com/j4yop/arb-bound-live.git
cd arb-bound-live

# Configure TinyFish credentials
cp .env.example .env
# Edit .env and paste your key: TINYFISH_API_KEY=sk-tinyfish-...

# Install package with server and dev dependencies
pip install -e ".[server,dev]"
```

### 2. Run Offline Tests
```bash
# 47 offline tests verifying parsing, bound math, network isolation, and claims
pytest -q
```

### 3. Run Live Ingestion & Analysis
```bash
# Check TinyFish wallet balance and API rates
python -m mcx_live wallet

# Fetch live MCX bhavcopy, parse, evaluate bound, and output verdict
python -m mcx_live live

# Query official circular archive via TinyFish Agent
python -m mcx_live circulars 01/10/2024 31/12/2024

# Launch local FastAPI server
uvicorn mcx_live.server:app --reload

# Run full end-to-end live smoke test
bash scripts/smoke_live.sh
```

---

## Verification & Guardrails

- **Zero Credential Leakage:** `tests/test_claims.py` scans all tracked git files and fails the build if any live `sk-tinyfish-` key is committed, or if `.env`, `.env.local`, or `opencode.json` are unignored.
- **Architectural Isolation:** `test_the_engine_never_touches_the_network` asserts that only `plane.py` imports `urllib`, ensuring analysis logic never triggers accidental live network calls.
- **Dashboard Integrity:** `test_the_published_dashboard_is_generated_not_hand_typed` guarantees that `docs/index.html` matches committed scan data exactly.

---

## License

MIT License. Built for the Hack in Hills '26 TinyFish Builder Challenge.
