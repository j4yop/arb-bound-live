"""Guards that the published claims are backed by committed evidence.

The repo's rule is that no claim is written down until the code produces it.
``docs/TINYFISH.md`` makes empirical claims about what the TinyFish API does;
this suite checks the committed evidence actually supports them, and that the
offline suites never secretly become live metered calls.

A further group guards credential hygiene: `.env`, `.env.local` and
`opencode.json` all held live secrets at one point and a blanket `.env*` rule
did not cover them all.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

DOC = Path("docs/TINYFISH.md")
ARCHIVE = Path("data/mcx_circulars_oct_dec_2024.json")
SAMPLE = Path("docs/data/scan-sample.json")
SECRET_FILES = (".env", ".env.local", "opencode.json")


def _looks_like_real_key(blob: bytes) -> bool:
    """A real key is ``sk-tinyfish-`` then 20+ random characters.

    The template placeholder is short and obviously fake, so this separates
    "documented placeholder" from "leaked credential".
    """
    return bool(re.search(rb"sk-tinyfish-[A-Za-z0-9_-]{20,}", blob))


# ------------------------------------------------------------- evidence


def test_gate_results_are_published_with_an_outcome():
    text = DOC.read_text()
    for check in ("G1", "G2", "G3", "G4"):
        assert check in text, f"{check} gate is missing from the plan"
    assert re.search(r"\*\*(PASS|PARTIAL)\*\*", text), "no gate outcome recorded"


def test_archived_circulars_match_the_claimed_count():
    """The headline claim -- 204 circulars -- must match the committed file."""
    assert ARCHIVE.exists(), (
        f"{ARCHIVE} missing: the 204-circulars claim has no committed evidence"
    )
    data = json.loads(ARCHIVE.read_text())
    assert data["date_filter"] == "01/10/2024 to 31/12/2024"
    assert data["status"] == "COMPLETED", data["status"]
    assert data["source"].startswith("TinyFish Web Agent run ")
    assert len(data["circulars"]) == 204, len(data["circulars"])


def test_the_gold_petal_circular_is_in_the_archived_evidence():
    """The specific circular the whole archive search was run to find."""
    data = json.loads(ARCHIVE.read_text())
    hits = [
        c
        for c in data["circulars"]
        if c.get("circular_no") == "858"
        and "Gold Petal" in c.get("title", "")
        and c.get("date") == "31 Dec 2024"
    ]
    assert hits, "circular 858 (Gold Petal Apr-2025) is not in the archive"


def test_the_date_bug_and_its_fix_are_documented():
    text = DOC.read_text()
    assert "DateDisplay" in text, "the date bug is not documented"
    assert "2026-10-12" in text, "the corrected date is not recorded"


# ----------------------------------------------------- repo invariants


def test_the_engine_never_touches_the_network():
    """``plane`` is the only module allowed to import ``urllib``."""
    import mcx_live

    root = Path(mcx_live.__file__).parent
    offenders = []
    for path in sorted(root.glob("*.py")):
        if path.name == "plane.py":
            continue
        text = path.read_text()
        if "urllib.request" in text or "import urllib" in text:
            offenders.append(path.name)
    assert not offenders, f"network access outside plane.py: {offenders}"


def test_lenient_of_no_license():
    """A repo submitted to a sponsor should carry a licence."""
    assert Path("LICENSE").exists(), "LICENSE is missing"


def test_the_published_dashboard_is_generated_not_hand_typed():
    """The page's numbers must be reproducible from committed scans.

    A hand-edited dashboard would drift the moment the market moved, and would
    silently claim a figure no run produced. Regenerating must be a no-op.
    """
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, "scripts/build_dashboard.py"],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    # Regenerating into the same path must not change the committed file.
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "docs/index.html"],
        capture_output=True,
        text=True,
    )
    assert diff.returncode == 0, (
        "docs/index.html is stale -- run scripts/build_dashboard.py and commit it"
    )


def test_the_daily_scan_directory_is_committable():
    """Regression: scans/ was gitignored, so the daily workflow's ``git add
    scans/`` failed silently and it reported success while committing nothing.

    The corpus is the point of the scheduled job; if it cannot be committed the
    job is theatre.
    """
    import subprocess

    out = subprocess.run(
        ["git", "check-ignore", "scans/"], capture_output=True, text=True
    )
    assert out.returncode != 0, (
        "scans/ is gitignored -- `git add scans/` will silently skip it and the "
        "daily workflow will commit nothing"
    )
    # And the workflow must use -f, so it stays correct if that regresses.
    daily = Path(".github/workflows/daily.yml").read_text()
    assert "git add -f scans/" in daily, (
        "the daily workflow should force-add scans/ so a .gitignore change "
        "cannot silently break it"
    )
    """The committed sample must carry the shape build_dashboard expects."""
    assert SAMPLE.exists(), "docs/data/scan-sample.json is missing"
    data = json.loads(SAMPLE.read_text())
    for key in ("date", "source", "rows_with_trades", "basis_observations",
                "reference_price_inr_per_g_fine", "verdict_summary", "verdicts"):
        assert key in data, f"sample scan is missing {key}"
    # And it must have come from the plane, not been written by hand.
    assert data["source"].startswith("tinyfish-live:"), data["source"]


# ------------------------------------------------------ credential guards


def test_files_that_can_hold_secrets_are_gitignored():
    for name in SECRET_FILES:
        out = subprocess.run(
            ["git", "check-ignore", name], capture_output=True, text=True
        )
        assert out.returncode == 0, (
            f"{name} is not gitignored and can carry a live credential"
        )


def test_tracked_tree_holds_no_live_key():
    """Binary-safe: a .pptx or .csv must not abort the scan."""
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True
    ).stdout.split()
    leaked = []
    for rel in tracked:
        path = Path(rel)
        if not path.is_file():
            continue
        try:
            blob = path.read_bytes()
        except OSError:
            continue
        if _looks_like_real_key(blob):
            leaked.append(rel)
    assert not leaked, f"a live TinyFish key is committed in: {leaked}"


def test_templates_document_the_config_without_the_secret():
    for template in (".env.example",):
        path = Path(template)
        assert path.exists(), f"{template} is missing"
        assert not _looks_like_real_key(path.read_bytes()), (
            f"{template} contains a credential"
        )
        assert "TINYFISH_API_KEY" in path.read_text(), f"{template} names no key"
