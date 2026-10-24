"""Measure the QIRO heuristic against the exact optimum on random synthetic instances.

    python benchmarks/qiro_optimality.py --instances 500 --seed 0

Instances draw finding types/severities/pillars uniformly from the remediation
catalogue, with budgets {20k, 50k, 100k} USD and downtime {4, 10, 40} h, n in [3, 14].
Reports, for annealing alone and annealing + local-search polish, the share of
instances solved optimally and the gap distribution. Synthetic workload only.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.knowledge.remediation import ACTION_TEMPLATES  # noqa: E402
from safeguard_pq.optimizer import qiro  # noqa: E402

TYPES = sorted(ACTION_TEMPLATES)
SEVS = ["critical", "high", "medium", "low"]
PILLARS = ["Trust", "Identity", "Privacy", "Protection", "Safety", "Security"]
AGENTS = ["crypto_inventory", "pq_identification", "clinical_privacy", "device_identity", "safety_risk", "secret_exposure"]


def instance(rng: random.Random) -> tuple[list[dict], float, float]:
    n = rng.randint(3, qiro.EXACT_SOLVER_MAX_N)
    findings = [{"id": f"F{i}", "agent": rng.choice(AGENTS), "type": rng.choice(TYPES), "severity": rng.choice(SEVS),
                 "detail": "", "tippss_mapping": rng.sample(PILLARS, rng.randint(1, 3))} for i in range(n)]
    return findings, rng.choice([20_000, 50_000, 100_000]), rng.choice([4, 10, 40])


def summarize(gaps: list[float]) -> dict:
    return {
        "optimal_share": round(sum(g <= 1e-9 for g in gaps) / len(gaps), 4),
        "mean_gap_pct": round(statistics.fmean(gaps), 4),
        "p95_gap_pct": round(sorted(gaps)[int(0.95 * (len(gaps) - 1))], 4),
        "max_gap_pct": round(max(gaps), 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "qiro_optimality.json")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    sa_gaps, final_gaps, times = [], [], []
    for k in range(args.instances):
        findings, budget, downtime = instance(rng)
        t0 = time.perf_counter()
        r = qiro.optimize(findings, budget, downtime, seed=k)
        times.append((time.perf_counter() - t0) * 1000)
        o = r["optimality"]
        if not o or not o["exact_objective"]:
            continue
        ex = o["exact_objective"]
        sa_gaps.append(100 * (ex - o["annealing_objective"]) / ex)
        final_gaps.append(100 * (ex - o["heuristic_objective"]) / ex)

    result = {
        "benchmark": "qiro_optimality_vs_exhaustive",
        "software_version": __version__,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "instances_with_nonzero_optimum": len(final_gaps),
        "annealing_only": summarize(sa_gaps),
        "annealing_plus_local_search": summarize(final_gaps),
        "mean_optimize_ms_including_exact_solver": round(statistics.fmean(times), 2),
        "caveat": "Synthetic random instances drawn from the illustrative remediation catalogue; not real hospital data.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
