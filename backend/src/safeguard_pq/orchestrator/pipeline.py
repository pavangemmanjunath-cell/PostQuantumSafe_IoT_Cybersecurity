"""Multi-agent assessment pipeline."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from .. import __version__
from ..agents import REQUIRED_AGENTS, STAGES
from ..agents.base import Agent, AgentRecorder, EventSink, RunContext
from ..agents.scoring import WEIGHTS
from ..config import Settings, get_settings
from ..domain.models import AgentTrace, AssessmentRequest, AssessmentResult
from ..tools import ToolRegistry, default_registry


class AssessmentPipeline:
    def __init__(self, settings: Settings | None = None, tools: ToolRegistry | None = None) -> None:
        self.settings = settings or get_settings()
        self.tools = tools or default_registry()

    async def run(self, request: AssessmentRequest, sink: EventSink | None = None) -> AssessmentResult:
        req = request.model_copy(deep=True)
        run_id = uuid.uuid4().hex[:12]
        seed = req.seed if req.seed is not None else self.settings.qiro_default_seed
        ctx = RunContext(run_id=run_id, request=req, settings=self.settings, tools=self.tools, seed=seed)
        disabled = set(req.options.disabled_agents) - REQUIRED_AGENTS
        pace = req.options.pace_ms / 1000
        traces: list[AgentTrace] = []

        async def emit(event: dict[str, Any]) -> None:
            if sink:
                await sink({"ts": datetime.now(UTC).isoformat(), **event})

        await emit({"type": "run_started", "run_id": run_id, "stages": [[a.spec.id for a in s] for s in STAGES]})

        for stage_index, stage in enumerate(STAGES):
            agents = [cls() for cls in stage]
            await emit({"type": "stage_started", "run_id": run_id, "stage": stage_index, "agents": [a.spec.id for a in agents]})
            results = await asyncio.gather(*(self._run_agent(a, ctx, disabled, emit, pace) for a in agents))
            for rec, trace in results:
                for f in rec.staged:  # merge in declared order → deterministic ids
                    f.id = f"F{len(ctx.findings) + 1}"
                    ctx.findings.append(f)
                trace.finding_ids = [f.id for f in rec.staged]
                traces.append(trace)
                for f in rec.staged:
                    await emit({"type": "finding", "run_id": run_id, "agent": trace.agent, "finding": f.model_dump()})
                await emit({"type": "agent_completed", "run_id": run_id, "agent": trace.agent, "status": trace.status,
                            "duration_ms": trace.duration_ms, "finding_count": len(trace.finding_ids),
                            "tool_calls": len(trace.tool_calls), "notes": trace.notes[-3:]})

        result = self._assemble(ctx, traces)
        await emit({"type": "run_completed", "run_id": run_id, "assessment_id": result.assessment_id,
                    "environment_status": result.environment_status, "pq_risk_score": result.pq_risk_score})
        return result

    async def _run_agent(self, agent: Agent, ctx: RunContext, disabled: set[str], emit: EventSink, pace: float):
        rec = AgentRecorder(ctx, agent.spec, emit)
        await rec.emit("agent_started", title=agent.spec.title, layer=agent.spec.layer)
        if pace:
            await asyncio.sleep(pace)
        if agent.spec.id in disabled:
            await rec.note("Disabled by request options.")
            return rec, rec.trace("skipped")
        ok, reason = agent.applicable(ctx)
        if not ok:
            await rec.note(f"Skipped: {reason}.")
            return rec, rec.trace("skipped")
        try:
            await agent.run(ctx, rec)
        except Exception as exc:  # an agent failure must not hide other evidence
            rec.staged.clear()
            await rec.note(f"Agent failed: {type(exc).__name__}: {exc}")
            if agent.spec.id in REQUIRED_AGENTS:
                raise
            return rec, rec.trace("failed", error=f"{type(exc).__name__}: {exc}")
        return rec, rec.trace("completed")

    def _assemble(self, ctx: RunContext, traces: list[AgentTrace]) -> AssessmentResult:
        a = ctx.artifacts
        s, env = a["scoring"], a["environment"]
        explanation = a["explanation"]
        explanation["agent_reasoning"] = [{"agent": t.agent, "title": t.title, "status": t.status, "notes": t.notes} for t in traces]
        tippss = {k: {"score": v["score"], "finding_ids": v["finding_ids"]} for k, v in a["tippss"].items()}
        return AssessmentResult(
            assessment_id=ctx.run_id,
            system_id=ctx.request.system_id or "unknown",
            timestamp=datetime.now(UTC).isoformat(),
            domain=ctx.request.domain,
            version=__version__,
            environment_status=env["status"],
            environment_reasons=env["reasons"],
            verdict=s["status"],
            pq_risk_score=s["pq_risk_score"],
            findings_count=len(ctx.findings),
            findings=ctx.findings,
            tippss_scores=tippss,
            category_breakdown=s["category_breakdown"],
            weights=dict(WEIGHTS),
            crypto_inventory=a.get("crypto_inventory", []),
            pq_posture=a.get("pq_posture", {}),
            qiro_optimization=a["qiro"],
            explanation=explanation,
            report=a["report"],
            trace=traces,
            metadata={
                "seed": ctx.seed,
                "input_types_detected": a.get("input_types_detected", []),
                "traffic_features": a.get("traffic_features"),
                "scenario_summary": ctx.request.scenario_summary,
                "source_file": ctx.request.source_file,
                "constraints": ctx.request.constraints.model_dump(),
                "assumptions": ctx.request.assumptions.model_dump(),
                "disabled_agents": sorted(set(ctx.request.options.disabled_agents) - REQUIRED_AGENTS),
                "disclaimer": "Research prototype. Rule-based heuristics and illustrative costs; not a certified security "
                              "assessment and not for clinical decision-making.",
            },
        )


async def run_assessment(request: AssessmentRequest | dict, sink: EventSink | None = None,
                         settings: Settings | None = None) -> AssessmentResult:
    req = request if isinstance(request, AssessmentRequest) else AssessmentRequest.model_validate(request)
    return await AssessmentPipeline(settings).run(req, sink)
