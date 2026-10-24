from __future__ import annotations

import time

from .base import Agent, AgentRecorder, AgentSpec, RunContext, as_list

INPUT_FIELDS = ("tls_config", "iot_traffic", "ehr_records", "ai_prompt_logs", "device_logs")


class IntakeAgent(Agent):
    spec = AgentSpec(
        id="intake",
        title="Intake & Validation",
        description="Validates the request, normalises prompt and device lists, and records which evidence sources are present.",
        layer="ingest",
        reads=INPUT_FIELDS,
        produces=("prompts", "devices", "input_types_detected"),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        req = ctx.request
        if not req.system_id:
            req.system_id = f"SYS-{int(time.time() * 1000)}"
        detected = [k for k in INPUT_FIELDS if getattr(req, k) is not None]
        ctx.artifacts["input_types_detected"] = detected
        ctx.artifacts["prompts"] = as_list(req.ai_prompt_logs)
        ctx.artifacts["devices"] = as_list(req.device_logs)

        await rec.note(f"System '{req.system_id}' in domain '{req.domain}'.")
        await rec.note(f"Evidence sources present: {', '.join(detected) if detected else 'none'}.")
        await rec.note(
            f"{len(ctx.prompts)} AI prompt entr{'y' if len(ctx.prompts) == 1 else 'ies'}, "
            f"{len(ctx.devices)} device log record(s)."
        )
        if req.tls_config is None:
            await rec.note("No TLS configuration supplied — post-quantum posture cannot be verified from evidence.")
        await rec.note(
            f"Constraints: budget ${req.constraints.budget_usd:,.0f}, max downtime {req.constraints.max_downtime_hrs:g}h; "
            f"optimizer seed {ctx.seed}."
        )
