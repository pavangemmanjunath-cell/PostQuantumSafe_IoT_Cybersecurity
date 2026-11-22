"""Evaluate QIRO plans by reassessment on the ten built-in scenarios.

    python benchmarks/plan_reassessment.py --seed 2026 --exhaustive-max-n 10

Question: does the planner's projected risk reduction (summed benefits, and a projection that assumes each selected
action removes only its own finding) match the effect of remediation (the reassessed score)?
For every scenario this script

1. runs the baseline assessment;
2. builds plan A with the shipped planner (independent per-finding actions) and plan B with the shared-root-cause
   planner (actions whose remediation is the same mitigation are merged and costed once);
3. applies each plan to the configuration with ``safeguard_pq.optimizer.reassess`` — the "after" state is produced
   by code from the plan, not edited by hand — re-runs the pipeline and reports summed benefit, projected score and
   reassessed score independently;
4. for scenarios with at most ``--exhaustive-max-n`` candidate actions, enumerates every feasible subset, reassesses
   each one (one pipeline run per subset) and reports the best reassessed outcome the constraints allow, the cheapest
   subset reaching it, and whether plan A and plan B attain it (summarised separately for the ICU gateway scenario,
   ``icu_gateway_critical``). Plan A is checked against subsets of per-finding actions under the shipped cost
   accounting (every action paid); plan B against subsets of whole root-cause groups under the grouped accounting
   (each group paid once).

Synthetic scenarios; configuration-level reassessment only — network mitigations are reported as unmodelled.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.config import Settings  # noqa: E402
from safeguard_pq.domain.models import AssessmentRequest, AssessmentResult  # noqa: E402
from safeguard_pq.optimizer import qiro  # noqa: E402
from safeguard_pq.optimizer.reassess import (  # noqa: E402
    CAVEAT,
    METHOD,
    NETWORK_MITIGATIONS,
    evaluate_plan_by_reassessment,
    reassess,
)
from safeguard_pq.orchestrator import run_assessment  # noqa: E402
from safeguard_pq.scenarios import load_scenarios  # noqa: E402

STATUS_RANK = {"SAFE": 0, "AT_RISK": 1, "UNSAFE": 2}
ICU_GATEWAY_SCENARIO = "icu_gateway_critical"  # summarised in summary.icu_gateway_scenario


def outcome_key(score: int, status: str, remaining: int) -> tuple[int, int, int]:
    """Lower is better: PQ risk score, then environment status, then number of remaining findings."""
    return (score, STATUS_RANK.get(status, 3), remaining)


def plan_row(ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "planner_mode": ev["planner_mode"],
        "selected_action_ids": ev["selected_action_ids"],
        "selected_finding_ids": ev["selected_finding_ids"],
        "total_cost_usd": ev["total_cost_usd"],
        "total_downtime_hrs": ev["total_downtime_hrs"],
        "summed_benefit": ev["summed_benefit"],
        "total_risk_reduction": ev["total_risk_reduction"],
        "projected_pq_score": ev["projected_pq_score"],
        "projected_status": ev["projected_status"],
        "reassessed_pq_score": ev["reassessed_pq_score"],
        "reassessed_status": ev["reassessed_status"],
        "reassessed_verdict": ev["reassessed_verdict"],
        "projection_error": ev["projection_error"],
        "remaining_finding_types": ev["remaining_finding_types"],
        "applied_mitigations": ev["applied"]["applied_mitigations"],
        "unmodelled_mitigations": ev["applied"]["unmodelled_mitigations"],
        "changes": ev["applied"]["changes"],
        "notes": ev["applied"]["notes"],
    }


async def _row(req: AssessmentRequest, chosen: list[dict[str, Any]], cost: float, dt: float, settings: Settings,
               **extra: Any) -> dict[str, Any]:
    res, report = await reassess(req, chosen, settings=settings, seed=req.seed)
    return {"action_ids": [a["id"] for a in chosen], "mitigations": sorted({a["mitigation"] for a in chosen if a["mitigation"]}),
            "cost_usd": cost, "downtime_hrs": dt, "score": res.pq_risk_score, "status": res.environment_status,
            "remaining": res.findings_count, "unmodelled": report["unmodelled_mitigations"], **extra}


def _best(rows: list[dict[str, Any]], enumerated: int) -> dict[str, Any]:
    best = min(outcome_key(r["score"], r["status"], r["remaining"]) for r in rows)
    attaining = [r for r in rows if outcome_key(r["score"], r["status"], r["remaining"]) == best]
    cheapest = min(attaining, key=lambda r: (r["cost_usd"], r["downtime_hrs"], len(r["action_ids"])))
    return {
        "subsets_enumerated": enumerated,
        "feasible_subsets_reassessed": len(rows),
        "subsets_attaining_best": len(attaining),
        "best_reassessed_pq_score": best[0],
        "best_outcome": {"pq_risk_score": best[0], "environment_status": cheapest["status"], "remaining_findings": best[2]},
        "cheapest_best_subset": {k: cheapest[k] for k in cheapest if k not in ("score", "status", "remaining")},
    }


def _attains(ev: dict[str, Any], model: dict[str, Any]) -> tuple[bool, bool]:
    key = outcome_key(ev["reassessed_pq_score"], ev["reassessed_status"], len(ev["remaining_findings"]))
    b = model["best_outcome"]
    attains = key == (b["pq_risk_score"], STATUS_RANK[b["environment_status"]], b["remaining_findings"])
    return attains, attains and ev["total_cost_usd"] <= model["cheapest_best_subset"]["cost_usd"]


async def exhaustive(req: AssessmentRequest, actions: list[dict[str, Any]], settings: Settings, max_n: int,
                     ev_a: dict[str, Any], ev_b: dict[str, Any]) -> dict[str, Any] | None:
    n = len(actions)
    if n > max_n:
        return None
    budget, max_dt = req.constraints.budget_usd, req.constraints.max_downtime_hrs

    # Independent accounting (the shipped planner's decision space): every subset of per-finding actions, each paid.
    rows_i: list[dict[str, Any]] = []
    for mask in range(1 << n):
        chosen = [actions[i] for i in range(n) if mask >> i & 1]
        cost, dt = sum(a["cost_usd"] for a in chosen), sum(a["downtime_hrs"] for a in chosen)
        if cost <= budget and dt <= max_dt:
            rows_i.append(await _row(req, chosen, cost, dt, settings))

    # Grouped accounting (the shared-root-cause planner's decision space): every subset of whole groups, paid once.
    groups = qiro.group_actions(actions)
    rows_g: list[dict[str, Any]] = []
    for mask in range(1 << len(groups)):
        chosen_groups = [groups[i] for i in range(len(groups)) if mask >> i & 1]
        cost, dt = sum(g["cost_usd"] for g in chosen_groups), sum(g["downtime_hrs"] for g in chosen_groups)
        if cost <= budget and dt <= max_dt:
            members = [m for g in chosen_groups for m in g["members"]]
            rows_g.append(await _row(req, members, cost, dt, settings, group_ids=[g["id"] for g in chosen_groups]))

    independent, grouped = _best(rows_i, 1 << n), _best(rows_g, 1 << len(groups))
    a_best, a_cheapest = _attains(ev_a, independent)
    b_best, b_cheapest = _attains(ev_b, grouped)
    b_global, _ = _attains(ev_b, independent)
    return {
        "candidate_actions": n,
        "root_cause_groups": len(groups),
        "pipeline_runs": len(rows_i) + len(rows_g),
        "independent_cost_model": independent,
        "grouped_cost_model": grouped,
        "best_reassessed_pq_score": independent["best_reassessed_pq_score"],
        "plan_a_is_best_by_reassessment": a_best,
        "plan_a_is_cheapest_best": a_cheapest,
        "plan_b_is_best_by_reassessment": b_best,
        "plan_b_is_cheapest_best": b_cheapest,
        "plan_b_attains_independent_best": b_global,
    }


async def evaluate_scenario(sc: dict[str, Any], seed: int, settings: Settings, max_n: int) -> dict[str, Any]:
    req = AssessmentRequest.model_validate(sc["request"])
    req.seed = seed
    req.options.llm_report = False
    req_b = req.model_copy(deep=True)
    req_b.options.group_shared_root_causes = True
    base_a: AssessmentResult = await run_assessment(req, settings=settings)
    base_b: AssessmentResult = await run_assessment(req_b, settings=settings)
    ev_a = await evaluate_plan_by_reassessment(req, base_a, settings=settings)
    ev_b = await evaluate_plan_by_reassessment(req_b, base_b, settings=settings)
    actions = qiro.build_actions([f.model_dump() for f in base_a.findings])
    return {
        "scenario": sc["id"],
        "system_id": base_a.system_id,
        "title": sc["title"],
        "budget_usd": req.constraints.budget_usd,
        "max_downtime_hrs": req.constraints.max_downtime_hrs,
        "baseline": {"pq_risk_score": base_a.pq_risk_score, "environment_status": base_a.environment_status,
                     "findings_count": base_a.findings_count,
                     "findings": [{"id": f.id, "type": f.type, "severity": f.severity} for f in base_a.findings]},
        "candidate_actions": len(actions),
        "plan_a": plan_row(ev_a),
        "plan_b": plan_row(ev_b) | {"root_cause_groups": base_b.qiro_optimization.get("root_cause_groups", []),
                                   "root_cause_dependencies": base_b.qiro_optimization.get("root_cause_dependencies", []),
                                   "dependency_adjusted_benefit": base_b.qiro_optimization.get("dependency_adjusted_benefit")},
        "exhaustive": await exhaustive(req, actions, settings, max_n, ev_a, ev_b),
    }


def summarize(systems: list[dict[str, Any]]) -> dict[str, Any]:
    def plan_stats(key: str, best_key: str, cheapest_key: str) -> dict[str, Any]:
        plans = [s[key] for s in systems]
        errors = [abs(p["projection_error"]) for p in plans if p["projection_error"] is not None]
        ex = [s["exhaustive"] for s in systems if s["exhaustive"] is not None]
        return {
            "safe_after_reassessment": sum(p["reassessed_status"] == "SAFE" for p in plans),
            "at_risk_after_reassessment": sum(p["reassessed_status"] == "AT_RISK" for p in plans),
            "unsafe_after_reassessment": sum(p["reassessed_status"] == "UNSAFE" for p in plans),
            "systems_with_remaining_findings": sum(bool(p["remaining_finding_types"]) for p in plans),
            "systems_where_projected_equals_reassessed": sum(e == 0 for e in errors),
            "mean_abs_projection_error": round(statistics.fmean(errors), 3) if errors else None,
            "max_abs_projection_error": max(errors) if errors else None,
            "systems_with_unmodelled_network_mitigations": sum(
                bool(set(p["unmodelled_mitigations"]) & NETWORK_MITIGATIONS) for p in plans),
            "exhaustively_checked": len(ex),
            "best_by_reassessment": sum(e[best_key] for e in ex),
            "cheapest_best": sum(e[cheapest_key] for e in ex),
        }

    icu = next((s for s in systems if s["scenario"] == ICU_GATEWAY_SCENARIO), None)
    wx = icu["exhaustive"] if icu else None
    return {
        "systems": len(systems),
        "systems_safe_at_baseline": sum(s["baseline"]["environment_status"] == "SAFE" for s in systems),
        "plan_a": plan_stats("plan_a", "plan_a_is_best_by_reassessment", "plan_a_is_cheapest_best"),
        "plan_b": plan_stats("plan_b", "plan_b_is_best_by_reassessment", "plan_b_is_cheapest_best"),
        "systems_with_unmodelled_network_mitigations": sum(
            bool((set(s["plan_a"]["unmodelled_mitigations"]) | set(s["plan_b"]["unmodelled_mitigations"])) & NETWORK_MITIGATIONS)
            for s in systems),
        "total_pipeline_runs_exhaustive": sum(s["exhaustive"]["pipeline_runs"] for s in systems if s["exhaustive"]),
        "icu_gateway_scenario": None if icu is None else {
            "scenario": ICU_GATEWAY_SCENARIO,
            "plan_a": {k: icu["plan_a"][k] for k in ("selected_action_ids", "total_cost_usd", "summed_benefit",
                                                        "projected_pq_score", "reassessed_pq_score", "reassessed_status")},
            "plan_a_is_best_by_reassessment": wx["plan_a_is_best_by_reassessment"] if wx else None,
            "plan_a_is_cheapest_best": wx["plan_a_is_cheapest_best"] if wx else None,
            "cheapest_best_subset_independent": wx["independent_cost_model"]["cheapest_best_subset"] if wx else None,
            "plan_b": {k: icu["plan_b"][k] for k in ("selected_action_ids", "total_cost_usd", "summed_benefit",
                                                        "projected_pq_score", "reassessed_pq_score", "reassessed_status")},
            "plan_b_is_best_by_reassessment": wx["plan_b_is_best_by_reassessment"] if wx else None,
            "plan_b_is_cheapest_best": wx["plan_b_is_cheapest_best"] if wx else None,
        },
    }


def _fmt_plan(p: dict[str, Any]) -> str:
    return (f"{p['total_cost_usd']:>7,.0f} {p['summed_benefit']:>4} {p['projected_pq_score']:>3}->{p['reassessed_pq_score']:<3} "
            f"{p['reassessed_status']:<7}")


def print_table(result: dict[str, Any]) -> None:
    head = (f"{'scenario':<22} {'n':>2} | {'A: cost':>7} {'ben':>4} {'proj->re':>8} {'status':<7} | "
            f"{'B: cost':>7} {'ben':>4} {'proj->re':>8} {'status':<7} | best S(ind/grp) A best? B best? unmodelled")
    print(head)
    print("-" * len(head))
    for s in result["systems"]:
        ex = s["exhaustive"]
        if ex:
            best = f"{ex['independent_cost_model']['best_reassessed_pq_score']}/{ex['grouped_cost_model']['best_reassessed_pq_score']}"
            flags = f"{str(ex['plan_a_is_best_by_reassessment']):<7} {str(ex['plan_b_is_best_by_reassessment']):<7}"
        else:
            best, flags = "n/a", f"{'n/a':<7} {'n/a':<7}"
        unmodelled = ",".join(sorted(set(s["plan_a"]["unmodelled_mitigations"]) | set(s["plan_b"]["unmodelled_mitigations"]))) or "-"
        print(f"{s['scenario']:<22} {s['candidate_actions']:>2} | {_fmt_plan(s['plan_a'])} | {_fmt_plan(s['plan_b'])} | "
              f"{best:<15} {flags} {unmodelled}")
    sm = result["summary"]
    print()
    for key in ("plan_a", "plan_b"):
        p = sm[key]
        print(f"{key}: SAFE after reassessment {p['safe_after_reassessment']}/{sm['systems']}; projected == reassessed in "
              f"{p['systems_where_projected_equals_reassessed']}; mean |projected - reassessed| {p['mean_abs_projection_error']}; "
              f"best by reassessment {p['best_by_reassessment']}/{p['exhaustively_checked']}; cheapest best {p['cheapest_best']}")
    print(f"systems with unmodelled network mitigations: {sm['systems_with_unmodelled_network_mitigations']}; "
          f"exhaustive pipeline runs: {sm['total_pipeline_runs_exhaustive']}")
    if sm["icu_gateway_scenario"]:
        w = sm["icu_gateway_scenario"]
        print(f"ICU gateway scenario {w['scenario']}: plan A best by reassessment = {w['plan_a_is_best_by_reassessment']}, "
              f"cheapest best = {w['plan_a_is_cheapest_best']}; cheapest subset reaching the best outcome: "
              f"{w['cheapest_best_subset_independent']}")


async def run(seed: int, max_n: int) -> dict[str, Any]:
    settings = Settings(_env_file=None, llm_provider="none", online_tools_enabled=False)
    t0 = time.perf_counter()
    systems = [await evaluate_scenario(sc, seed, settings, max_n) for sc in load_scenarios()]
    return {
        "benchmark": "plan_reassessment",
        "software_version": __version__,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "seed": seed,
        "exhaustive_max_n": max_n,
        "method": (
            f"{METHOD} Plan A: shipped planner (independent per-finding actions). Plan B: shared-root-cause planner "
            "(actions whose remediation is the same mitigation merged into one decision unit costed once: max cost / "
            "downtime / complexity of the members, summed benefit). Exhaustive check: for scenarios with at most "
            f"{max_n} candidate actions, every subset of per-finding actions feasible under the independent accounting "
            "and every subset of whole root-cause groups feasible under the grouped accounting is reassessed with one "
            "full pipeline run; outcomes are ranked by (PQ score, environment status, remaining findings) and the "
            "cheapest subset attaining the best outcome is reported per accounting. Plan A is compared with the "
            "independent enumeration, plan B with the grouped one. 'Summed benefit' is the sum of the selected "
            "actions' optimization_benefit; 'projected' is the explainer's plan_projection, which assumes each action "
            "removes only its own finding."
        ),
        "caveat": CAVEAT,
        "systems": systems,
        "summary": summarize(systems),
        "runtime_s": round(time.perf_counter() - t0, 2),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "plan_reassessment.json")
    ap.add_argument("--exhaustive-max-n", type=int, default=10)
    args = ap.parse_args(argv)
    result = asyncio.run(run(args.seed, args.exhaustive_max_n))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print_table(result)
    print(f"\nwritten: {args.out} ({result['runtime_s']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
