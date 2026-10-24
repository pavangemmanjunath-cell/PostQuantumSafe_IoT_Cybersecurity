"""IoT fleet simulation endpoints and live WebSocket stream."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ...domain.models import AssessmentResult
from ...reporting import build_fleet_pdf
from ...simulation import Simulation, SimulationError
from ...simulation.engine import catalog_view
from ...simulation.fleet import assess_fleet
from ..state import AppState
from .deps import core, pdf_headers, ws_core

router = APIRouter(prefix="/simulations", tags=["simulation"])


class CreateSimulation(BaseModel):
    template: str = "hospital_ward"
    seed: int = 7
    data_source: str = "synthetic"


class AttackBody(BaseModel):
    device_id: str
    attack: str


class MitigationBody(BaseModel):
    mitigation: str
    device_id: str | None = Field(default=None, description="Omit to apply fleet-wide.")


class PlanBody(BaseModel):
    action_mitigations: list[dict[str, str | None]] = Field(
        description="[{'mitigation': id, 'device_id': id|null}] — typically taken from QIRO selected actions.")


class AssumptionBody(BaseModel):
    migration_years: float = Field(default=5, ge=0, le=50)
    years_to_crqc: float = Field(default=10, ge=0, le=100)


class ConstraintBody(BaseModel):
    budget_usd: float = Field(default=100_000, ge=0)
    max_downtime_hrs: float = Field(default=40, ge=0)


def _sim(state: AppState, sim_id: str) -> Simulation:
    try:
        return state.simulations.get(sim_id)
    except SimulationError as exc:
        raise HTTPException(404, str(exc)) from exc


def _guard(fn, *args):  # noqa: ANN001, ANN202
    try:
        return fn(*args)
    except SimulationError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/catalog")
def simulation_catalog() -> dict[str, Any]:
    return catalog_view()


@router.post("")
def create_simulation(body: CreateSimulation, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _guard(lambda: Simulation(body.template, body.seed, body.data_source, state.settings.replay_data_dir))
    state.simulations.add(sim)
    return sim.snapshot()


@router.get("/{sim_id}")
def get_simulation(sim_id: str, state: AppState = Depends(core)) -> dict[str, Any]:
    return _sim(state, sim_id).snapshot()


@router.post("/{sim_id}/step")
def step(sim_id: str, ticks: int = 1, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _sim(state, sim_id)
    for _ in range(max(1, min(ticks, 50))):
        sim.step()
    return sim.snapshot()


@router.post("/{sim_id}/attacks")
def inject(sim_id: str, body: AttackBody, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _sim(state, sim_id)
    event = _guard(sim.inject, body.device_id, body.attack)
    return {"event": event, "device": sim.device_view(sim.device(body.device_id))}


@router.delete("/{sim_id}/attacks/{device_id}/{attack}")
def clear_attack(sim_id: str, device_id: str, attack: str, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _sim(state, sim_id)
    event = _guard(sim.clear_attack, device_id, attack)
    return {"event": event, "device": sim.device_view(sim.device(device_id))}


@router.post("/{sim_id}/mitigations")
def mitigate(sim_id: str, body: MitigationBody, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _sim(state, sim_id)
    events = _guard(sim.mitigate, body.device_id, body.mitigation)
    return {"events": events, "snapshot": sim.snapshot()}


@router.post("/{sim_id}/assumptions")
def set_assumptions(sim_id: str, body: AssumptionBody, state: AppState = Depends(core)) -> dict[str, Any]:
    """Q-Day what-if: change the assumed years to a CRQC and migration duration (Mosca's inequality)."""
    sim = _sim(state, sim_id)
    _guard(sim.set_assumptions, body.migration_years, body.years_to_crqc)
    return sim.snapshot()


@router.post("/{sim_id}/apply-plan")
def apply_plan(sim_id: str, body: PlanBody, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _sim(state, sim_id)
    events: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str]] = set()
    for item in body.action_mitigations:
        m, d = item.get("mitigation"), item.get("device_id")
        if not m or (d, m) in seen:
            continue
        seen.add((d, m))
        try:
            events += sim.mitigate(d, m)
        except SimulationError as exc:
            events.append({"level": "warning", "message": str(exc), "device_id": d})
    return {"events": events, "snapshot": sim.snapshot()}


@router.post("/{sim_id}/devices/{device_id}/assess", response_model=AssessmentResult)
async def assess_device(sim_id: str, device_id: str, body: ConstraintBody | None = None,
                        state: AppState = Depends(core)) -> AssessmentResult:
    sim = _sim(state, sim_id)
    c = body or ConstraintBody()
    req = _guard(sim.to_request, device_id, c.budget_usd, c.max_downtime_hrs)
    result = await state.pipeline.run(req)
    state.assessments.put(result)
    sim.device(device_id).last_assessment = {"assessment_id": result.assessment_id, "environment_status": result.environment_status,
                                             "pq_risk_score": result.pq_risk_score, "findings_count": result.findings_count,
                                             "tick": sim.tick}
    return result


@router.post("/{sim_id}/assess")
async def assess_simulation(sim_id: str, body: ConstraintBody | None = None, state: AppState = Depends(core)) -> dict[str, Any]:
    sim = _sim(state, sim_id)
    c = body or ConstraintBody(budget_usd=250_000, max_downtime_hrs=80)
    report = await assess_fleet(sim, state.pipeline, c.budget_usd, c.max_downtime_hrs, state.assessments)
    state.fleet_reports[sim.id] = report
    return report


@router.get("/{sim_id}/report.pdf", response_class=Response)
def fleet_pdf(sim_id: str, state: AppState = Depends(core)) -> Response:
    sim = _sim(state, sim_id)
    report = state.fleet_reports.get(sim.id)
    if report is None:
        raise HTTPException(409, "run a fleet assessment first (POST /simulations/{id}/assess)")
    return Response(build_fleet_pdf(report), media_type="application/pdf",
                    headers=pdf_headers(f"safeguard-pq_fleet_{sim.id}_tick{report['tick']}.pdf"))


@router.websocket("/{sim_id}/stream")
async def stream(ws: WebSocket, sim_id: str, interval_ms: int = 1000) -> None:
    """Live telemetry stream: one 'tick' message per interval with device states and new events."""
    state = ws_core(ws)
    try:
        sim = state.simulations.get(sim_id)
    except SimulationError:
        await ws.close(code=1008)
        return
    await ws.accept()
    interval = max(0.2, min(interval_ms / 1000, 10))
    last_seq = 0
    try:
        while True:
            if time.monotonic() - sim.last_step >= interval * 0.9:
                sim.step()
            snap = sim.snapshot(since_event=last_seq)
            if snap["events"]:
                last_seq = snap["events"][-1]["seq"]
            await ws.send_json({"type": "tick", **snap})
            await asyncio.sleep(interval)
    except (WebSocketDisconnect, RuntimeError):
        return
