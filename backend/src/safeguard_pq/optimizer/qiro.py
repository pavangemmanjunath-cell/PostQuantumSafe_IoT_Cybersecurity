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

Two planner modes share the same search:

* ``independent_actions`` (default, the shipped behaviour): one decision
  variable per finding. Findings that share a root cause are planned, costed
  and credited separately, so the planner's summed benefit can diverge from
  the effect of actually remediating (see ``optimizer/reassess.py``).
* ``shared_root_cause`` (``group_shared_root_causes=True``): actions whose
  remediation is the same simulator mitigation are merged into one composite
  decision unit, because one mitigation removes all of them. The unit is
  costed once (max cost / downtime / complexity of its members) and credited
  with the summed benefit. Selected units are expanded back to per-finding
  actions so every downstream consumer is unchanged. The one cross-unit
  dependency grounded in the mitigation catalogue (``enable_hybrid_mlkem``
  already sets TLS 1.3, the TLS-version part of ``upgrade_tls13``) is
  recorded; no further dependencies are invented.

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
SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
PILLAR_WEIGHTS = {"Trust": 1.0, "Identity": 1.0, "Privacy": 1.2, "Protection": 1.0, "Safety": 1.4, "Security": 1.0}
PQ_FINDING_TYPES = {
    "classical_key_exchange", "classical_signature", "classical_certificate_key", "deprecated_tls_version",
    "weak_hash", "long_lifetime_classical_crypto", "pq_migration_required", "mosca_hndl_exposure",
}
PQ_AGENTS = {"pq_identification"}

MODE_INDEPENDENT = "independent_actions"
MODE_SHARED = "shared_root_cause"

# The only dependency between mitigations that the simulator catalogue grounds: the config of ``enable_hybrid_mlkem``
# already sets ``tls_version`` to TLS1.3, which is what the ``deprecated_tls_version`` member of ``upgrade_tls13``
# needs (the cipher part of ``upgrade_tls13``, AES-256-GCM, is independent).
IMPLIED_PARTS: dict[str, dict[str, Any]] = {
    "upgrade_tls13": {"implied_by": "enable_hybrid_mlkem", "config": ("tls_version",), "finding_types": ("deprecated_tls_version",)},
}

_EXCLUDED_KEYS = (
    "id", "finding_index", "finding_id", "finding_type", "severity", "device_id", "description", "remediation",
    "mitigation", "risk_reduction", "cost_usd", "downtime_hrs", "pqc_urgency", "safety_criticality",
    "tippss_weight", "tippss_pillars", "optimization_benefit")


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


