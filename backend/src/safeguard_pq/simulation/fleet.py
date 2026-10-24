"""Fleet-level assessment: run the pipeline per device, then plan remediation under one shared budget."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..domain.models import PILLARS, AssessmentResult
from ..optimizer import qiro
from ..orchestrator import AssessmentPipeline
from .engine import Simulation

_ORDER = {"SAFE": 0, "AT_RISK": 1, "UNSAFE": 2}


async def assess_fleet(sim: Simulation, pipeline: AssessmentPipeline, budget_usd: float, max_downtime_hrs: float,
                       store: Any | None = None) -> dict[str, Any]:
    results: list[tuple[str, AssessmentResult]] = []
    for d in sim.devices.values():
        res = await pipeline.run(sim.to_request(d.id))
        if store is not None:
            store.put(res)
        d.last_assessment = {"assessment_id": res.assessment_id, "environment_status": res.environment_status,
                             "pq_risk_score": res.pq_risk_score, "findings_count": res.findings_count, "tick": sim.tick}
        results.append((d.id, res))

    combined: list[dict[str, Any]] = []
    for did, res in results:
        for f in res.findings:
            fd = f.model_dump()
            fd.update(id=f"{did}:{f.id}", device_id=did, detail=f"[{did}] {f.detail}")
            combined.append(fd)
    plan = qiro.optimize(combined, budget_usd, max_downtime_hrs, sim.seed)

    devices = []
    pillars = {p: 100 for p in PILLARS}
    counts = {"SAFE": 0, "AT_RISK": 0, "UNSAFE": 0}
    for did, res in results:
        d = sim.devices[did]
        counts[res.environment_status] += 1
        for p, v in res.tippss_scores.items():
            pillars[p] = min(pillars[p], v["score"])
        sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        top = [f.type for f in sorted(res.findings, key=lambda f: sev_rank.get(f.severity, 5))][:3]
        devices.append({
            "device_id": did, "label": d.label, "zone": d.zone, "assessment_id": res.assessment_id,
            "environment_status": res.environment_status, "pq_risk_score": res.pq_risk_score, "verdict": res.verdict,
            "pq_readiness": res.pq_posture.get("readiness", "Unknown"), "findings_count": res.findings_count,
            "top_issues": list(dict.fromkeys(top)), "active_attacks": list(d.active_attacks),
        })
    worst = max((r.environment_status for _, r in results), key=lambda s: _ORDER[s], default="SAFE")
    return {
        "simulation_id": sim.id, "template": sim.template.id, "template_label": sim.template.label, "tick": sim.tick,
        "data_source": sim.data_source, "timestamp": datetime.now(UTC).isoformat(),
        "environment_status": worst, "counts": counts,
        "mean_pq_risk_score": round(sum(r.pq_risk_score for _, r in results) / max(1, len(results)), 1),
        "fleet_pillars": pillars, "devices": devices, "fleet_plan": plan,
        "budget_usd": budget_usd, "max_downtime_hrs": max_downtime_hrs,
    }
