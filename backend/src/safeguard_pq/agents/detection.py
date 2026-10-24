"""Content, identity and traffic detection agents (run in parallel)."""

from __future__ import annotations

from ..domain.models import Evidence
from ..knowledge import patterns
from .base import Agent, AgentRecorder, AgentSpec, RunContext
from .text import js_stringify, prompt_text

_HIPAA_REF = "HIPAA Privacy Rule, 45 CFR 164.514(b)(2) identifiers"


class ClinicalPrivacyAgent(Agent):
    spec = AgentSpec(
        id="clinical_privacy",
        title="Clinical Privacy (PHI)",
        description="Scans AI prompt logs for protected health information before it reaches a model or a log store.",
        layer="detection",
        reads=("ai_prompt_logs",),
        tools=("privacy.scan_phi",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (bool(ctx.prompts), "no AI prompt logs supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        for i, p in enumerate(ctx.prompts):
            if not p:
                continue
            text = prompt_text(p, stringify_objects=True)
            for h in await rec.tool("privacy.scan_phi", text=text):
                rec.finding(
                    severity="critical" if h["type"] == "sensitive_diagnosis" else "high",
                    type=h["type"], detail=f"PHI detected in prompt #{i}: {h['type']}", match_count=h["match_count"],
                    tippss_mapping=patterns.PHI_PILLARS,
                    evidence=[Evidence(source=f"ai_prompt_logs[{i}]", rule=h["description"], observed=h["excerpt"], reference=_HIPAA_REF)],
                )
        await rec.note(f"Scanned {len(ctx.prompts)} prompt(s); {len(rec.staged)} PHI finding(s). Excerpts are redacted.")


class PromptInjectionAgent(Agent):
    spec = AgentSpec(
        id="prompt_injection",
        title="Prompt Injection & PQ-Downgrade",
        description="Detects instruction overrides, fake system messages, tool hijacking and instructions that try to make an "
                    "AI agent weaken post-quantum protection.",
        layer="detection",
        reads=("ai_prompt_logs",),
        tools=("security.scan_prompt_injection",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (bool(ctx.prompts), "no AI prompt logs supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        for i, p in enumerate(ctx.prompts):
            if not p:
                continue
            text = prompt_text(p, stringify_objects=False)
            for h in await rec.tool("security.scan_prompt_injection", text=text):
                pillars = patterns.PQ_INJECTION_PILLARS if h["type"] == "pq_downgrade_instruction" else patterns.INJECTION_PILLARS
                rec.finding(
                    severity=h["severity"], type=h["type"], detail=f"Prompt injection in #{i}: {h['type']}",
                    tippss_mapping=pillars,
                    evidence=[Evidence(source=f"ai_prompt_logs[{i}]", rule=h["description"], observed=h["excerpt"],
                                       reference="OWASP Top 10 for LLM Applications — LLM01 Prompt Injection")],
                )
        await rec.note(f"{len(rec.staged)} injection pattern(s) matched across {len(ctx.prompts)} prompt(s).")


class SecretExposureAgent(Agent):
    spec = AgentSpec(
        id="secret_exposure",
        title="Secret Exposure",
        description="Searches device logs and AI prompts for leaked credentials (cloud keys, tokens, private keys).",
        layer="detection",
        reads=("device_logs", "ai_prompt_logs"),
        tools=("security.scan_secrets",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (bool(ctx.prompts or ctx.devices), "no logs supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        parts = [x if isinstance(x, str) else js_stringify(x or {}) for x in [*ctx.devices, *ctx.prompts]]
        text = "\n".join(parts)
        for h in await rec.tool("security.scan_secrets", text=text):
            rec.finding(
                severity=h["severity"], type=h["type"], detail=f"Exposed {h['type']} ({h['match_count']}x)",
                match_count=h["match_count"], tippss_mapping=patterns.SECRET_PILLARS,
                evidence=[Evidence(source="device_logs + ai_prompt_logs", rule=h["description"], observed=h["excerpt"],
                                   reference="CWE-532: Insertion of Sensitive Information into Log File")],
            )
        await rec.note(f"Scanned {len(parts)} log/prompt record(s); {len(rec.staged)} secret type(s) exposed (values masked).")


class SafetyRiskAgent(Agent):
    spec = AgentSpec(
        id="safety_risk",
        title="Clinical Safety",
        description="Flags autonomous clinical actions (dosing, discharge, alarm override, sign-off bypass) requested of AI systems.",
        layer="detection",
        reads=("ai_prompt_logs",),
        tools=("safety.scan_unsafe_instructions",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (bool(ctx.prompts), "no AI prompt logs supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        for i, p in enumerate(ctx.prompts):
            if not p:
                continue
            text = prompt_text(p, stringify_objects=False)
            for h in await rec.tool("safety.scan_unsafe_instructions", text=text):
                rec.finding(
                    severity=h["severity"], type=h["type"], detail=f"Unsafe pattern in #{i}: {h['type']}",
                    tippss_mapping=patterns.UNSAFE_PILLARS,
                    evidence=[Evidence(source=f"ai_prompt_logs[{i}]", rule=h["description"], observed=h["excerpt"],
                                       reference="IEEE 2933-2024 TIPPSS — Safety")],
                )
        await rec.note(f"{len(rec.staged)} unsafe clinical instruction(s) detected.")


class DeviceIdentityAgent(Agent):
    spec = AgentSpec(
        id="device_identity",
        title="Device Identity",
        description="Checks medical IoT device certificates and authentication outcomes.",
        layer="detection",
        reads=("device_logs",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (bool(ctx.devices), "no device logs supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        for idx, d in enumerate(ctx.devices):
            if not isinstance(d, dict):
                continue
            did = d.get("device_id") or "unknown"
            src = f"device_logs[{idx}]"
            if d.get("cert_present") is False or ("certificate" in d and d["certificate"] is None):
                rec.finding(severity="high", type="missing_certificate", detail=f"Device {did} has no certificate",
                            device_id=d.get("device_id"), tippss_mapping=["Identity", "Security"],
                            evidence=[Evidence(source=f"{src}.cert_present", rule="device must present an X.509 identity",
                                               observed=str(d.get("cert_present")), reference="IEEE 2933-2024 TIPPSS — Identity")])
            if d.get("auth_status") == "failed":
                rec.finding(severity="critical", type="authentication_failed", detail=f"Device {did} authentication failed",
                            device_id=d.get("device_id"), tippss_mapping=["Identity", "Safety"],
                            evidence=[Evidence(source=f"{src}.auth_status", rule="authentication must succeed",
                                               observed="failed", reference="IEEE 2933-2024 TIPPSS — Identity")])
            fails = d.get("failed_login_count")
            if isinstance(fails, int | float) and fails > 0:
                await rec.note(f"{did}: {fails:g} failed login attempt(s) recorded.")
        await rec.note(f"Checked {len(ctx.devices)} device record(s); {len(rec.staged)} identity finding(s).")


class TrafficAnomalyAgent(Agent):
    spec = AgentSpec(
        id="traffic_anomaly",
        title="Network Traffic Anomaly",
        description="Computes CICIoMT-style flow features from the traffic window and evaluates transparent anomaly rules "
                    "(flood, SYN flood, scan, malformed protocol, MITM-like mix).",
        layer="detection",
        reads=("iot_traffic",),
        tools=("traffic.analyze_features",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (bool(ctx.request.iot_traffic), "no iot_traffic supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        res = await rec.tool("traffic.analyze_features", iot_traffic=ctx.request.iot_traffic)
        feats = res["features"]
        ctx.artifacts["traffic_features"] = feats
        if not feats:
            await rec.note("Traffic present but no recognised flow features — nothing evaluated.")
            return
        rows = int(feats.get("rows") or (ctx.request.iot_traffic or {}).get("rows_sampled") or 0)
        await rec.note(
            f"Features: SYN {feats.get('syn_ratio', 0):.3f}, RST {feats.get('rst_ratio', 0):.3f}, "
            f"UDP {feats.get('udp_ratio', 0):.3f}, size {feats.get('tot_size_mean', 0):.0f} B, rate {feats.get('rate_mean', 0):.0f}."
        )
        for r in res["rules"]:
            if not r["hit"]:
                continue
            rec.finding(
                severity=r["severity"], type=r["type"], detail=f"{r['description']}" + (f" ({rows} rows)" if rows else ""),
                tippss_mapping=r["pillars"],
                evidence=[Evidence(source="iot_traffic", rule=f"traffic_rules:{r['type']}", observed="; ".join(r["reasons"]),
                                   reference="Heuristic rule calibrated on CICIoMT2024 (see benchmarks/)")],
            )
        await rec.note(f"{len(rec.staged)} traffic rule(s) fired." if rec.staged else "No traffic rule fired — traffic looks baseline-like.")
