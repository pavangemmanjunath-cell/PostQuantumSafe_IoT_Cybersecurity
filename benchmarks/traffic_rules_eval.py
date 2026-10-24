"""Evaluate the heuristic traffic rules on CICIoMT2024 CSV files (window-level).

The dataset is NOT redistributed with this repository. Download it from the
Canadian Institute for Cybersecurity (see datasets/README.md) and pass the
folder containing the ``*.pcap.csv`` test files:

    python benchmarks/traffic_rules_eval.py --data-dir /path/to/CICIoMT2024/test --window 100

Each file is cut into consecutive non-overlapping windows of ``--window`` rows
(the same window the CSV upload adapter uses). A window counts as "flagged"
when any traffic rule fires. Expected label per file is taken from the file
name (benign vs. attack), which is how CICIoMT2024 distributes its splits.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.knowledge import traffic_rules  # noqa: E402


def windows(path: Path, size: int, max_windows: int):
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        buf: list[dict] = []
        produced = 0
        for row in reader:
            buf.append(row)
            if len(buf) == size:
                yield buf
                produced += 1
                buf = []
                if produced >= max_windows:
                    return


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, type=Path)
    ap.add_argument("--window", type=int, default=100)
    ap.add_argument("--max-windows", type=int, default=2000)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "traffic_rules_eval.json")
    args = ap.parse_args()

    files = sorted(args.data_dir.glob("*.csv"))
    if not files:
        print(f"No CSV files found in {args.data_dir}", file=sys.stderr)
        return 1

    rows = []
    for f in files:
        is_benign = "benign" in f.name.lower()
        n = flagged = 0
        hits: Counter[str] = Counter()
        for w in windows(f, args.window, args.max_windows):
            feats = traffic_rules.features_from_rows(w)
            fired = [r["type"] for r in traffic_rules.evaluate(feats) if r["hit"]]
            n += 1
            flagged += bool(fired)
            hits.update(fired)
        rate = flagged / n if n else 0.0
        rows.append({
            "file": f.name,
            "expected": "benign" if is_benign else "attack",
            "windows": n,
            "flagged_windows": flagged,
            "flag_rate": round(rate, 4),
            "metric": "false_positive_rate" if is_benign else "detection_rate",
            "rule_hits": dict(hits.most_common()),
        })
        print(f"{f.name:40s} windows={n:5d} flagged={flagged:5d} rate={rate:.3f} {dict(hits.most_common(3))}")

    result = {
        "benchmark": "traffic_rules_window_eval",
        "software_version": __version__,
        "date": date.today().isoformat(),
        "window_rows": args.window,
        "max_windows_per_file": args.max_windows,
        "python": platform.python_version(),
        "caveat": "Thresholds were chosen by inspecting this same data; results are optimistic and not a generalisation estimate.",
        "results": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWritten: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
