"""Command line entry points.

    python -m mcx_live wallet
    python -m mcx_live live                       # today's bhavcopy + verdict
    python -m mcx_live scan --last N              # last N rows from the archive
    python -m mcx_live circulars 01/10/2024 31/12/2024
    python -m mcx_live search "gold petal contract"

Everything prints as JSON so it can be piped, diffed and archived. The key is
read from the environment and never printed.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import plane
from .analysis import bound_for, matched_basis, verdict
from .contracts import CONTRACTS
from .ingest import extract_bhavcopy_array, normalise


def _emit(payload) -> None:
    sys.stdout.write(json.dumps(payload, indent=1, default=str) + "\n")


def _reference_price(frame) -> float:
    """Derive the reference price from the data, never hardcode one.

    The median rupees-per-gram-of-fine across every traded row. A fixed
    reference price would make the bound's basis points quietly wrong the first
    time the market moved.
    """
    traded = frame[~frame["no_trade"]]
    return float(traded["px_per_g_fine"].median())


def build_report(frame, source: str) -> dict:
    """Run the full analysis on a normalised frame.

    Shared by the CLI and the HTTP server so there is exactly one definition of
    "the verdict", and so a test can assert the two agree.
    """
    ref = _reference_price(frame)
    basis = matched_basis(frame)
    rows = verdict(basis, ref)
    cleared = sum(1 for r in rows if r["cleared"])
    date = str(frame["date"].max().date())
    return {
        "source": source,
        "date": date,
        "rows": int(len(frame)),
        "rows_with_trades": int((~frame["no_trade"]).sum()),
        "reference_price_inr_per_g_fine": round(ref, 2),
        "basis_observations": int(len(basis)),
        "pairs": [
            {
                "pair": r["pair"],
                "bound_bps": [r["bound_low_bps"], r["bound_high_bps"]],
                "centre_bps": r["bound_centre_bps"],
            }
            for r in rows
        ],
        "verdict_summary": {
            "pairs_tested": len(rows),
            "pairs_cleared": cleared,
        },
        "verdicts": rows,
        "summary_line": (
            f"{date}: {len(rows)} pairs tested, {cleared} cleared the bound"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mcx_live", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("wallet", help="wallet balance and per-unit rates")
    sub.add_parser("live", help="fetch and parse today's live bhavcopy")
    sp = sub.add_parser("scan", help="analyse an archived circular window")
    sp.add_argument("date_from")
    sp.add_argument("date_to")
    sp.add_argument("--max-wait", type=float, default=1800.0)
    s2 = sub.add_parser("search", help="free TinyFish web search")
    s2.add_argument("query")

    args = ap.parse_args(argv)

    try:
        if args.cmd == "wallet":
            w = plane.wallet()
            _emit(
                {
                    "available_balance": w.get("available_balance"),
                    "currency": w.get("currency"),
                    "rates": {
                        m["label"]: f"{m['unit_amount']} / {m['per']}"
                        for m in w.get("rates", {}).get("meters", [])
                    },
                }
            )
        elif args.cmd == "live":
            frame, source = plane.live_frame()
            report = build_report(frame, source)
            _emit(report)
            sys.stderr.write(report["summary_line"] + "\n")
        elif args.cmd == "circulars":
            run = plane.archive_circulars(
                args.date_from, args.date_to, max_wait=args.max_wait
            )
            res = run.get("result") or {}
            circulars = res.get("circulars") or []
            _emit(
                {
                    "run_id": run.get("run_id"),
                    "status": run.get("status"),
                    "steps": run.get("num_of_steps"),
                    "applied_date_filter": res.get("applied_date_filter"),
                    "reason_if_failed": res.get("reason_if_failed"),
                    "circulars": circulars,
                }
            )
            sys.stderr.write(
                f"{run.get('status')}: {len(circulars)} circulars "
                f"({run.get('num_of_steps')} agent steps)\n"
            )
        elif args.cmd == "search":
            _emit({"query": args.query, "results": plane.search(args.query)})
    except plane.TinyFishUnavailable as exc:
        sys.stderr.write(f"tinyfish unavailable: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
