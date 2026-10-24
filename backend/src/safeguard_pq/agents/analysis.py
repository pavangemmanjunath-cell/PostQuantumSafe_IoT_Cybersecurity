"""TIPPSS mapping, risk scoring and QIRO planning agents."""

from __future__ import annotations

from ..optimizer import qiro
from . import scoring
from .base import Agent, AgentRecorder, AgentSpec, RunContext


class TIPPSSMappingAgent(Agent):
    spec = AgentSpec(
        id="tippss_mapping",
        title="TIPPSS Mapping",
        description="Maps every finding onto the six IEEE 2933-2024 TIPPSS pillars and computes per-pillar scores.",
        layer="analysis",
        reads=("findings",),
        produces=("tippss",),
        tools=("standards.tippss_pillars",),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        await rec.tool("standards.tippss_pillars")
        pillars = scoring.tippss_pillars(ctx.findings)
        ctx.artifacts["tippss"] = pillars
        weakest = min(pillars.items(), key=lambda kv: kv[1]["score"])
        await rec.note("Pillar scores: " + ", ".join(f"{k} {v['score']}" for k, v in pillars.items()) + ".")
        if weakest[1]["score"] < 100:
            await rec.note(f"Weakest pillar: {weakest[0]} ({weakest[1]['score']}/100, {len(weakest[1]['finding_ids'])} finding(s)).")


class RiskScoringAgent(Agent):
    spec = AgentSpec(
        id="risk_scoring",
        title="PQ Risk Scoring",
        description="Computes the weighted 0–100 post-quantum risk score, the PQ verdict, and the overall environment status.",
        layer="analysis",
        reads=("findings", "pq_posture"),
        produces=("scoring", "environment_status"),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        posture = ctx.artifacts.get("pq_posture", {})
        s = scoring.pq_score(ctx.findings, bool(posture.get("pq_detected")))
        status, reasons = scoring.environment_status(ctx.findings, s["pq_risk_score"], ctx.request.tls_config is not None)
        ctx.artifacts["scoring"] = s
        ctx.artifacts["environment"] = {"status": status, "reasons": reasons}
        parts = [f"{scoring.CATEGORY_LABELS[k]} {v:g}×{scoring.WEIGHTS[k]:.2f}" for k, v in s["category_breakdown"].items() if v]
        await rec.note(f"Score = {' + '.join(parts) or '0'} = {s['raw_score']:.2f} → {s['pq_risk_score']}/100 ({s['status']}).")
        await rec.note(f"Environment status: {status} — {'; '.join(reasons)}.")


class QIROAgent(Agent):
    spec = AgentSpec(
        id="qiro_optimizer",
        title="QIRO Remediation Planner",
        description="Turns findings into candidate actions and selects the best portfolio under budget and downtime "
                    "using seeded simulated annealing; reports the gap to the exact optimum for small problems.",
        layer="optimization",
        reads=("findings", "constraints"),
        produces=("qiro",),
        tools=("remediation.lookup",),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        for t in sorted({f.type for f in ctx.findings}):
            await rec.tool("remediation.lookup", finding_type=t)
        c = ctx.request.constraints
        result = qiro.optimize([f.model_dump() for f in ctx.findings], c.budget_usd, c.max_downtime_hrs, ctx.seed)
        ctx.artifacts["qiro"] = result
        await rec.note(result["message"])
        opt = result.get("optimality")
        if opt and opt.get("exact_objective") is not None:
            await rec.note(f"Annealing objective {opt['heuristic_objective']:g} vs exact optimum {opt['exact_objective']:g} "
                           f"(gap {opt['gap_pct'] or 0:g}%).")