def group_actions(actions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge actions that share a simulator mitigation into composite decision units (shared root causes).

    A unit is costed once — max cost, downtime and complexity of its members, i.e. the most expensive member's
    template — and credited with the members' summed risk reduction and benefit. Actions without a mitigation
    stay singleton units. The catalogue-grounded dependency in ``IMPLIED_PARTS`` is recorded on the implied unit.
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    for a in actions:
        buckets.setdefault(a["mitigation"] or f"__single__{a['id']}", []).append(a)
    units: list[dict[str, Any]] = []
    for gi, members in enumerate(buckets.values(), start=1):
        cost = max(m["cost_usd"] for m in members)
        dt = max(m["downtime_hrs"] for m in members)
        complexity = max(m["complexity"] for m in members)
        benefit = sum(m["optimization_benefit"] for m in members)
        units.append({
            "id": f"G{gi}",
            "mitigation": members[0]["mitigation"],
            "member_action_ids": [m["id"] for m in members],
            "finding_ids": [m["finding_id"] for m in members],
            "finding_types": [m["finding_type"] for m in members],
            "members": members,
            "severity": min((m["severity"] for m in members), key=lambda s: SEV_RANK.get(s, 9)),
            "risk_reduction": sum(m["risk_reduction"] for m in members),
            "cost_usd": cost,
            "downtime_hrs": dt,
            "complexity": complexity,
            "pqc_urgency": max(m["pqc_urgency"] for m in members),
            "safety_criticality": max(m["safety_criticality"] for m in members),
            "tippss_weight": sum(m["tippss_weight"] for m in members),
            "tippss_pillars": list(dict.fromkeys(p for m in members for p in m["tippss_pillars"])),
            "optimization_benefit": benefit,
            "value_density": float(f"{benefit / max(1, cost / 1000 + dt * 2 + complexity):.3f}"),
        })
    by_mitigation = {u["mitigation"]: u for u in units if u["mitigation"]}
    for implied, dep in IMPLIED_PARTS.items():
        if implied not in by_mitigation or dep["implied_by"] not in by_mitigation:
            continue
        unit, source = by_mitigation[implied], by_mitigation[dep["implied_by"]]
        part = [m for m in unit["members"] if m["finding_type"] in dep["finding_types"]]
        unit.update({
            "implied_by": source["id"],
            "implied_by_mitigation": dep["implied_by"],
            "implied_config": list(dep["config"]),
            "implied_finding_ids": [m["finding_id"] for m in part],
            "implied_benefit": sum(m["optimization_benefit"] for m in part),
            "dependency_note": (
                f"{dep['implied_by']} already sets {', '.join(dep['config'])} to the value {implied} would set, so the "
                f"{'/'.join(dep['finding_types'])} part of {unit['id']} is fixed as a side effect whenever {source['id']} is "
                f"applied. Both units are kept (the rest of {implied} is independent); the overlapping benefit is reported "
                "in implied_benefit and removed once in dependency_adjusted_benefit so it is not double-counted."),
        })
    return units


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


def _search(units: Sequence[dict], budget: float, max_dt: float, seed: int) -> dict[str, Any]:
    """Greedy value-density start, seeded simulated annealing over feasible moves, deterministic local-search polish."""
    rng = random.Random(seed)
    n = len(units)
    iterations = min(3000, 200 + n * 80)
    temperature, cooling = 100.0, 0.995

    current = [0] * n
    run_cost = run_dt = 0.0
    for i in sorted(range(n), key=lambda k: -units[k]["value_density"]):
        if run_cost + units[i]["cost_usd"] <= budget and run_dt + units[i]["downtime_hrs"] <= max_dt:
            current[i] = 1
            run_cost += units[i]["cost_usd"]
            run_dt += units[i]["downtime_hrs"]
    greedy_score = objective(current, units, budget, max_dt)
    current_score = greedy_score
    best, best_score = list(current), current_score
    accepted = 0

    for _ in range(iterations):
        idx = rng.randrange(n)
        neighbor = list(current)
        neighbor[idx] = 1 - neighbor[idx]
        cost, dt = _totals(neighbor, units)
        feasible = cost <= budget and dt <= max_dt
        neighbor_score = objective(neighbor, units, budget, max_dt)
        delta = neighbor_score - current_score
        if feasible and (delta > 0 or rng.random() < math.exp(delta / temperature)):
            current, current_score = neighbor, neighbor_score
            accepted += 1
            if current_score > best_score:
                best, best_score = list(current), current_score
        temperature *= cooling

    sa_score = best_score
    best, best_score, polish_moves = _local_search(best, units, budget, max_dt)
    return {"selection": best, "score": best_score, "annealing_score": sa_score, "greedy_score": greedy_score,
            "polish_moves": polish_moves, "accepted": accepted, "iterations": iterations, "temperature": temperature}


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


def _exclusion_reason(cost: float, dt: float, budget: float, max_dt: float, rem_budget: float, rem_dt: float, *,
                      single: str = "this single action", it: str = "it") -> str:
    reason = "Lower optimization priority than selected actions under the current constraints."
    if cost > budget:
        reason = f"Not selected because {single} exceeds the total available budget."
    elif dt > max_dt:
        reason = f"Not selected because {single} exceeds the allowed service downtime."
    elif cost > rem_budget and dt > rem_dt:
        reason = f"Not selected because {it} exceeds the remaining budget and remaining downtime after higher-priority actions."
    elif cost > rem_budget:
        reason = f"Not selected because {it} exceeds the remaining budget after higher-priority actions."
    elif dt > rem_dt:
        reason = f"Not selected because {it} exceeds the remaining downtime after higher-priority actions."
    return reason


def _rank(selected: list[dict]) -> None:
    selected.sort(
        key=lambda a: -(a["pqc_urgency"] + a["safety_criticality"] + SEV_MULT.get(a["severity"], 0.5) * 100 + a["tippss_weight"])
    )
    for rank, a in enumerate(selected, start=1):
        a["priority_rank"] = rank
        a["selection_reason"] = _selection_reason(a)


def _phases(selected: list[dict]) -> dict[str, list[dict]]:
    # Phases partition the selected actions (correction vs v0, where items could appear twice or be dropped):
    # phase 1 = critical or PQ-urgent (max 5, by priority), phase 2 = remaining high/overflow, phase 3 = the rest.
    urgent = [a for a in selected if a["severity"] == "critical" or a["pqc_urgency"] >= 25]
    p1 = urgent[:5]
    p1_ids = {a["id"] for a in p1}
    p2 = [a for a in selected if a["id"] not in p1_ids and (a["severity"] == "high" or a in urgent)]
    p2_ids = {a["id"] for a in p2}
    return {
        "phase_1_immediate_0_6mo": p1,
        "phase_2_transitional_6_18mo": p2,
        "phase_3_full_pq_18_36mo": [a for a in selected if a["id"] not in p1_ids | p2_ids],
    }


def _constraint_explanation(n_selected: int, n: int, n_excluded: int, budget: float, max_dt: float) -> str:
    b, d = fmt_money(budget), fmt_num(max_dt)
    if n_selected == n:
        return f"QIRO selected all {n} remediation actions because they fit within the available budget of ${b} and allowed downtime of {d}h."
    if not n_selected:
        return f"QIRO selected no actions because none of the candidate remediations fit within the available budget of ${b} and allowed downtime of {d}h."
    return (
        f"QIRO selected {n_selected} of {n} actions that maximize risk reduction, PQ urgency, safety impact, and TIPPSS "
        f"improvement while staying within the available budget of ${b} and allowed downtime of {d}h. "
        f"{n_excluded} actions were deferred because of budget, downtime, or lower optimization priority."
    )


def _optimality(units: Sequence[dict], budget: float, max_dt: float, s: dict[str, Any]) -> dict[str, Any]:
    exact = exact_optimum(units, budget, max_dt)
    return {
        "heuristic_objective": round(s["score"], 3),
        "annealing_objective": round(s["annealing_score"], 3),
        "local_search_moves": s["polish_moves"],
        "greedy_objective": round(s["greedy_score"], 3),
        "exact_objective": None if exact is None else round(exact, 3),
        "gap_pct": None if exact in (None, 0) else round(100 * (exact - s["score"]) / exact, 3),
        "exact_solver": f"exhaustive search (n ≤ {EXACT_SOLVER_MAX_N})" if exact is not None else f"skipped (n > {EXACT_SOLVER_MAX_N})",
        "accepted_moves": s["accepted"],
    }


def _empty(budget: float, max_dt: float, mode: str) -> dict[str, Any]:
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
        "planner_mode": mode,
        "root_cause_groups": [],
    }


