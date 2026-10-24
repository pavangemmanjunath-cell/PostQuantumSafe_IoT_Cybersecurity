"""Agent abstraction.

An agent is a small, single-responsibility unit that reads the shared run
context, calls registered tools to gather evidence, and returns findings plus
human-readable reasoning notes. Agents are deterministic given their inputs
(and the run seed), which keeps every assessment reproducible and auditable.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

from ..config import Settings
from ..domain.models import AgentTrace, AssessmentRequest, Evidence, Finding, ToolCall
from ..tools.registry import ToolRegistry

EventSink = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class AgentSpec:
    id: str
    title: str
    description: str
    layer: str  # ingest | detection | post-quantum | analysis | optimization | explanation | reporting
    reads: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    def describe(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "description": self.description, "layer": self.layer,
                "reads": list(self.reads), "produces": list(self.produces), "tools": list(self.tools)}


@dataclass
class RunContext:
    run_id: str
    request: AssessmentRequest
    settings: Settings
    tools: ToolRegistry
    seed: int
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    @property
    def prompts(self) -> list[Any]:
        return self.artifacts.get("prompts", [])

    @property
    def devices(self) -> list[Any]:
        return self.artifacts.get("devices", [])


class AgentRecorder:
    """Collects notes, tool calls and staged findings for one agent run, and emits live events."""

    def __init__(self, ctx: RunContext, spec: AgentSpec, sink: EventSink | None) -> None:
        self.ctx, self.spec, self._sink = ctx, spec, sink
        self.notes: list[str] = []
        self.tool_calls: list[ToolCall] = []
        self.staged: list[Finding] = []
        self.started_at = datetime.now(UTC).isoformat()
        self._t0 = time.perf_counter()

    async def emit(self, type_: str, **data: Any) -> None:
        if self._sink:
            await self._sink({"type": type_, "run_id": self.ctx.run_id, "agent": self.spec.id, **data})

    async def note(self, text: str) -> None:
        self.notes.append(text)
        await self.emit("agent_note", text=text)

    async def tool(self, tool_name: str, /, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        result = self.ctx.tools.call(tool_name, **kwargs)
        tool = self.ctx.tools.get(tool_name)
        call = ToolCall(
            tool=tool_name,
            arguments={k: (v if not isinstance(v, str) or len(v) <= 60 else v[:57] + "…") for k, v in kwargs.items()
                       if not isinstance(v, dict | list)},
            result_summary=tool.summarize(result),
            duration_ms=round((time.perf_counter() - t0) * 1000, 3),
        )
        self.tool_calls.append(call)
        await self.emit("tool_called", tool=tool_name, summary=call.result_summary)
        return result

    def finding(self, *, severity: str, type: str, detail: str, tippss_mapping: list[str],
                evidence: list[Evidence] | None = None, **extra: Any) -> Finding:
        f = Finding(agent=self.spec.id, severity=severity, type=type, detail=detail,
                    tippss_mapping=list(tippss_mapping), evidence=evidence or [], **extra)
        self.staged.append(f)
        return f

    def trace(self, status: str = "completed", error: str | None = None) -> AgentTrace:
        return AgentTrace(
            agent=self.spec.id,
            title=self.spec.title,
            status=status,  # type: ignore[arg-type]
            started_at=self.started_at,
            duration_ms=round((time.perf_counter() - self._t0) * 1000, 3),
            notes=self.notes,
            tool_calls=self.tool_calls,
            finding_ids=[f.id for f in self.staged],
            error=error,
        )


class Agent(ABC):
    spec: ClassVar[AgentSpec]

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        """Return (run?, reason). Skipped agents are still shown in the trace."""
        return True, ""

    @abstractmethod
    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None: ...


def as_list(value: Any) -> list[Any]:
    """v0 semantics: arrays pass through; a single value becomes a one-element list; null → []."""
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]
