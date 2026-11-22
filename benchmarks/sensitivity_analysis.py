"""Sensitivity of the PQ risk score, verdict, environment status, pillar scores and QIRO plan to the
scoring constants and to the ten-year data-lifetime rule, over the ten built-in scenarios.

    python benchmarks/sensitivity_analysis.py --seed 2026

Designs
  S1 category weights     each of the six WEIGHTS scaled by 0.8 / 1.2 (one at a time), all renormalised to sum to 1
  S2 severity points      POINTS scaled by 0.8 / 1.2 (all severities at once)
  S3 pillar deductions    PILLAR_DEDUCT scaled by 0.8 / 1.2 (all severities at once)
  S4 lifetime threshold   L in {5, 10, 15, 20} years, full pipeline re-run per scenario
  S5 optimizer weights    qiro.PILLAR_WEIGHTS scaled by 0.8 / 1.2, QIRO re-run on the baseline findings

S1-S3 recompute the pure scoring functions on the baseline findings (findings do not depend on those
constants); S4 and S5 re-run the pipeline / optimizer. Synthetic scenarios only: the constants are design
choices, not calibrated on incident data.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import platform
import statistics
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend" / "src"))
sys.path.insert(0, str(HERE))

from _stats import jaccard, spearman  # noqa: E402
from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.agents import scoring  # noqa: E402
from safeguard_pq.config import Settings  # noqa: E402
from safeguard_pq.domain.models import PILLARS, AssessmentResult, Assumptions, Finding  # noqa: E402
from safeguard_pq.optimizer import qiro  # noqa: E402
from safeguard_pq.orchestrator.pipeline import run_assessment  # noqa: E402
from safeguard_pq.scenarios import load_scenarios  # noqa: E402

FACTORS = (0.8, 1.2)
LIFETIME_THRESHOLDS = (5, 10, 15, 20)
DEFAULT_THRESHOLD = Assumptions().lifetime_threshold_years
HNDL_TYPE = "long_lifetime_classical_crypto"
CAVEAT = "Ten synthetic hand-written scenarios; weights are design choices, not calibrated on incident data."

METHOD = {
    "scenarios": "The ten built-in synthetic scenarios (safeguard_pq/data/scenarios.json), each run once through the "
                 "full pipeline (llm_report=False, fixed seed) to obtain the baseline findings, PQ score, verdict, "
                 "environment status, pillar scores and QIRO plan.",
    "S1_category_weights": "One-at-a-time: each of the six category weights is scaled by 0.8 and 1.2 and all six are "
                           "renormalised to sum to 1; the score is recomputed from the baseline findings.",
    "S2_severity_points": "All severity points (critical 100, high 75, medium 50, low 25) scaled by 0.8 and 1.2 at "
                          "once; the fixed 75-point 'no PQ algorithm in use' posture value is not a severity and is "
                          "not scaled.",
    "S3_pillar_deductions": "All per-severity pillar deductions scaled by 0.8 and 1.2 at once; pillar scores "
                            "recomputed from the baseline findings. Deductions do not enter the PQ score, so the "
                            "score metrics are reported only as a check.",
    "S4_lifetime_threshold": "The data-lifetime threshold of the critical long_lifetime_classical_crypto rule "
                             "(default 10 years) set to 5, 10, 15 and 20 years via assumptions.lifetime_threshold_years "
                             "and the full pipeline re-run, so findings, score, status and plan can all change.",
    "S5_optimizer_pillar_weights": "QIRO's TIPPSS pillar weights scaled by 0.8 and 1.2 at once (module constant "
                                   "patched for the run and restored); the optimizer re-run on the baseline findings "
                                   "with the scenario's budget / downtime constraints and the same seed.",
    "metrics": {
        "verdict_change_share": "share of the ten scenarios whose 4-level PQ verdict differs from baseline",
        "status_change_share": "share whose SAFE / AT_RISK / UNSAFE environment status differs from baseline",
        "mean_abs_delta_score, max_abs_delta_score": "mean and maximum |perturbed - baseline| PQ risk score "
                                                      "(0-100 integer scale)",
        "spearman_rank_correlation": "Spearman rank correlation (average ranks for ties) between the baseline and "
                                     "perturbed PQ-score rankings of the ten scenarios; null when undefined",
        "mean_plan_jaccard": "mean Jaccard similarity of the selected-action sets, matched by finding; only where "
                             "plans were recomputed (S4, S5), else null. Findings are renumbered when the finding set "
                             "changes (S4), so actions are matched by a stable finding signature "
                             "(agent, type, device / detected value) rather than by the F-number.",
        "pillar_metrics (S3)": "mean and max |perturbed - baseline| pillar score over 6 pillars x 10 scenarios; the "
                               "share of scenarios whose reported weakest pillar changes (argmin, ties broken in TIPPSS "
                               "order) and the share where that change is strict (the baseline weakest pillar is no "
                               "longer at the minimum). Under uniform scaling, non-strict changes arise only from the "
                               "0 floor creating ties.",
    },
}


# --------------------------------------------------------------------------- data


@dataclass(frozen=True)
class Outcome:
    score: int
    verdict: str
    status: str
    findings: int | None = None
    plan: frozenset[str] | None = None  # stable keys of the selected actions; None when the plan was not recomputed


@dataclass
class Baseline:
    scenario: str
    request: dict[str, Any]
    result: AssessmentResult

    @property
    def findings(self) -> list[Finding]:
        return self.result.findings

    @property
    def has_tls(self) -> bool:
        return self.request.get("tls_config") is not None

    @property
    def pq_detected(self) -> bool:
        return bool(self.result.pq_posture.get("pq_detected"))

    @property
    def outcome(self) -> Outcome:
        return outcome_of(self.result)


def finding_signatures(findings: Sequence[Finding]) -> dict[str, str]:
    """Stable per-finding keys (agent, type, device / value, occurrence) that survive F-number renumbering."""
    seen: Counter[str] = Counter()
    out: dict[str, str] = {}
    for f in findings:
        extra = f.model_dump()
        base = f"{f.agent}:{f.type}:{extra.get('device_id') or ''}:{extra.get('detected_value') or extra.get('detected_algorithm') or ''}"
        seen[base] += 1
        out[f.id] = base if seen[base] == 1 else f"{base}#{seen[base]}"
    return out


def plan_keys(findings: Sequence[Finding], plan: Mapping[str, Any]) -> frozenset[str]:
    sig = finding_signatures(findings)
    return frozenset(sig[a["finding_id"]] for a in plan["selected_actions"])


def outcome_of(r: AssessmentResult) -> Outcome:
    return Outcome(r.pq_risk_score, r.verdict, r.environment_status, r.findings_count, plan_keys(r.findings, r.qiro_optimization))


def run_scenario(request: dict[str, Any], seed: int, settings: Settings, threshold: float | None = None) -> AssessmentResult:
    req = copy.deepcopy(request)
    req["options"] = {**req.get("options", {}), "llm_report": False}
    req["seed"] = seed
    if threshold is not None:
        req["assumptions"] = {**req.get("assumptions", {}), "lifetime_threshold_years": threshold}
    return asyncio.run(run_assessment(req, settings=settings))


# --------------------------------------------------------------------------- perturbations


def rescored(b: Baseline, *, weights: Mapping[str, float] | None = None, points: Mapping[str, float] | None = None) -> Outcome:
    s = scoring.pq_score(b.findings, b.pq_detected, weights=weights, points=points)
    status, _ = scoring.environment_status(b.findings, s["pq_risk_score"], b.has_tls)
    return Outcome(s["pq_risk_score"], s["status"], status)


def scaled(table: Mapping[str, float], factor: float) -> dict[str, float]:
    return {k: v * factor for k, v in table.items()}


def renormalised_weights(category: str, factor: float) -> dict[str, float]:
    w = dict(scoring.WEIGHTS)
    w[category] *= factor
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}


def pillar_scores(findings: Sequence[Finding], deduct: Mapping[str, float] | None = None) -> dict[str, float]:
    return {k: v["score"] for k, v in scoring.tippss_pillars(findings, deduct=deduct).items()}


def weakest_pillar(scores: Mapping[str, float]) -> str:
    return min(PILLARS, key=lambda p: scores[p])  # ties -> first in TIPPSS order, as in the explainer


def rerun_qiro(b: Baseline, factor: float) -> frozenset[str]:
    original = qiro.PILLAR_WEIGHTS
    qiro.PILLAR_WEIGHTS = scaled(original, factor)
    try:
        c = b.request.get("constraints", {})
        plan = qiro.optimize([f.model_dump() for f in b.findings], c.get("budget_usd", 100_000),
                             c.get("max_downtime_hrs", 40), b.result.metadata["seed"])
    finally:
        qiro.PILLAR_WEIGHTS = original
    return plan_keys(b.findings, plan)


# --------------------------------------------------------------------------- metrics


def compare(ids: Sequence[str], base: Sequence[Outcome], pert: Sequence[Outcome]) -> dict[str, Any]:
    pairs = list(zip(base, pert, strict=True))
    n = len(pairs)
    verdict_changed = [{"scenario": s, "from": b.verdict, "to": p.verdict} for s, (b, p) in zip(ids, pairs, strict=True)
                       if b.verdict != p.verdict]
    status_changed = [{"scenario": s, "from": b.status, "to": p.status} for s, (b, p) in zip(ids, pairs, strict=True)
                      if b.status != p.status]
    deltas = [abs(p.score - b.score) for b, p in pairs]
    jac = [jaccard(b.plan or (), p.plan) for b, p in pairs if p.plan is not None]
    return {
        "verdict_change_share": len(verdict_changed) / n,
        "status_change_share": len(status_changed) / n,
        "mean_abs_delta_score": statistics.fmean(deltas),
        "max_abs_delta_score": max(deltas),
        "spearman_rank_correlation": spearman([b.score for b, _ in pairs], [p.score for _, p in pairs]),
        "mean_plan_jaccard": statistics.fmean(jac) if jac else None,
        "verdict_changed": verdict_changed,
        "status_changed": status_changed,
    }


def compare_pillars(ids: Sequence[str], base: Sequence[Mapping[str, float]], pert: Sequence[Mapping[str, float]]) -> dict[str, Any]:
    diffs = [abs(p[k] - b[k]) for b, p in zip(base, pert, strict=True) for k in PILLARS]
    changed, strict = [], 0
    for s, b, p in zip(ids, base, pert, strict=True):
        wb, wp = weakest_pillar(b), weakest_pillar(p)
        if wb == wp:
            continue
        tie_break = p[wb] == p[wp]  # baseline-weakest pillar is still at the minimum: a tie (0 floor), not a reordering
        strict += not tie_break
        changed.append({"scenario": s, "from": wb, "to": wp, "from_score_after": p[wb], "to_score_after": p[wp],
                        "tie_break_only": tie_break})
    return {
        "mean_abs_delta_pillar_score": statistics.fmean(diffs),
        "max_abs_delta_pillar_score": max(diffs),
        "weakest_pillar_change_share": len(changed) / len(ids),
        "strict_weakest_pillar_change_share": strict / len(ids),
        "weakest_pillar_changed": changed,
    }


def round_floats(obj: Any, ndigits: int = 4) -> Any:
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [round_floats(v, ndigits) for v in obj]
    return obj


# --------------------------------------------------------------------------- designs


def design_s1(ids: Sequence[str], bases: Sequence[Baseline]) -> list[dict[str, Any]]:
    base = [b.outcome for b in bases]
    rows = []
    for category in scoring.WEIGHTS:
        for factor in FACTORS:
            w = renormalised_weights(category, factor)
            pert = [rescored(b, weights=w) for b in bases]
            rows.append({"config": f"{category} x{factor}", "category": category, "factor": factor, "weights": w,
                         "metrics": compare(ids, base, pert)})
    return rows


def design_s2(ids: Sequence[str], bases: Sequence[Baseline]) -> list[dict[str, Any]]:
    base = [b.outcome for b in bases]
    rows = []
    for factor in FACTORS:
        pts = scaled(scoring.POINTS, factor)
        pert = [rescored(b, points=pts) for b in bases]
        rows.append({"config": f"points x{factor}", "factor": factor, "points": pts, "metrics": compare(ids, base, pert)})
    return rows


def design_s3(ids: Sequence[str], bases: Sequence[Baseline]) -> list[dict[str, Any]]:
    base = [b.outcome for b in bases]
    base_pillars = [pillar_scores(b.findings) for b in bases]
    rows = []
    for factor in FACTORS:
        ded = scaled(scoring.PILLAR_DEDUCT, factor)
        pert_pillars = [pillar_scores(b.findings, ded) for b in bases]
        pert = [rescored(b) for b in bases]  # deductions do not enter the PQ score: default recompute, as a check
        rows.append({"config": f"deductions x{factor}", "factor": factor, "pillar_deduct": ded,
                     "metrics": compare(ids, base, pert),
                     "pillar_metrics": compare_pillars(ids, base_pillars, pert_pillars)})
    return rows


def design_s4(ids: Sequence[str], bases: Sequence[Baseline], seed: int, settings: Settings) -> dict[str, Any]:
    base = [b.outcome for b in bases]
    configs, table = [], {b.scenario: {} for b in bases}
    for threshold in LIFETIME_THRESHOLDS:
        pert = []
        for b in bases:
            r = run_scenario(b.request, seed, settings, threshold=threshold)
            if r.metadata["assumptions"]["lifetime_threshold_years"] != threshold:
                raise RuntimeError("lifetime threshold was not applied")
            o = outcome_of(r)
            pert.append(o)
            table[b.scenario][str(threshold)] = {
                "pq_risk_score": o.score, "verdict": o.verdict, "environment_status": o.status, "findings": o.findings,
                "long_lifetime_finding": any(f.type == HNDL_TYPE for f in r.findings),
            }
        identical = all(p == b for p, b in zip(pert, base, strict=True))
        if threshold == DEFAULT_THRESHOLD and not identical:
            raise RuntimeError("default-threshold re-run does not reproduce the baseline")
        configs.append({"config": f"L={threshold}", "lifetime_threshold_years": threshold,
                        "identical_to_baseline": identical, "metrics": compare(ids, base, pert)})
    per_scenario = [{"scenario": b.scenario, "data_lifetime_years": (b.request.get("tls_config") or {}).get("data_lifetime_years"),
                     "by_threshold": table[b.scenario]} for b in bases]
    return {"thresholds_years": list(LIFETIME_THRESHOLDS), "configs": configs, "per_scenario": per_scenario}


def design_s5(ids: Sequence[str], bases: Sequence[Baseline]) -> list[dict[str, Any]]:
    base = [b.outcome for b in bases]
    for b, o in zip(bases, base, strict=True):  # control: the unscaled re-run must reproduce the pipeline's plan
        if rerun_qiro(b, 1.0) != o.plan:
            raise RuntimeError(f"baseline QIRO plan not reproducible for {b.scenario}")
    rows = []
    for factor in FACTORS:
        pert = [Outcome(o.score, o.verdict, o.status, o.findings, rerun_qiro(b, factor)) for b, o in zip(bases, base, strict=True)]
        changed = [s for s, b, p in zip(ids, base, pert, strict=True) if b.plan != p.plan]
        rows.append({"config": f"pillar weights x{factor}", "factor": factor, "pillar_weights": scaled(qiro.PILLAR_WEIGHTS, factor),
                     "metrics": compare(ids, base, pert), "plans_changed": changed})
    return rows


# --------------------------------------------------------------------------- reporting


def _num(x: float | None, width: int = 8, digits: int = 4) -> str:
    return f"{'-':>{width}}" if x is None else f"{x:>{width}.{digits}f}"


def print_summary(result: dict[str, Any]) -> None:
    n = len(result["scenarios"])
    print(f"Scoring sensitivity over {n} scenarios (seed {result['assessment_seed']}, v{result['software_version']})")
    print(f"{'design':<6} {'config':<22} {'verdict':>8} {'status':>8} {'mean|dS|':>9} {'max|dS|':>8} {'Spearman':>9} {'Jaccard':>8}")
    designs = result["designs"]
    for key, rows in designs.items():
        if key == "S4_lifetime_threshold":
            rows = rows["configs"]
        for row in rows:
            m = row["metrics"]
            print(f"{key[:2]:<6} {row['config']:<22} {round(m['verdict_change_share'] * n):>5}/{n:<2} "
                  f"{round(m['status_change_share'] * n):>5}/{n:<2} {_num(m['mean_abs_delta_score'], 9, 2)} "
                  f"{m['max_abs_delta_score']:>8} {_num(m['spearman_rank_correlation'], 9)} {_num(m['mean_plan_jaccard'])}")
    print()
    print("S3 pillar scores: " + "; ".join(
        f"{r['config']}: mean|dP| {r['pillar_metrics']['mean_abs_delta_pillar_score']:.2f}, "
        f"max|dP| {r['pillar_metrics']['max_abs_delta_pillar_score']:.2f}, weakest pillar changes "
        f"{round(r['pillar_metrics']['weakest_pillar_change_share'] * n)}/{n} "
        f"(strict {round(r['pillar_metrics']['strict_weakest_pillar_change_share'] * n)}/{n})"
        for r in designs["S3_pillar_deductions"]))
    print()
    s4 = designs["S4_lifetime_threshold"]
    print("S4 per scenario (PQ score / environment status / findings):")
    print(f"{'scenario':<22} {'lifetime':>8} " + " ".join(f"{'L=' + str(t):>22}" for t in s4["thresholds_years"]))
    for row in s4["per_scenario"]:
        cells = [f"{c['pq_risk_score']:>3} / {c['environment_status']:<7} / {c['findings']:>2}"
                 for c in (row["by_threshold"][str(t)] for t in s4["thresholds_years"])]
        print(f"{row['scenario']:<22} {str(row['data_lifetime_years']):>8} " + " ".join(f"{c:>22}" for c in cells))


# --------------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=2026, help="assessment / QIRO seed (default 2026)")
    ap.add_argument("--out", type=Path, default=HERE / "results" / "sensitivity_analysis.json")
    args = ap.parse_args(argv)

    settings = Settings(_env_file=None, llm_provider="none", online_tools_enabled=False)
    bases = [Baseline(s["id"], json.loads(json.dumps(s["request"])), run_scenario(s["request"], args.seed, settings))
             for s in load_scenarios()]
    ids = [b.scenario for b in bases]

    result = {
        "benchmark": "scoring_sensitivity",
        "software_version": __version__,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "assessment_seed": args.seed,
        "scenarios": ids,
        "defaults": {
            "weights": dict(scoring.WEIGHTS), "points": dict(scoring.POINTS), "pillar_deduct": dict(scoring.PILLAR_DEDUCT),
            "lifetime_threshold_years": DEFAULT_THRESHOLD, "optimizer_pillar_weights": dict(qiro.PILLAR_WEIGHTS),
        },
        "baseline": [{
            "scenario": b.scenario, "pq_risk_score": b.result.pq_risk_score, "verdict": b.result.verdict,
            "environment_status": b.result.environment_status, "findings": b.result.findings_count,
            "selected_action_finding_ids": [a["finding_id"] for a in b.result.qiro_optimization["selected_actions"]],
            "pillar_scores": pillar_scores(b.findings), "weakest_pillar": weakest_pillar(pillar_scores(b.findings)),
        } for b in bases],
        "designs": {
            "S1_category_weights": design_s1(ids, bases),
            "S2_severity_points": design_s2(ids, bases),
            "S3_pillar_deductions": design_s3(ids, bases),
            "S4_lifetime_threshold": design_s4(ids, bases, args.seed, settings),
            "S5_optimizer_pillar_weights": design_s5(ids, bases),
        },
        "method": METHOD,
        "caveat": CAVEAT,
    }
    result = round_floats(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print_summary(result)
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
