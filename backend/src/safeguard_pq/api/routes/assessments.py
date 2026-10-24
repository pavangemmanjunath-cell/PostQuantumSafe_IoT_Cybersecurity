"""Assessment, scenario, upload and live-stream endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import ValidationError

from ...domain.models import AssessmentRequest, AssessmentResult
from ...ingest.csv_adapters import IngestError, build_request
from ...reporting import build_assessment_pdf
from ...scenarios import get_scenario, load_scenarios
from ...simulation import SimulationError
from ..state import AppState
from .deps import core, pdf_headers, ws_core

router = APIRouter(tags=["assessments"])


def _summary(r: AssessmentResult) -> dict[str, Any]:
    return {"assessment_id": r.assessment_id, "system_id": r.system_id, "timestamp": r.timestamp,
            "environment_status": r.environment_status, "pq_risk_score": r.pq_risk_score, "verdict": r.verdict,
            "findings_count": r.findings_count}


@router.get("/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return [{k: s[k] for k in ("id", "title", "summary", "story", "origin")} for s in load_scenarios()]


@router.get("/scenarios/{scenario_id}")
def scenario(scenario_id: str) -> dict[str, Any]:
    s = get_scenario(scenario_id)
    if not s:
        raise HTTPException(404, f"unknown scenario '{scenario_id}'")
    return s


@router.post("/assessments", response_model=AssessmentResult)
async def create_assessment(req: AssessmentRequest, state: AppState = Depends(core)) -> AssessmentResult:
    result = await state.pipeline.run(req)
    state.assessments.put(result)
    return result


@router.get("/assessments")
def recent_assessments(limit: int = 20, state: AppState = Depends(core)) -> list[dict[str, Any]]:
    return [_summary(r) for r in state.assessments.recent(min(max(limit, 1), 100))]


def _get(state: AppState, assessment_id: str) -> AssessmentResult:
    r = state.assessments.get(assessment_id)
    if r is None:
        raise HTTPException(404, f"unknown assessment '{assessment_id}' (results are kept in memory only)")
    return r


@router.get("/assessments/{assessment_id}", response_model=AssessmentResult)
def get_assessment(assessment_id: str, state: AppState = Depends(core)) -> AssessmentResult:
    return _get(state, assessment_id)


@router.get("/assessments/{assessment_id}/report.pdf", response_class=Response)
def assessment_pdf(assessment_id: str, state: AppState = Depends(core)) -> Response:
    r = _get(state, assessment_id)
    return Response(build_assessment_pdf(r), media_type="application/pdf",
                    headers=pdf_headers(f"safeguard-pq_{r.system_id}_{r.assessment_id}.pdf"))


@router.post("/uploads/assess", response_model=AssessmentResult)
async def assess_upload(
    file: UploadFile = File(...),
    tls_profile: str = Form("none"),
    budget_usd: float = Form(100_000),
    max_downtime_hrs: float = Form(40),
    window_rows: int = Form(100),
    include_injection_probe: bool = Form(False),
    state: AppState = Depends(core),
) -> AssessmentResult:
    limit = state.settings.max_upload_mb * 1024 * 1024
    raw = await file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(413, f"file exceeds {state.settings.max_upload_mb} MB")
    try:
        payload = build_request(file.filename or "upload.csv", raw, window_rows=max(20, min(window_rows, 2000)),
                                max_rows=state.settings.max_upload_rows, tls_profile=tls_profile, budget_usd=budget_usd,
                                max_downtime_hrs=max_downtime_hrs, include_injection_probe=include_injection_probe)
        req = AssessmentRequest.model_validate(payload)
    except (IngestError, ValidationError) as exc:
        raise HTTPException(422, str(exc)) from exc
    result = await state.pipeline.run(req)
    state.assessments.put(result)
    return result


@router.websocket("/ws/assessments")
async def assessment_stream(ws: WebSocket) -> None:
    """Client sends one JSON message: {"request": {...}} | {"scenario_id": "..."} | {"simulation_id": "...", "device_id": "..."}
    plus optional "pace_ms". The server streams agent events and finishes with {"type": "result", "result": {...}}."""
    state = ws_core(ws)
    await ws.accept()
    try:
        msg = await ws.receive_json()
        req = _resolve_request(state, msg)
        if "pace_ms" in msg:
            req.options.pace_ms = max(0, min(int(msg["pace_ms"]), 2000))

        async def sink(event: dict[str, Any]) -> None:
            await ws.send_json(event)

        result = await state.pipeline.run(req, sink)
        state.assessments.put(result)
        if msg.get("simulation_id") and msg.get("device_id"):
            sim = state.simulations.get(msg["simulation_id"])
            sim.device(msg["device_id"]).last_assessment = {
                "assessment_id": result.assessment_id, "environment_status": result.environment_status,
                "pq_risk_score": result.pq_risk_score, "findings_count": result.findings_count, "tick": sim.tick}
        await ws.send_json({"type": "result", "result": result.model_dump(mode="json")})
        await ws.close()
    except WebSocketDisconnect:
        return
    except (ValidationError, SimulationError, ValueError, KeyError) as exc:
        await ws.send_json({"type": "error", "detail": str(exc)})
        await ws.close(code=1008)


def _resolve_request(state: AppState, msg: dict[str, Any]) -> AssessmentRequest:
    if "request" in msg:
        return AssessmentRequest.model_validate(msg["request"])
    if "scenario_id" in msg:
        s = get_scenario(msg["scenario_id"])
        if not s:
            raise ValueError(f"unknown scenario '{msg['scenario_id']}'")
        req = AssessmentRequest.model_validate(s["request"])
        if "constraints" in msg:
            req.constraints = req.constraints.model_validate(msg["constraints"])
        return req
    if "simulation_id" in msg and "device_id" in msg:
        sim = state.simulations.get(msg["simulation_id"])
        c = msg.get("constraints") or {}
        return sim.to_request(msg["device_id"], c.get("budget_usd", 100_000), c.get("max_downtime_hrs", 40))
    raise ValueError("expected 'request', 'scenario_id' or 'simulation_id' + 'device_id'")
