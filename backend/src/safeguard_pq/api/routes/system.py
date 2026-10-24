"""Health, agent catalogue and tool APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from ... import __version__
from ...agents import describe_agents
from ...knowledge import patterns, pqc_catalog, remediation
from ...tools import default_registry
from ...tools.registry import ToolError
from ..state import AppState
from .deps import core

router = APIRouter(tags=["system"])


@router.get("/health")
def health(state: AppState = Depends(core)) -> dict[str, Any]:
    s = state.settings
    return {
        "status": "ok",
        "version": __version__,
        "llm": {"provider": s.llm_provider if s.llm_enabled else "none", "model": s.llm_model if s.llm_enabled else None},
        "online_tools_enabled": s.online_tools_enabled,
        "replay_data_available": bool(s.replay_data_dir),
        "agents": len(describe_agents()),
        "tools": len(default_registry().list()),
    }


@router.get("/agents")
def agents() -> list[dict[str, Any]]:
    return describe_agents()


@router.get("/tools")
def list_tools() -> list[dict[str, Any]]:
    return [t.describe() for t in default_registry().list()]


@router.post("/tools/{name}")
def call_tool(name: str, arguments: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    reg = default_registry()
    try:
        tool = reg.get(name)
        result = reg.call(name, **arguments)
    except ToolError as exc:
        raise HTTPException(status_code=400 if "unknown tool" not in str(exc) else 404, detail=str(exc)) from exc
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid arguments: {exc}") from exc
    return {"tool": name, "summary": tool.summarize(result), "result": result}


@router.get("/knowledge")
def knowledge() -> dict[str, Any]:
    return {
        "pqc_catalog": pqc_catalog.catalog(),
        "rules": {name: patterns.describe(patterns.rule_table(name)) for name in ("phi", "injection", "secrets", "unsafe")},
        "remediation_templates": remediation.catalog(),
        "remediation_note": "Costs/downtimes are illustrative placeholders.",
    }
