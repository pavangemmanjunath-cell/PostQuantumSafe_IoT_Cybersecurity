"""Explainability and reporting agents."""

from __future__ import annotations

import json
from typing import Any

from ..domain.models import Finding
from ..knowledge.redaction import redact
from ..llm import LLMError, get_provider
from . import scoring
from .base import Agent, AgentRecorder, AgentSpec, RunContext

CRYPTO_AGENTS = {"crypto_inventory", "pq_identification"}


def _min_pillar(findings: list[Finding]) -> tuple[str, int]:
    p = scoring.tippss_pillars(findings)
    name = min(p, key=lambda k: p[k]["score"])
    return name, p[name]["score"]


def _evaluate(findings: list[Finding], pq_detected: bool, has_tls: bool) -> dict[str, Any]:
    s = scoring.pq_score(findings, pq_detected)
    status, _ = scoring.environment_status(findings, s["pq_risk_score"], has_tls)
    pillar, pscore = _min_pillar(findings)
    return {"pq_risk_score": s["pq_risk_score"], "verdict": s["status"], "environment_status": status,
            "weakest_pillar": pillar, "weakest_pillar_score": pscore}


class ExplainerAgent(Agent):
    spec = AgentSpec(
        id="explainer",
        title="Explainability (XAI)",
        description="Produces exact additive score attributions, pillar deduction breakdowns, per-finding evidence chains, "
                    "and counterfactuals ('what if this were fixed?') by re-running the same scoring functions.",
        layer="explanation",
        reads=("findings", "scoring", "tippss", "qiro"),
        produces=("explanation",),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        s = ctx.artifacts["scoring"]
        posture = ctx.artifacts.get("pq_posture", {})
        has_tls = ctx.request.tls_config is not None
        pq_detected = bool(posture.get("pq_detected"))
        findings = ctx.findings
        qiro = ctx.artifacts.get("qiro", {})

        # 1) exact additive attribution of the PQ risk score
        attribution = []
        for k, w in scoring.WEIGHTS.items():
            v = s["category_breakdown"][k]
            attribution.append({
                "category": k, "label": scoring.CATEGORY_LABELS[k], "value": v, "weight": w,
                "contribution": round(v * w, 3), "share_pct": round(100 * v * w / s["raw_score"], 1) if s["raw_score"] else 0.0,
                "driver_finding_ids": s["drivers"].get(k, []),
                "explanation": ("no PQ key exchange or signature detected" if k == "migration" and v else None),
            })

        # 2) per-finding explanation chain
        action_by_finding: dict[str, dict] = {}
        for a in qiro.get("selected_actions", []):
            action_by_finding[a["finding_id"]] = {"action_id": a["id"], "decision": "selected", "rank": a.get("priority_rank"),
                                                  "reason": a.get("selection_reason"), "remediation": a["remediation"]}
        for a in qiro.get("excluded_actions", []):
            action_by_finding[a["finding_id"]] = {"action_id": a["id"], "decision": "deferred", "reason": a.get("reason"),
                                                  "remediation": a["remediation"]}
        per_finding = []
        for f in findings:
            cat = scoring.category_of(f)
            per_finding.append({
                "finding_id": f.id, "agent": f.agent, "type": f.type, "severity": f.severity, "detail": f.detail,
                "evidence": [e.model_dump() for e in f.evidence],
                "score_category": cat, "drives_score": bool(cat and f.id in s["drivers"].get(cat, [])),
                "pillar_deduction": {p: scoring.PILLAR_DEDUCT.get(f.severity, 5) for p in f.tippss_mapping},
                "remediation": action_by_finding.get(f.id),
            })

        # 3) counterfactuals: remove all findings of one type; and apply the QIRO plan
        baseline = _evaluate(findings, pq_detected, has_tls)
        counterfactuals = []
        for t in sorted({f.type for f in findings}):
            rest = [f for f in findings if f.type != t]
            crypto_left = any(f.agent in CRYPTO_AGENTS for f in rest)
            after = _evaluate(rest, pq_detected or (has_tls and not crypto_left and t in _PQ_FIX_TYPES), has_tls)
            counterfactuals.append({"scenario": f"Fix all '{t}' findings", "removed_type": t, "before": baseline, "after": after,
                                    "delta_pq_score": after["pq_risk_score"] - baseline["pq_risk_score"]})
        counterfactuals.sort(key=lambda c: (c["delta_pq_score"], c["after"]["environment_status"] != "SAFE"))

        selected_ids = {a["finding_id"] for a in qiro.get("selected_actions", [])}
        plan_rest = [f for f in findings if f.id not in selected_ids]
        plan_pq = pq_detected or (has_tls and not any(f.agent in CRYPTO_AGENTS for f in plan_rest)
                                  and any(f.agent in CRYPTO_AGENTS for f in findings))
        projection = {"scenario": "Apply the QIRO-selected plan", "before": baseline,
                      "after": _evaluate(plan_rest, plan_pq, has_tls), "remaining_findings": [f.id for f in plan_rest]}

        # 4) binding constraint for the optimiser
        binding = None
        if qiro.get("excluded_count"):
            reasons = " ".join(a.get("reason", "") for a in qiro.get("excluded_actions", []))
            binding = "budget" if "budget" in reasons and "downtime" not in reasons else (
                "downtime" if "downtime" in reasons and "budget" not in reasons else "budget and downtime" if "budget" in reasons else "priority")

        top = sorted(attribution, key=lambda a: -a["contribution"])
        summary = []
        if s["raw_score"]:
            summary.append("Largest score drivers: " + ", ".join(
                f"{a['label']} ({a['contribution']:g} pts)" for a in top if a["contribution"] > 0) + ".")
        best_cf = next((c for c in counterfactuals if c["delta_pq_score"] < 0), None)
        if best_cf:
            summary.append(f"Single most effective fix for the PQ score: {best_cf['removed_type']} "
                           f"({baseline['pq_risk_score']} → {best_cf['after']['pq_risk_score']}).")
        summary.append(f"Applying the QIRO plan is projected to move the environment from {baseline['environment_status']} "
                       f"to {projection['after']['environment_status']} (PQ score {baseline['pq_risk_score']} → "
                       f"{projection['after']['pq_risk_score']}).")
        if binding:
            summary.append(f"The binding optimisation constraint was: {binding}.")

        ctx.artifacts["explanation"] = {
            "method": "Rule-based, glass-box assessment: attributions are exact decompositions of the additive score; "
                      "counterfactuals re-run the same scoring functions with findings removed; projections assume a "
                      "remediation fully removes its finding.",
            "summary": summary,
            "score_attribution": attribution,
            "raw_score": round(s["raw_score"], 3),
            "rounded_score": s["pq_risk_score"],
            "pillars": {k: {"score": v["score"], "deductions": v["deductions"]} for k, v in ctx.artifacts["tippss"].items()},
            "findings": per_finding,
            "counterfactuals": counterfactuals[:15],
            "plan_projection": projection,
            "binding_constraint": binding,
            "agent_reasoning": [],  # filled by orchestrator from traces
        }
        for line in summary:
            await rec.note(line)


_PQ_FIX_TYPES = {"classical_key_exchange", "classical_signature", "classical_certificate_key", "pq_migration_required",
                 "long_lifetime_classical_crypto"}

SYSTEM_PROMPT = (
    "You are a clinical cybersecurity advisor. Using ONLY the JSON facts provided, write a concise executive summary "
    "(max 350 words, Markdown) for a hospital CISO: overall status, why (cite finding types), the top 3 actions from the "
    "plan, NIST PQC migration notes (FIPS 203/204/205) and a phased timeline. Do not invent numbers, standards or facts. "
    "State that this is a research-prototype assessment."
)


def deterministic_report(ctx: RunContext) -> str:
    s, env = ctx.artifacts["scoring"], ctx.artifacts["environment"]
    q, posture = ctx.artifacts.get("qiro", {}), ctx.artifacts.get("pq_posture", {})
    lines = [
        f"## Executive summary — {ctx.request.system_id}",
        "",
        f"**Environment status: {env['status'].replace('_', ' ')}.** {'; '.join(env['reasons']).capitalize()}.",
        "",
        f"- PQ risk score **{s['pq_risk_score']}/100** ({s['status']}); PQ readiness: **{posture.get('readiness', 'Unknown')}**.",
        f"- {len(ctx.findings)} finding(s) across {len({f.agent for f in ctx.findings})} agent(s).",
    ]
    if q.get("selected_actions"):
        lines += ["", "### Priority actions (QIRO)"]
        for a in q["selected_actions"][:5]:
            lines.append(f"{a['priority_rank']}. {a['remediation']} — ${a['cost_usd']:,.0f}, {a['downtime_hrs']:g}h "
                         f"(addresses `{a['finding_type']}`)")
        lines += ["", q.get("constraint_explanation", "")]
    if posture.get("advisories"):
        lines += ["", "### Post-quantum notes"] + [f"- {a}" for a in posture["advisories"]]
    lines += ["", "_Research-prototype output. Costs are illustrative; not a certified security assessment._"]
    return "\n".join(lines)


class ReporterAgent(Agent):
    spec = AgentSpec(
        id="reporter",
        title="Report Writer",
        description="Writes the executive narrative. Uses a deterministic template by default; if an LLM is configured "
                    "it rephrases redacted, aggregated facts only.",
        layer="reporting",
        reads=("scoring", "qiro", "pq_posture", "explanation"),
        produces=("report",),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        text = deterministic_report(ctx)
        report = {"markdown": text, "generator": "deterministic-template", "llm_provider": None, "llm_model": None, "llm_error": None}
        provider = get_provider(ctx.settings)
        if provider.name != "none" and ctx.request.options.llm_report:
            facts = {
                "system_id": ctx.request.system_id,
                "environment": ctx.artifacts["environment"],
                "pq_score": ctx.artifacts["scoring"]["pq_risk_score"],
                "pq_readiness": ctx.artifacts.get("pq_posture", {}).get("readiness"),
                "findings": [{"type": f.type, "severity": f.severity, "detail": redact(f.detail)} for f in ctx.findings],
                "plan": [{"rank": a["priority_rank"], "action": a["remediation"], "cost_usd": a["cost_usd"],
                          "downtime_hrs": a["downtime_hrs"]} for a in ctx.artifacts.get("qiro", {}).get("selected_actions", [])],
                "phases": {k: [a["id"] for a in v] for k, v in ctx.artifacts.get("qiro", {}).get("migration_phase_plan", {}).items()},
            }
            try:
                await rec.note(f"Requesting narrative from {provider.name} ({provider.model}) with redacted facts only.")
                llm_text = await provider.complete(SYSTEM_PROMPT, json.dumps(facts))
                if llm_text.strip():
                    report.update(markdown=llm_text.strip(), generator="llm", llm_provider=provider.name, llm_model=provider.model)
            except LLMError as exc:
                report["llm_error"] = str(exc)
                await rec.note(f"LLM unavailable ({exc}); kept deterministic report.")
        else:
            await rec.note("LLM not configured — deterministic template report generated.")
        ctx.artifacts["report"] = report
