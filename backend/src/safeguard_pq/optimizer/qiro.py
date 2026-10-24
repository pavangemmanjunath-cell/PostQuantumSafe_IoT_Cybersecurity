"""QIRO — Quantum-Inspired Remediation Optimizer.

Problem: choose a subset of remediation actions (x_i ∈ {0,1}) that maximises

    f(x) = Σ B_i x_i − 0.5 Σ K_i x_i            (benefit minus complexity)

subject to   Σ C_i x_i ≤ budget   and   Σ D_i x_i ≤ max_downtime.

This is a two-constraint 0/1 knapsack problem. QIRO solves it with a greedy
value-density start followed by simulated annealing (Kirkpatrick et al.,
1983) that only accepts feasible moves. "Quantum-inspired" refers to the
Ising/QUBO-style energy formulation; no quantum hardware is used. For small
instances the exact optimum is also computed so the optimality gap of the
heuristic is reported rather than assumed.

The scoring constants reproduce the v0 prototype. A seeded RNG makes results
reproducible.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

from ..knowledge.remediation import template_for

ALGORITHM = "Simulated annealing over a QUBO-style energy + deterministic local-search polish (quantum-inspired; classical CPU)"
QIRO_VERSION = "2.1.0"
EXACT_SOLVER_MAX_N = 14

SEV_MULT = {"critical": 1.5, "high": 1.0, "medium": 0.6, "low": 0.3}
PILLAR_WEIGHTS = {"Trust": 1.0, "Identity": 1.0, "Privacy": 1.2, "Protection": 1.0, "Safety": 1.4, "Security": 1.0}
PQ_FINDING_TYPES = {
    "classical_key_exchange", "classical_signature", "classical_certificate_key", "deprecated_tls_version",
    "weak_hash", "long_lifetime_classical_crypto", "pq_migration_required", "mosca_hndl_exposure",
}
PQ_AGENTS = {"pq_identification"}


def js_round(x: float) -> int:
    """JavaScript Math.round semantics (half rounds toward +∞)."""
    return math.floor(x + 0.5)


def fmt_money(x: float) -> str:
    return f"{x:,.0f}"


def fmt_num(x: float) -> str:
    return f"{int(x)}" if float(x).is_integer() else f"{x:g}"


def build_actions(findings: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for idx, f in enumerate(findings):
        t = template_for(f["type"])
        sev_mult = SEV_MULT.get(f.get("severity"), 0.5)
        pillars = list(f.get("tippss_mapping") or [])
        tippss_weight = sum(PILLAR_WEIGHTS.get(p, 1) for p in pillars)
        is_pq = f.get("agent") in PQ_AGENTS or f["type"] in PQ_FINDING_TYPES
        is_safety = "Safety" in pillars
        risk_reduction = js_round(t.base_risk_reduction * sev_mult)
        benefit = risk_reduction + (25 if is_pq else 0) + (20 if is_safety else 0) + js_round(tippss_weight * 10)
        density = benefit / max(1, t.cost / 1000 + t.downtime * 2 + t.complexity)
        actions.append({
            "id": f"A{idx + 1}",
            "finding_index": idx,
            "finding_id": f.get("id"),
            "finding_type": f["type"],
            "severity": f.get("severity"),
            "source_agent": f.get("agent"),
            "device_id": f.get("device_id"),
            "description": f.get("detail"),
            "remediation": t.remediation,
            "mitigation": t.mitigation,
            "risk_reduction": risk_reduction,
            "cost_usd": t.cost,
            "downtime_hrs": t.downtime,
            "complexity": t.complexity,
            "pqc_urgency": 25 if is_pq else 0,
            "safety_criticality": 20 if is_safety else 0,
            "tippss_weight": js_round(tippss_weight * 10),
            "tippss_pillars": pillars,
            "optimization_benefit": benefit,
            "value_density": float(f"{density:.3f}"),
        })
    return actions


def objective(sel: Sequence[int], actions: Sequence[dict], budget: float, max_dt: float) -> float:
    cost = dt = benefit = complexity = 0.0
    for i, s in enumerate(sel):
        if s:
            a = actions[i]
            cost += a["cost_usd"]
            dt += a["downtime_hrs"]
            benefit += a["optimization_benefit"]
            complexity += a["complexity"] * 0.5
    penalty = 0.0
    if cost > budget:
        penalty += ((cost - budget) / 1000) * 100
    if dt > max_dt:
        penalty += (dt - max_dt) * 100
    return benefit - complexity - penalty


def _totals(sel: Sequence[int], actions: Sequence[dict]) -> tuple[float, float]:
    cost = dt = 0.0
    for i, s in enumerate(sel):
        if s:
            cost += actions[i]["cost_usd"]
            dt += actions[i]["downtime_hrs"]
    return cost, dt


def exact_optimum(actions: Sequence[dict], budget: float, max_dt: float) -> float | None:
    """Exhaustive search over feasible subsets (only for small N)."""
    n = len(actions)
    if n > EXACT_SOLVER_MAX_N:
        return None
    best = 0.0
    for mask in range(1 << n):
        cost = dt = val = 0.0
        ok = True
        for i in range(n):
            if mask >> i & 1:
                a = actions[i]
                cost += a["cost_usd"]
                dt += a["downtime_hrs"]
                if cost > budget or dt > max_dt:
                    ok = False
                    break
                val += a["optimization_benefit"] - a["complexity"] * 0.5
        if ok and val > best:
            best = val
    return best


def _local_search(sel: list[int], actions: Sequence[dict], budget: float, max_dt: float) -> tuple[list[int], float, int]:
    """Deterministic best-improvement polish over feasible add / drop / swap moves (never worsens the objective)."""
    sel = list(sel)
    score = objective(sel, actions, budget, max_dt)
    moves = 0
    n = len(sel)
    while True:
        best_move, best_val = None, score
        candidates = [(i,) for i in range(n)] + [(i, j) for i in range(n) if sel[i] for j in range(n) if not sel[j]]
        for mv in candidates:
            trial = list(sel)
            for k in mv:
                trial[k] = 1 - trial[k]
            cost, dt = _totals(trial, actions)
            if cost > budget or dt > max_dt:
                continue
            val = objective(trial, actions, budget, max_dt)
            if val > best_val + 1e-9:
                best_move, best_val = trial, val
        if best_move is None:
            return sel, score, moves
        sel, score, moves = best_move, best_val, moves + 1


def _selection_reason(a: dict) -> str:
    reasons = []
    if a["severity"] == "critical":
        reasons.append("critical severity")
    if a["pqc_urgency"] > 0:
        reasons.append("post-quantum migration urgency")
    if a["safety_criticality"] > 0:
        reasons.append("clinical safety impact")
    if a["tippss_weight"] >= 30:
        reasons.append("high TIPPSS impact")
    if a["cost_usd"] <= 10000:
        reasons.append("low-cost quick win")
    if not reasons:
        reasons.append("best optimization value under current constraints")
    return f"Selected because of {', '.join(reasons)}."


def _empty(budget: float, max_dt: float) -> dict[str, Any]:
    return {
        "algorithm": ALGORITHM,
        "qiro_version": QIRO_VERSION,
        "selected_actions": [],
        "excluded_actions": [],
        "total_candidate_actions": 0,
        "selection_count": 0,
        "excluded_count": 0,
        "total_cost_usd": 0,
        "total_downtime_hrs": 0,
        "total_risk_reduction": 0,
        "budget_constraint_usd": budget,
        "downtime_constraint_hrs": max_dt,
        "budget_remaining_usd": budget,
        "downtime_remaining_hrs": max_dt,
        "budget_utilization_pct": 0,
        "downtime_utilization_pct": 0,
        "status": "no_actions_needed",
        "constraint_explanation": "No remediation actions were needed because the system produced no findings.",
        "migration_phase_plan": {"phase_1_immediate_0_6mo": [], "phase_2_transitional_6_18mo": [], "phase_3_full_pq_18_36mo": []},
        "message": "No remediation actions required. System is already clean for the tested controls.",
        "optimality": None,
    }


def optimize(findings: Sequence[dict[str, Any]], budget: float, max_dt: float, seed: int) -> dict[str, Any]:
    budget, max_dt = float(budget), float(max_dt)
    actions = build_actions(findings)
    if not actions:
        return _empty(budget, max_dt)

    rng = random.Random(seed)
    n = len(actions)
    iterations = min(3000, 200 + n * 80)
    temperature, cooling = 100.0, 0.995

    # Greedy start: highest value density first while constraints hold.
    current = [0] * n
    run_cost = run_dt = 0.0
    for i in sorted(range(n), key=lambda k: -actions[k]["value_density"]):
        if run_cost + actions[i]["cost_usd"] <= budget and run_dt + actions[i]["downtime_hrs"] <= max_dt:
            current[i] = 1
            run_cost += actions[i]["cost_usd"]
            run_dt += actions[i]["downtime_hrs"]
    greedy_score = objective(current, actions, budget, max_dt)
    current_score = greedy_score
    best, best_score = list(current), current_score
    accepted = 0

    for _ in range(iterations):
        idx = rng.randrange(n)
        neighbor = list(current)
        neighbor[idx] = 1 - neighbor[idx]
        cost, dt = _totals(neighbor, actions)
        feasible = cost <= budget and dt <= max_dt
        neighbor_score = objective(neighbor, actions, budget, max_dt)
        delta = neighbor_score - current_score
        if feasible and (delta > 0 or rng.random() < math.exp(delta / temperature)):
            current, current_score = neighbor, neighbor_score
            accepted += 1
            if current_score > best_score:
                best, best_score = list(current), current_score
        temperature *= cooling

    sa_score = best_score
    best, best_score, polish_moves = _local_search(best, actions, budget, max_dt)

    selected = [dict(actions[i]) for i in range(n) if best[i]]
    total_cost = sum(a["cost_usd"] for a in selected)
    total_dt = sum(a["downtime_hrs"] for a in selected)
    total_rr = sum(a["risk_reduction"] for a in selected)

    selected.sort(
        key=lambda a: -(a["pqc_urgency"] + a["safety_criticality"] + SEV_MULT.get(a["severity"], 0.5) * 100 + a["tippss_weight"])
    )
    for rank, a in enumerate(selected, start=1):
        a["priority_rank"] = rank
        a["selection_reason"] = _selection_reason(a)

    sel_ids = {a["id"] for a in selected}
    rem_budget = max(0.0, budget - total_cost)
    rem_dt = max(0.0, max_dt - total_dt)
    excluded = []
    for a in actions:
        if a["id"] in sel_ids:
            continue
        reason = "Lower optimization priority than selected actions under the current constraints."
        if a["cost_usd"] > budget:
            reason = "Not selected because this single action exceeds the total available budget."
        elif a["downtime_hrs"] > max_dt:
            reason = "Not selected because this single action exceeds the allowed service downtime."
        elif a["cost_usd"] > rem_budget and a["downtime_hrs"] > rem_dt:
            reason = "Not selected because it exceeds the remaining budget and remaining downtime after higher-priority actions."
        elif a["cost_usd"] > rem_budget:
            reason = "Not selected because it exceeds the remaining budget after higher-priority actions."
        elif a["downtime_hrs"] > rem_dt:
            reason = "Not selected because it exceeds the remaining downtime after higher-priority actions."
        excluded.append({**{k: a[k] for k in (
            "id", "finding_index", "finding_id", "finding_type", "severity", "device_id", "description", "remediation",
            "mitigation", "risk_reduction", "cost_usd", "downtime_hrs", "pqc_urgency", "safety_criticality",
            "tippss_weight", "tippss_pillars", "optimization_benefit")}, "reason": reason})

    # Phases partition the selected actions (correction vs v0, where items could appear twice or be dropped):
    # phase 1 = critical or PQ-urgent (max 5, by priority), phase 2 = remaining high/overflow, phase 3 = the rest.
    urgent = [a for a in selected if a["severity"] == "critical" or a["pqc_urgency"] >= 25]
    p1 = urgent[:5]
    p1_ids = {a["id"] for a in p1}
    p2 = [a for a in selected if a["id"] not in p1_ids and (a["severity"] == "high" or a in urgent)]
    p2_ids = {a["id"] for a in p2}
    phases = {
        "phase_1_immediate_0_6mo": p1,
        "phase_2_transitional_6_18mo": p2,
        "phase_3_full_pq_18_36mo": [a for a in selected if a["id"] not in p1_ids | p2_ids],
    }

    b, d = fmt_money(budget), fmt_num(max_dt)
    if len(selected) == n:
        explanation = f"QIRO selected all {n} remediation actions because they fit within the available budget of ${b} and allowed downtime of {d}h."
    elif not selected:
        explanation = f"QIRO selected no actions because none of the candidate remediations fit within the available budget of ${b} and allowed downtime of {d}h."
    else:
        explanation = (
            f"QIRO selected {len(selected)} of {n} actions that maximize risk reduction, PQ urgency, safety impact, and TIPPSS "
            f"improvement while staying within the available budget of ${b} and allowed downtime of {d}h. "
            f"{len(excluded)} actions were deferred because of budget, downtime, or lower optimization priority."
        )

    exact = exact_optimum(actions, budget, max_dt)
    optimality = {
        "heuristic_objective": round(best_score, 3),
        "annealing_objective": round(sa_score, 3),
        "local_search_moves": polish_moves,
        "greedy_objective": round(greedy_score, 3),
        "exact_objective": None if exact is None else round(exact, 3),
        "gap_pct": None if exact in (None, 0) else round(100 * (exact - best_score) / exact, 3),
        "exact_solver": f"exhaustive search (n ≤ {EXACT_SOLVER_MAX_N})" if exact is not None else f"skipped (n > {EXACT_SOLVER_MAX_N})",
        "accepted_moves": accepted,
    }

    return {
        "algorithm": ALGORITHM,
        "qiro_version": QIRO_VERSION,
        "seed": seed,
        "iterations_run": iterations,
        "final_temperature": f"{temperature:.4f}",
        "optimization_score": js_round(best_score),
        "objective": "Maximize risk reduction + PQ urgency + safety criticality + TIPPSS impact − complexity, s.t. budget and downtime.",
        "total_candidate_actions": n,
        "selected_actions": selected,
        "excluded_actions": excluded,
        "selection_count": len(selected),
        "excluded_count": len(excluded),
        "budget_constraint_usd": budget,
        "downtime_constraint_hrs": max_dt,
        "total_cost_usd": total_cost,
        "total_downtime_hrs": total_dt,
        "budget_remaining_usd": rem_budget,
        "downtime_remaining_hrs": rem_dt,
        "budget_utilization_pct": js_round(total_cost / budget * 100) if budget > 0 else 0,
        "downtime_utilization_pct": js_round(total_dt / max_dt * 100) if max_dt > 0 else 0,
        "total_risk_reduction": total_rr,
        "migration_phase_plan": phases,
        "constraint_explanation": explanation,
        "status": "optimized",
        "optimality": optimality,
        "message": (
            f"QIRO selected {len(selected)} of {n} candidate remediation actions, achieving {total_rr} total risk reduction "
            f"within ${fmt_money(total_cost)} cost and {fmt_num(total_dt)}h downtime. Budget remaining: ${fmt_money(rem_budget)}; "
            f"downtime remaining: {fmt_num(rem_dt)}h."
        ),
    }