def _assemble(*, units: Sequence[dict], n_actions: int, selected: list[dict], excluded: list[dict], budget: float, max_dt: float,
              seed: int, search: dict[str, Any], total_cost: float, total_dt: float, total_rr: float, explanation: str,
              message: str, mode: str, groups: list[dict], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    rem_budget = max(0.0, budget - total_cost)
    rem_dt = max(0.0, max_dt - total_dt)
    return {
        "algorithm": ALGORITHM,
        "qiro_version": QIRO_VERSION,
        "seed": seed,
        "iterations_run": search["iterations"],
        "final_temperature": f"{search['temperature']:.4f}",
        "optimization_score": js_round(search["score"]),
        "objective": "Maximize risk reduction + PQ urgency + safety criticality + TIPPSS impact − complexity, s.t. budget and downtime.",
        "total_candidate_actions": n_actions,
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
        "migration_phase_plan": _phases(selected),
        "constraint_explanation": explanation,
        "status": "optimized",
        "optimality": _optimality(units, budget, max_dt, search),
        "message": message,
        "planner_mode": mode,
        "root_cause_groups": groups,
        **(extra or {}),
    }


def _optimize_independent(actions: list[dict], budget: float, max_dt: float, seed: int) -> dict[str, Any]:
    n = len(actions)
    s = _search(actions, budget, max_dt, seed)
    best = s["selection"]
    selected = [dict(actions[i]) for i in range(n) if best[i]]
    total_cost = sum(a["cost_usd"] for a in selected)
    total_dt = sum(a["downtime_hrs"] for a in selected)
    total_rr = sum(a["risk_reduction"] for a in selected)
    _rank(selected)

    sel_ids = {a["id"] for a in selected}
    rem_budget = max(0.0, budget - total_cost)
    rem_dt = max(0.0, max_dt - total_dt)
    excluded = [
        {**{k: a[k] for k in _EXCLUDED_KEYS},
         "reason": _exclusion_reason(a["cost_usd"], a["downtime_hrs"], budget, max_dt, rem_budget, rem_dt)}
        for a in actions if a["id"] not in sel_ids]

    explanation = _constraint_explanation(len(selected), n, len(excluded), budget, max_dt)
    message = (
        f"QIRO selected {len(selected)} of {n} candidate remediation actions, achieving {total_rr} total risk reduction "
        f"within ${fmt_money(total_cost)} cost and {fmt_num(total_dt)}h downtime. Budget remaining: ${fmt_money(rem_budget)}; "
        f"downtime remaining: {fmt_num(rem_dt)}h."
    )
    return _assemble(units=actions, n_actions=n, selected=selected, excluded=excluded, budget=budget, max_dt=max_dt, seed=seed,
                     search=s, total_cost=total_cost, total_dt=total_dt, total_rr=total_rr, explanation=explanation,
                     message=message, mode=MODE_INDEPENDENT, groups=[])


def _group_view(u: dict[str, Any], selected: bool) -> dict[str, Any]:
    view = {
        "group_id": u["id"], "mitigation": u["mitigation"], "finding_ids": u["finding_ids"], "finding_types": u["finding_types"],
        "member_action_ids": u["member_action_ids"], "cost_usd": u["cost_usd"], "downtime_hrs": u["downtime_hrs"],
        "complexity": u["complexity"], "risk_reduction": u["risk_reduction"], "optimization_benefit": u["optimization_benefit"],
        "selected": selected,
    }
    for k in ("implied_by", "implied_by_mitigation", "implied_config", "implied_finding_ids", "implied_benefit", "dependency_note"):
        if k in u:
            view[k] = u[k]
    return view


def _optimize_grouped(actions: list[dict], budget: float, max_dt: float, seed: int) -> dict[str, Any]:
    n = len(actions)
    units = group_actions(actions)
    s = _search(units, budget, max_dt, seed)
    chosen = [u for i, u in enumerate(units) if s["selection"][i]]
    chosen_ids = {u["id"] for u in chosen}
    by_id = {u["id"]: u for u in units}

    selected = [{**m, "root_cause_group": u["id"], "group_cost_usd": u["cost_usd"], "group_downtime_hrs": u["downtime_hrs"]}
                for u in chosen for m in u["members"]]
    total_cost = sum(u["cost_usd"] for u in chosen)
    total_dt = sum(u["downtime_hrs"] for u in chosen)
    total_rr = sum(u["risk_reduction"] for u in chosen)
    _rank(selected)
    for a in selected:
        u = by_id[a["root_cause_group"]]
        if len(u["members"]) > 1:
            others = ", ".join(i for i in u["member_action_ids"] if i != a["id"])
            a["selection_reason"] += f" Shares one root cause ({u['mitigation']}) with {others}; planned once as group {u['id']}."

    rem_budget = max(0.0, budget - total_cost)
    rem_dt = max(0.0, max_dt - total_dt)
    excluded = []
    for u in units:
        if u["id"] in chosen_ids:
            continue
        if len(u["members"]) > 1:
            subject = f"its shared-root-cause group {u['id']} ({u['mitigation']})"
            reason = _exclusion_reason(u["cost_usd"], u["downtime_hrs"], budget, max_dt, rem_budget, rem_dt, single=subject, it=subject)
        else:
            reason = _exclusion_reason(u["cost_usd"], u["downtime_hrs"], budget, max_dt, rem_budget, rem_dt)
        excluded += [{**{k: m[k] for k in _EXCLUDED_KEYS}, "reason": reason, "root_cause_group": u["id"]} for m in u["members"]]

    explanation = _constraint_explanation(len(selected), n, len(excluded), budget, max_dt) + (
        f" Findings that share one root cause were planned as {len(units)} group(s) ({len(chosen)} selected); cost, downtime "
        "and complexity are counted once per group (its most expensive member) and benefit is summed over the group."
    )
    message = (
        f"QIRO selected {len(selected)} of {n} candidate remediation actions ({len(chosen)} of {len(units)} shared root causes), "
        f"achieving {total_rr} total risk reduction within ${fmt_money(total_cost)} cost and {fmt_num(total_dt)}h downtime "
        f"(counted once per root cause). Budget remaining: ${fmt_money(rem_budget)}; downtime remaining: {fmt_num(rem_dt)}h."
    )
    groups = [_group_view(u, u["id"] in chosen_ids) for u in units]
    dependencies = [
        {"group_id": u["id"], "mitigation": u["mitigation"], "implied_by": u["implied_by"],
         "implied_by_mitigation": u["implied_by_mitigation"], "shared_config": u["implied_config"],
         "implied_finding_ids": u["implied_finding_ids"], "implied_benefit": u["implied_benefit"],
         "both_selected": u["id"] in chosen_ids and u["implied_by"] in chosen_ids, "note": u["dependency_note"]}
        for u in units if "implied_by" in u]
    summed_benefit = sum(a["optimization_benefit"] for a in selected)
    double_counted = sum(d["implied_benefit"] for d in dependencies if d["both_selected"])
    return _assemble(units=units, n_actions=n, selected=selected, excluded=excluded, budget=budget, max_dt=max_dt, seed=seed,
                     search=s, total_cost=total_cost, total_dt=total_dt, total_rr=total_rr, explanation=explanation,
                     message=message, mode=MODE_SHARED, groups=groups,
                     extra={"root_cause_dependencies": dependencies, "dependency_adjusted_benefit": summed_benefit - double_counted})


def optimize(findings: Sequence[dict[str, Any]], budget: float, max_dt: float, seed: int, *,
             group_shared_root_causes: bool = False) -> dict[str, Any]:
    """Plan remediation under budget and downtime.

    ``group_shared_root_causes=False`` (default) is the shipped independent-actions planner and its output is
    unchanged. ``True`` merges actions that share a mitigation into one decision unit (see module docstring);
    selected and excluded actions are still reported per finding, annotated with ``root_cause_group``.
    """
    budget, max_dt = float(budget), float(max_dt)
    actions = build_actions(findings)
    mode = MODE_SHARED if group_shared_root_causes else MODE_INDEPENDENT
    if not actions:
        return _empty(budget, max_dt, mode)
    if group_shared_root_causes:
        return _optimize_grouped(actions, budget, max_dt, seed)
    return _optimize_independent(actions, budget, max_dt, seed)
