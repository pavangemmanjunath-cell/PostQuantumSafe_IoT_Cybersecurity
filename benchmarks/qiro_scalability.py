"""Scale the QIRO heuristic to n = 20..200 remediation actions and compare it with an exact ILP optimum.

    python benchmarks/qiro_scalability.py --sizes 20,50,100,200 --instances-per-size 50 --seed 0

Extension of ``qiro_optimality.py``, whose exhaustive reference is limited to n ≤ 14.
Findings are drawn exactly as in ``qiro_optimality.instance`` (type, severity, agent and TIPPSS pillars
uniformly from the remediation catalogue) but with n fixed per size, and the constraint tightness
τ ∈ {0.25, 0.5, 0.75} is sampled per instance: budget = τ·Σ cost_i and max_downtime = τ·Σ downtime_i.

Methods compared on identical instances: the greedy value-density start alone, greedy + the shipped
deterministic local search (no annealing), greedy + simulated annealing (``annealing_objective``), the
shipped QIRO pipeline greedy + annealing + local-search polish (``heuristic_objective``), and the exact
optimum from the HiGHS MIP solver (``_ilp.py``, zero gap tolerances). Gap formula per instance:
gap_pct = 100·(f_ILP − f_method)/f_ILP; instances with f_ILP = 0 are skipped and counted. Before the main
run the ILP model is cross-validated against the exhaustive solver on ``--small-check`` instances with
n ∈ [3, 14]; the run aborts if any of them disagree. Synthetic workload only; catalogue costs are
illustrative placeholders.
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from _ilp import DEFAULT_TIME_LIMIT_S, SOLVER_OPTIONS, ilp_optimum, solver_name
from qiro_optimality import AGENTS, PILLARS, SEVS, TYPES, summarize
from safeguard_pq import __version__
from safeguard_pq.knowledge.remediation import ACTION_TEMPLATES
from safeguard_pq.optimizer import qiro

TAUS = (0.25, 0.5, 0.75)
METHODS = ("greedy", "greedy_local_search", "annealing", "annealing_local_search")
TIMED_METHODS = ("greedy", "greedy_local_search", "annealing_local_search", "ilp")
SMALL_CHECK_TOLERANCE = 1e-6
OPTIMAL_TOLERANCE = 1e-9


# --------------------------------------------------------------------------------------------- instances
def findings_for(rng: random.Random, n: int) -> list[dict]:
    """``n`` synthetic findings drawn with the same per-finding rules as ``qiro_optimality.instance``."""
    return [{"id": f"F{i}", "agent": rng.choice(AGENTS), "type": rng.choice(TYPES), "severity": rng.choice(SEVS),
             "detail": "", "tippss_mapping": rng.sample(PILLARS, rng.randint(1, 3))} for i in range(n)]


def instance(rng: random.Random, n: int) -> tuple[list[dict], float, float, float]:
    """Return ``(findings, budget, max_downtime, tau)`` with budget = τ·Σcost and max_downtime = τ·Σdowntime."""
    findings = findings_for(rng, n)
    tau = rng.choice(TAUS)
    actions = qiro.build_actions(findings)
    return findings, tau * sum(a["cost_usd"] for a in actions), tau * sum(a["downtime_hrs"] for a in actions), tau


def size_rng(seed: int, n: int) -> random.Random:
    """Instance stream for one size; independent of which other sizes are requested."""
    return random.Random(f"{seed}-n{n}")


# ----------------------------------------------------------------------------------------------- methods
def greedy_start(actions: list[dict], budget: float, max_dt: float) -> list[int]:
    """The greedy value-density start used inside ``qiro.optimize`` (same order and feasibility test)."""
    n = len(actions)
    sel = [0] * n
    cost = dt = 0.0
    for i in sorted(range(n), key=lambda k: -actions[k]["value_density"]):
        if cost + actions[i]["cost_usd"] <= budget and dt + actions[i]["downtime_hrs"] <= max_dt:
            sel[i] = 1
            cost += actions[i]["cost_usd"]
            dt += actions[i]["downtime_hrs"]
    return sel


def evaluate(findings: list[dict], budget: float, max_dt: float, tau: float, seed: int, time_limit_s: float) -> dict:
    """Run every method on one instance and return the raw record."""
    actions = qiro.build_actions(findings)

    t0 = time.perf_counter()
    result = qiro.optimize(findings, budget, max_dt, seed=seed)
    optimize_ms = (time.perf_counter() - t0) * 1000
    opt = result["optimality"]

    t0 = time.perf_counter()
    greedy = greedy_start(actions, budget, max_dt)
    greedy_ms = (time.perf_counter() - t0) * 1000
    greedy_obj = qiro.objective(greedy, actions, budget, max_dt)
    if abs(greedy_obj - opt["greedy_objective"]) > 1e-6:
        raise RuntimeError(f"greedy replica {greedy_obj} != qiro greedy_objective {opt['greedy_objective']}")

    t0 = time.perf_counter()
    _, gls_obj, gls_moves = qiro._local_search(greedy, actions, budget, max_dt)
    gls_ms = greedy_ms + (time.perf_counter() - t0) * 1000

    ilp = ilp_optimum(actions, budget, max_dt, time_limit_s=time_limit_s)
    coefficients = [a["optimization_benefit"] - 0.5 * a["complexity"] for a in actions]
    return {
        "n": len(actions),
        "tau": tau,
        "optimizer_seed": seed,
        "budget_usd": budget,
        "max_downtime_hrs": max_dt,
        "iterations_run": result["iterations_run"],
        "objective": {
            "greedy": opt["greedy_objective"],
            "greedy_local_search": gls_obj,
            "annealing": opt["annealing_objective"],
            "annealing_local_search": opt["heuristic_objective"],
            "ilp": ilp["objective"],
        },
        "runtime_ms": {
            "greedy": round(greedy_ms, 3),
            "greedy_local_search": round(gls_ms, 3),
            "annealing_local_search": round(optimize_ms, 3),
            "ilp": ilp["solve_ms"],
        },
        "local_search_moves": {"greedy_local_search": gls_moves, "annealing_local_search": opt["local_search_moves"]},
        "annealing_accepted_moves": opt["accepted_moves"],
        "selected_count": {"annealing_local_search": result["selection_count"], "ilp": sum(ilp["selection"])},
        "ilp_status": ilp["status"],
        "action_ranges": {
            "cost_usd": [min(a["cost_usd"] for a in actions), max(a["cost_usd"] for a in actions)],
            "downtime_hrs": [min(a["downtime_hrs"] for a in actions), max(a["downtime_hrs"] for a in actions)],
            "complexity": [min(a["complexity"] for a in actions), max(a["complexity"] for a in actions)],
            "optimization_benefit": [min(a["optimization_benefit"] for a in actions), max(a["optimization_benefit"] for a in actions)],
            "objective_coefficient": [min(coefficients), max(coefficients)],
        },
    }


def gap_pct(record: dict, method: str) -> float:
    f_ilp = record["objective"]["ilp"]
    return 100 * (f_ilp - record["objective"][method]) / f_ilp


# --------------------------------------------------------------------------------------------- aggregates
def _runtime_stats(values: list[float]) -> dict:
    if not values:
        return {"mean_runtime_ms": None, "max_runtime_ms": None}
    return {"mean_runtime_ms": round(statistics.fmean(values), 3), "max_runtime_ms": round(max(values), 3)}


def aggregate(records: list[dict]) -> dict:
    """Optimal share / gap distribution / runtime per method over ``records`` (instances with f_ILP = 0 skipped)."""
    nonzero = [r for r in records if r["objective"]["ilp"] > 0]
    out: dict[str, Any] = {
        "instances": len(records),
        "instances_with_nonzero_ilp_optimum": len(nonzero),
        "skipped_zero_ilp_optimum": len(records) - len(nonzero),
        "methods": {},
    }
    for m in METHODS:
        gaps = [gap_pct(r, m) for r in nonzero]
        entry: dict[str, Any] = summarize(gaps) if gaps else {}
        entry.update(_runtime_stats([r["runtime_ms"][m] for r in records if m in r["runtime_ms"]]))
        if m in ("greedy_local_search", "annealing_local_search"):
            entry["mean_local_search_moves"] = round(statistics.fmean(r["local_search_moves"][m] for r in records), 3) if records else None
        out["methods"][m] = entry
    out["methods"]["ilp"] = {
        **_runtime_stats([r["runtime_ms"]["ilp"] for r in records]),
        "statuses": dict(Counter(r["ilp_status"] for r in records)),
    }
    heuristic, ilp = out["methods"]["annealing_local_search"]["mean_runtime_ms"], out["methods"]["ilp"]["mean_runtime_ms"]
    out["runtime_ratio_heuristic_over_ilp"] = round(heuristic / ilp, 3) if heuristic and ilp else None
    return out


def by_tau(records: list[dict]) -> dict:
    return {str(tau): aggregate([r for r in records if r["tau"] == tau]) for tau in TAUS if any(r["tau"] == tau for r in records)}


# -------------------------------------------------------------------------------------------- descriptions
def _range(key: str) -> list[float]:
    values = [getattr(ACTION_TEMPLATES[t], key) for t in TYPES]
    return [min(values), max(values)]


def generator_description(records: list[dict]) -> dict:
    observed = {}
    for key in ("cost_usd", "downtime_hrs", "complexity", "optimization_benefit", "objective_coefficient"):
        observed[key] = [min(r["action_ranges"][key][0] for r in records), max(r["action_ranges"][key][1] for r in records)] if records else None
    return {
        "description": (
            "Each instance is a portfolio of n synthetic findings (one finding = one candidate remediation action). Findings "
            "use the same draw rules as benchmarks/qiro_optimality.py::instance; only n is fixed per size and the constraints "
            "come from a sampled tightness τ instead of fixed budget / downtime levels."
        ),
        "n": "fixed per size (see sizes / instances_per_size)",
        "finding_type": {"distribution": "uniform", "support": "keys of safeguard_pq.knowledge.remediation.ACTION_TEMPLATES",
                         "support_size": len(TYPES), "values": TYPES},
        "severity": {"distribution": "uniform", "values": SEVS, "risk_reduction_multiplier": qiro.SEV_MULT},
        "tippss_mapping": {"distribution": "k ~ U{1, 2, 3} pillars sampled uniformly without replacement", "values": PILLARS,
                           "pillar_weights": qiro.PILLAR_WEIGHTS, "note": "a Safety pillar adds the +20 safety-criticality bonus"},
        "agent": {"distribution": "uniform", "values": AGENTS, "note": "agent pq_identification (or a PQ finding type) adds the +25 PQ-urgency bonus"},
        "catalogue_ranges": {
            "note": "min / max over the remediation catalogue (illustrative placeholder values, not market data)",
            "cost_usd": _range("cost"),
            "downtime_hrs": _range("downtime"),
            "complexity": _range("complexity"),
            "base_risk_reduction": _range("base_risk_reduction"),
        },
        "observed_action_ranges_in_this_run": observed,
        "derived_coefficients": {
            "optimization_benefit": "js_round(base_risk_reduction · sev_mult) + 25·[PQ] + 20·[Safety pillar] + js_round(10 · Σ pillar weights)",
            "objective_coefficient": "optimization_benefit − 0.5 · complexity (all values are integers or halves, so sums are exact in floating point)",
        },
        "constraint_tightness": {
            "tau_values": list(TAUS),
            "distribution": "uniform per instance",
            "budget_usd": "tau · Σ_i cost_usd_i",
            "max_downtime_hrs": "tau · Σ_i downtime_hrs_i",
        },
        "seeding": (
            "instances for size n are drawn from random.Random(f'{seed}-n{n}') so each size's instance set is independent of "
            "the other sizes requested; the k-th instance of a size runs qiro.optimize(seed=k); the small check uses "
            "random.Random(f'{seed}-small-check')"
        ),
    }


def method_description(time_limit_s: float) -> dict:
    return {
        "gap_formula": "gap_pct = 100 · (f_ILP − f_method) / f_ILP per instance; instances with f_ILP = 0 are skipped and counted in skipped_zero_ilp_optimum",
        "optimal_share": f"share of instances with gap_pct ≤ {OPTIMAL_TOLERANCE:g}",
        "p95_gap_pct": "sorted(gaps)[int(0.95 · (m − 1))] over the m evaluated instances (same estimator as qiro_optimality.py)",
        "methods": {
            "greedy": "greedy value-density start of qiro.optimize alone (optimality.greedy_objective)",
            "greedy_local_search": "greedy start + the shipped deterministic best-improvement add / drop / swap local search (qiro._local_search), without annealing",
            "annealing": "greedy start + simulated annealing (optimality.annealing_objective)",
            "annealing_local_search": "shipped QIRO pipeline: greedy start + simulated annealing + local-search polish (optimality.heuristic_objective)",
            "ilp": f"HiGHS MIP reference optimum via highspy with {SOLVER_OPTIONS} and time_limit={time_limit_s:g} s; status 'Optimal' = proven optimal",
        },
        "runtime": {
            "greedy": "wall time of the greedy start (replicated from qiro.optimize; its objective is checked against optimality.greedy_objective on every instance)",
            "greedy_local_search": "wall time of greedy start + qiro._local_search",
            "annealing": "not timed separately (stage inside qiro.optimize)",
            "annealing_local_search": "wall time of qiro.optimize (includes building actions, annealing, local search and the explanation payload; the exhaustive solver is skipped for n > 14)",
            "ilp": "wall time of highspy model construction + HiGHS solve (solve_ms)",
            "note": "single-process wall-clock measurements on one machine; absolute values vary with hardware and load",
        },
        "annealing_schedule": "iterations = min(3000, 200 + 80·n), T0 = 100, cooling 0.995, single-flip feasible moves (qiro.optimize)",
    }


# ------------------------------------------------------------------------------------------------- stages
def small_check(seed: int, count: int, time_limit_s: float) -> dict:
    """Cross-validate the ILP model against the exhaustive solver on n ∈ [3, 14] instances."""
    rng = random.Random(f"{seed}-small-check")
    agreeing, max_abs_diff, mismatches = 0, 0.0, []
    for k in range(count):
        n = rng.randint(3, qiro.EXACT_SOLVER_MAX_N)
        findings, budget, max_dt, tau = instance(rng, n)
        actions = qiro.build_actions(findings)
        exact = qiro.exact_optimum(actions, budget, max_dt)
        ilp = ilp_optimum(actions, budget, max_dt, time_limit_s=time_limit_s)
        diff = abs(exact - ilp["objective"])
        max_abs_diff = max(max_abs_diff, diff)
        if diff <= SMALL_CHECK_TOLERANCE and ilp["status"] == "Optimal":
            agreeing += 1
        else:
            mismatches.append({"index": k, "n": n, "tau": tau, "exact": exact, "ilp": ilp["objective"], "status": ilp["status"]})
    return {
        "description": "ILP optimum vs. exhaustive optimum (qiro.exact_optimum) on instances from the same generator with n ~ U{3..14}",
        "instances": count,
        "n_range": [3, qiro.EXACT_SOLVER_MAX_N],
        "tolerance": SMALL_CHECK_TOLERANCE,
        "agreeing": agreeing,
        "max_abs_diff": max_abs_diff,
        "passed": agreeing == count,
        "mismatches": mismatches,
    }


def run_size(n: int, count: int, seed: int, time_limit_s: float, log) -> list[dict]:
    rng = size_rng(seed, n)
    records = []
    for k in range(count):
        findings, budget, max_dt, tau = instance(rng, n)
        rec = evaluate(findings, budget, max_dt, tau, seed=k, time_limit_s=time_limit_s)
        records.append(rec)
        gaps = " ".join(f"{m}={gap_pct(rec, m):.3f}%" for m in METHODS) if rec["objective"]["ilp"] > 0 else "f_ILP=0 (skipped)"
        log(f"  n={n:<4d} {k + 1:>3d}/{count} tau={tau:<5} gaps: {gaps} | optimize {rec['runtime_ms']['annealing_local_search']:.0f} ms, "
            f"ilp {rec['runtime_ms']['ilp']:.0f} ms ({rec['ilp_status']})")
    return records


def parse_sizes(spec: str) -> list[int]:
    sizes = [int(s) for s in spec.split(",") if s.strip()]
    if not sizes or any(s < 1 for s in sizes):
        raise argparse.ArgumentTypeError("--sizes needs a comma-separated list of positive integers")
    return sizes


def parse_counts(spec: str, sizes: list[int]) -> dict[int, int]:
    counts = [int(s) for s in spec.split(",") if s.strip()]
    if len(counts) == 1:
        counts = counts * len(sizes)
    if len(counts) != len(sizes) or any(c < 0 for c in counts):
        raise argparse.ArgumentTypeError("--instances-per-size needs one count or one count per size")
    return dict(zip(sizes, counts, strict=True))


def summary_table(result: dict) -> str:
    lines = [f"{'n':>5} {'tau':>5} {'inst':>4}  {'method':<24}{'optimal':>8}{'mean gap':>10}{'p95 gap':>9}{'max gap':>9}{'mean ms':>10}{'max ms':>10}"]

    def rows(label_n: str, label_tau: str, agg: dict) -> None:
        for m, e in agg["methods"].items():
            share = f"{100 * e['optimal_share']:.1f}%" if "optimal_share" in e else "ref"
            gaps = [f"{e[key]:.3f}%" if key in e else "-" for key in ("mean_gap_pct", "p95_gap_pct", "max_gap_pct")]
            ms = [f"{e[key]:.1f}" if e.get(key) is not None else "-" for key in ("mean_runtime_ms", "max_runtime_ms")]
            lines.append(f"{label_n:>5} {label_tau:>5} {agg['instances']:>4}  {m:<24}{share:>8}{gaps[0]:>10}{gaps[1]:>9}{gaps[2]:>9}{ms[0]:>10}{ms[1]:>10}")

    for n, agg in result["by_size"].items():
        rows(n, "all", agg)
        for tau, tagg in agg["by_tau"].items():
            rows(n, tau, tagg)
    for tau, tagg in result["by_tau"].items():
        rows("all", tau, tagg)
    return "\n".join(lines)


def dump_json(result: dict, path: Path) -> None:
    """indent=2 for the aggregates, one line per raw instance record so the file stays small and diff-friendly."""
    records = result["instances"]
    text = json.dumps({**result, "instances": "@@INSTANCES@@"}, indent=2)
    separator = ",\n    "
    body = f"[\n    {separator.join(json.dumps(r) for r in records)}\n  ]" if records else "[]"
    path.write_text(text.replace('"@@INSTANCES@@"', body), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sizes", type=parse_sizes, default="20,50,100,200", help="comma-separated portfolio sizes n")
    ap.add_argument("--instances-per-size", default="50", help="one count for all sizes, or one count per size (comma-separated)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--small-check", type=int, default=100, help="number of n in [3, 14] instances on which ILP must equal the exhaustive optimum")
    ap.add_argument("--ilp-time-limit", type=float, default=DEFAULT_TIME_LIMIT_S, help="HiGHS time limit per instance in seconds")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "qiro_scalability.json")
    args = ap.parse_args(argv)
    sizes: list[int] = args.sizes  # argparse applies parse_sizes to the string default as well
    counts = parse_counts(args.instances_per_size, sizes)

    def log(msg: str) -> None:
        print(msg, file=sys.stderr, flush=True)

    t_start = time.perf_counter()
    solver = solver_name()
    log(f"qiro_scalability: {solver}; sizes {sizes}; instances per size {counts}; seed {args.seed}")

    log(f"small check: {args.small_check} instances with n in [3, {qiro.EXACT_SOLVER_MAX_N}] (ILP vs exhaustive)")
    check = small_check(args.seed, args.small_check, args.ilp_time_limit)
    log(f"  agreeing {check['agreeing']}/{check['instances']} (max |diff| {check['max_abs_diff']:g})")
    if not check["passed"]:
        log(f"ILP model disagrees with the exhaustive optimum on {len(check['mismatches'])} instance(s): {check['mismatches']}")
        return 1

    records: list[dict] = []
    by_size: dict[str, Any] = {}
    for n in sizes:
        if counts[n] == 0:
            continue
        log(f"size n={n}: {counts[n]} instances")
        size_records = run_size(n, counts[n], args.seed, args.ilp_time_limit, log)
        iterations = sorted({r["iterations_run"] for r in size_records})
        agg = aggregate(size_records)
        agg["iterations_run"] = iterations[0] if len(iterations) == 1 else iterations
        agg["by_tau"] = by_tau(size_records)
        by_size[str(n)] = agg
        records.extend(size_records)
        m = agg["methods"]
        log(f"  summary n={n}: optimal share greedy {m['greedy']['optimal_share']:.3f} | greedy+LS {m['greedy_local_search']['optimal_share']:.3f} | "
            f"SA {m['annealing']['optimal_share']:.3f} | SA+LS {m['annealing_local_search']['optimal_share']:.3f}; "
            f"mean gap SA+LS {m['annealing_local_search']['mean_gap_pct']:.4f}%; mean ms optimize {m['annealing_local_search']['mean_runtime_ms']:.1f} "
            f"vs ILP {m['ilp']['mean_runtime_ms']:.1f}")

    result = {
        "benchmark": "qiro_scalability_vs_ilp",
        "software_version": __version__,
        "qiro_version": qiro.QIRO_VERSION,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "solver": solver,
        "seed": args.seed,
        "sizes": sizes,
        "instances_per_size": {str(n): counts[n] for n in sizes},
        "total_instances": len(records),
        "total_runtime_s": round(time.perf_counter() - t_start, 1),
        "generator": generator_description(records),
        "method": method_description(args.ilp_time_limit),
        "small_check": check,
        "by_size": by_size,
        "by_tau": by_tau(records),
        # Raw per-instance records (action_ranges are only kept in aggregated form under "generator").
        "instances": [{k: v for k, v in r.items() if k != "action_ranges"} for r in records],
        "caveat": (
            "Synthetic random instances drawn from the illustrative remediation catalogue (placeholder costs, downtime and "
            "complexity values); not real hospital data. Runtimes are single-machine wall-clock measurements."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    dump_json(result, args.out)
    print(summary_table(result))
    print(f"\nsmall check: {check['agreeing']}/{check['instances']} ILP == exhaustive; total runtime {result['total_runtime_s']} s; written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
