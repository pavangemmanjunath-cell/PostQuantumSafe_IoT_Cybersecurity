"""Integer-programming reference optimum for the QIRO objective (HiGHS MIP via ``highspy``).

Solves exactly the two-constraint 0/1 knapsack that ``safeguard_pq.optimizer.qiro`` approximates:

    max  Σ B_i x_i − 0.5 Σ K_i x_i          (B = optimization_benefit, K = complexity)
    s.t. Σ C_i x_i ≤ budget,  Σ D_i x_i ≤ max_downtime,  x_i ∈ {0, 1}

On a feasible selection this is the same number as ``qiro.objective`` (whose penalty term is zero
there), so the returned value is a valid optimum reference for the heuristic at any n. The solver is
run with zero MIP gap tolerances, so a model status of ``"Optimal"`` means proven optimality.

Research benchmarks only. ``highspy`` is an optional dependency::

    pip install -e 'backend[benchmark]'
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

try:
    import highspy
except ImportError as exc:  # pragma: no cover - only reachable without the optional extra
    raise ImportError(
        "The ILP benchmark baseline needs the HiGHS solver bindings (highspy), which are not installed. "
        "Install the optional benchmark extra: pip install -e 'backend[benchmark]'"
    ) from exc

# Zero gap tolerances: HiGHS must close the bound completely before reporting "Optimal".
SOLVER_OPTIONS: dict[str, Any] = {"mip_rel_gap": 0.0, "mip_abs_gap": 0.0}
DEFAULT_TIME_LIMIT_S = 300.0


def solver_name() -> str:
    """Human-readable solver identifier, e.g. ``HiGHS 1.16.0 via highspy``."""
    return f"HiGHS {highspy.Highs().version()} via highspy"


def ilp_optimum(
    actions: Sequence[dict[str, Any]], budget: float, max_dt: float, time_limit_s: float = DEFAULT_TIME_LIMIT_S
) -> dict[str, Any]:
    """Exact optimum of the QIRO objective for ``actions`` under the budget / downtime limits.

    Returns ``{"objective", "selection", "status", "solve_ms"}``:

    * ``objective`` - objective of the returned 0/1 selection, recomputed exactly with the ``qiro.objective``
      formula (Σ optimization_benefit − 0.5 Σ complexity over the selected actions);
    * ``selection`` - 0/1 vector aligned with ``actions``;
    * ``status`` - HiGHS model status string; ``"Optimal"`` means the optimum is proven, anything else
      (e.g. the time limit) means ``objective`` is only the best incumbent found;
    * ``solve_ms`` - wall-clock milliseconds for model construction plus the solve.
    """
    n = len(actions)
    budget, max_dt = float(budget), float(max_dt)
    if n == 0:
        return {"objective": 0.0, "selection": [], "status": "Optimal", "solve_ms": 0.0}

    t0 = time.perf_counter()
    h = highspy.Highs()
    h.silent()
    for key, value in SOLVER_OPTIONS.items():
        h.setOptionValue(key, value)
    h.setOptionValue("time_limit", float(time_limit_s))
    x = [h.addVariable(lb=0, ub=1, type=highspy.HighsVarType.kInteger) for _ in range(n)]
    h.addConstr(sum(a["cost_usd"] * x[i] for i, a in enumerate(actions)) <= budget)
    h.addConstr(sum(a["downtime_hrs"] * x[i] for i, a in enumerate(actions)) <= max_dt)
    # setObjective + run: Highs.maximize() would call solve() itself and run() would then solve twice.
    h.setObjective(
        sum((a["optimization_benefit"] - 0.5 * a["complexity"]) * x[i] for i, a in enumerate(actions)),
        highspy.ObjSense.kMaximize,
    )
    h.run()
    solve_ms = (time.perf_counter() - t0) * 1000

    status = h.modelStatusToString(h.getModelStatus())
    selection = [round(float(v)) for v in h.getSolution().col_value]  # round(float) -> int

    # Recompute the objective exactly on the rounded selection (same accumulation as qiro.objective).
    cost = dt = benefit = complexity = 0.0
    for a, s in zip(actions, selection, strict=True):
        if s:
            cost += a["cost_usd"]
            dt += a["downtime_hrs"]
            benefit += a["optimization_benefit"]
            complexity += a["complexity"] * 0.5
    if cost > budget or dt > max_dt:
        raise RuntimeError(f"HiGHS returned an infeasible selection (status {status!r}): cost {cost} / {budget}, downtime {dt} / {max_dt}")
    objective = benefit - complexity
    solver_objective = float(h.getObjectiveValue())
    if abs(solver_objective - objective) > 1e-6 * max(1.0, abs(objective)):
        raise RuntimeError(f"HiGHS objective {solver_objective} disagrees with the recomputed objective {objective} (status {status!r})")
    return {"objective": objective, "selection": selection, "status": status, "solve_ms": round(solve_ms, 3)}
