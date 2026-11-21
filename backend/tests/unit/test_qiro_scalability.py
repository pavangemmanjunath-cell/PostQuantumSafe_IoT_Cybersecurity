"""Scalability benchmark helpers: HiGHS ILP reference vs. exhaustive optimum, generator determinism, script run.

The benchmark modules live in ``benchmarks/`` (outside the package) and need the optional ``highspy`` extra.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

from safeguard_pq.optimizer import qiro

pytest.importorskip("highspy")

BENCHMARKS_DIR = Path(__file__).resolve().parents[3] / "benchmarks"
if str(BENCHMARKS_DIR) not in sys.path:
    sys.path.insert(0, str(BENCHMARKS_DIR))

import qiro_scalability  # noqa: E402
from _ilp import ilp_optimum  # noqa: E402


def small_instance(seed: int) -> tuple[list[dict], float, float]:
    """n in [3, 10]; even seeds use the tightness generator, odd seeds the fixed levels of qiro_optimality."""
    rng = random.Random(seed)
    n = rng.randint(3, 10)
    if seed % 2 == 0:
        findings, budget, max_dt, _tau = qiro_scalability.instance(rng, n)
    else:
        findings = qiro_scalability.findings_for(rng, n)
        budget, max_dt = rng.choice([20_000, 50_000, 100_000]), rng.choice([4, 10, 40])
    return qiro.build_actions(findings), budget, max_dt


@pytest.mark.parametrize("seed", range(25))
def test_ilp_equals_exhaustive_optimum(seed: int) -> None:
    actions, budget, max_dt = small_instance(seed)
    exact = qiro.exact_optimum(actions, budget, max_dt)
    res = ilp_optimum(actions, budget, max_dt)
    assert res["status"] == "Optimal"
    assert abs(res["objective"] - exact) <= 1e-6


@pytest.mark.parametrize("seed", range(5))
def test_ilp_objective_is_qiro_objective_of_its_selection(seed: int) -> None:
    findings, budget, max_dt, _tau = qiro_scalability.instance(random.Random(100 + seed), 40)
    actions = qiro.build_actions(findings)
    res = ilp_optimum(actions, budget, max_dt)
    assert len(res["selection"]) == 40 and set(res["selection"]) <= {0, 1}
    assert res["objective"] == qiro.objective(res["selection"], actions, budget, max_dt)
    cost, dt = qiro._totals(res["selection"], actions)
    assert cost <= budget and dt <= max_dt
    assert res["solve_ms"] >= 0
    # The shipped heuristic can never beat a proven optimum of the same objective.
    assert qiro.optimize(findings, budget, max_dt, seed=seed)["optimality"]["heuristic_objective"] <= res["objective"] + 1e-9


def test_ilp_empty_portfolio() -> None:
    assert ilp_optimum([], 1000, 10) == {"objective": 0.0, "selection": [], "status": "Optimal", "solve_ms": 0.0}


def test_generator_is_deterministic_for_a_seed() -> None:
    first = [qiro_scalability.instance(random.Random(7), n) for n in (5, 20, 50)]
    second = [qiro_scalability.instance(random.Random(7), n) for n in (5, 20, 50)]
    assert first == second
    assert [qiro_scalability.instance(qiro_scalability.size_rng(0, 20), 20) for _ in range(2)] == [
        qiro_scalability.instance(qiro_scalability.size_rng(0, 20), 20) for _ in range(2)
    ]
    findings, budget, max_dt, tau = first[1]
    assert len(findings) == 20 and tau in qiro_scalability.TAUS
    actions = qiro.build_actions(findings)
    assert budget == tau * sum(a["cost_usd"] for a in actions)
    assert max_dt == tau * sum(a["downtime_hrs"] for a in actions)
    assert qiro_scalability.instance(random.Random(8), 20) != first[1]


def test_script_runs_end_to_end(tmp_path: Path) -> None:
    out = tmp_path / "qiro_scalability.json"
    argv = ["--sizes", "20", "--instances-per-size", "2", "--small-check", "3", "--seed", "1", "--out", str(out)]
    assert qiro_scalability.main(argv) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["benchmark"] == "qiro_scalability_vs_ilp"
    assert data["solver"].startswith("HiGHS") and data["seed"] == 1
    assert data["small_check"]["passed"] and data["small_check"]["agreeing"] == 3
    assert data["instances_per_size"] == {"20": 2} and len(data["instances"]) == 2
    size = data["by_size"]["20"]
    assert size["instances"] == 2 and size["iterations_run"] == min(3000, 200 + 20 * 80)
    for method in ("greedy", "greedy_local_search", "annealing", "annealing_local_search"):
        assert 0 <= size["methods"][method]["optimal_share"] <= 1
        assert size["methods"][method]["mean_gap_pct"] >= 0
    assert size["methods"]["ilp"]["statuses"] == {"Optimal": 2}
    assert set(size["by_tau"]) <= {"0.25", "0.5", "0.75"}
    assert "gap_formula" in data["method"] and "tau_values" in data["generator"]["constraint_tightness"]
