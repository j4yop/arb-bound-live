#!/usr/bin/env bash
# Run the live scan offline of the repo's own venv assumptions.
# Usage: bash scripts/smoke_live.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; . ./.env; set +a; fi

if ! command -v curl >/dev/null; then
  echo "curl required" >&2; exit 1
fi

echo "== 1. wallet =="
python -m mcx_live wallet

echo
echo "== 2. live scan =="
python -m mcx_live live > /tmp/scan.json 2>/tmp/scan.err || { cat /tmp/scan.err; exit 1; }
cat /tmp/scan.err
python - <<'PY'
import json
d = json.load(open('/tmp/scan.json'))
print("date            :", d["date"])
print("source          :", d["source"])
print("rows / traded   :", d["rows"], "/", d["rows_with_trades"])
print("reference price :", d["reference_price_inr_per_g_fine"], "INR/g fine")
print("basis obs       :", d["basis_observations"])
print("pairs           :", d["verdict_summary"])
for p in d["pairs"]:
    print(f'  {p["pair"]:<18} bound {p["bound_bps"][0]:>7.1f} .. {p["bound_bps"][1]:>7.1f} bps  centre {p["centre_bps"]:>7.1f}')
for v in d["verdicts"]:
    print(f'  {v["pair"]:<18} median {v["median_basis_bps"]:>8.1f} bps  cleared={v["cleared"]}  above={v["days_above_bound"]}')
PY
