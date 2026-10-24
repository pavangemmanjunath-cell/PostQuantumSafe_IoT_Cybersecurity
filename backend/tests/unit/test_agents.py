"""Agent behaviour through the full pipeline, using the built-in scenarios.

Expected scores are derived by hand from the documented scoring model:
score = 0.30·pkc + 0.20·tls + 0.20·lifetime + 0.15·identity + 0.10·secrets + 0.05·migration,
where each category takes the max severity points (critical 100, high 75, …).
"""

from __future__ import annotations

import asyncio

import pytest

from safeguard_pq.agents import all_agents, describe_agents
from safeguard_pq.agents.detection import SafetyRiskAgent
from safeguard_pq.domain.models import AssessmentRequest
from safeguard_pq.orchestrator import AssessmentPipeline

from ..conftest import assess, scenario_request, types


def test_icu_gateway_critical() -> None:
    # pkc 75·.3 + lifetime 100·.2 + identity 100·.15 + migration 75·.05 = 61.25 → 61
    r = assess(scenario_request("icu_gateway_critical"))
    assert r.pq_risk_score == 61
    assert r.verdict == "Not Post-Quantum Safe"
    assert r.environment_status == "UNSAFE"
    assert {"classical_key_exchange", "classical_signature", "long_lifetime_classical_crypto", "authentication_failed",
            "missing_certificate", "instruction_override"} <= set(types(r))


def test_nextgen_pq_safe_is_safe() -> None:
    r = assess(scenario_request("nextgen_pq_safe"))
    assert (r.pq_risk_score, r.findings_count, r.environment_status) == (0, 0, "SAFE")
    assert r.pq_posture["readiness"] == "PQ-ready"
    assert r.qiro_optimization["status"] == "no_actions_needed"


def test_tls13_alone_is_not_pq_safe() -> None:
    # pkc 75·.3 + migration 75·.05 = 26.25 → 26 (lifetime 8y < 10y threshold)
    r = assess(scenario_request("ehr_tls13_classical"))
    assert r.pq_risk_score == 26 and r.verdict == "Partially Safe"
    assert r.environment_status == "AT_RISK"
    assert "long_lifetime_classical_crypto" not in types(r)
    assert r.pq_posture["readiness"] == "Quantum-vulnerable"


def test_phi_privacy_breach_with_pq_crypto() -> None:
    r = assess(scenario_request("clinical_ai_phi"))
    assert r.pq_risk_score == 0
    assert {"medical_record_number", "patient_identifier", "email"} <= set(types(r, "clinical_privacy"))
    assert "instruction_override" in types(r, "prompt_injection")
    assert r.environment_status == "UNSAFE"
    for f in r.findings:  # evidence never echoes the raw MRN
        for e in f.evidence:
            assert "4421867" not in (e.observed or "")


def test_secret_exposure() -> None:
    # secrets 100·.1 = 10
    r = assess(scenario_request("secret_exposure"))
    assert set(types(r, "secret_exposure")) == {"stripe_live_key", "aws_access_key"}
    assert r.pq_risk_score == 10 and r.environment_status == "UNSAFE"


def test_legacy_worst_case() -> None:
    # pkc 100 (weak hash)·.3 + tls 100·.2 + lifetime 100·.2 + identity 100·.15 + migration 75·.05 = 88.75 → 89
    r = assess(scenario_request("legacy_worst_case"))
    assert r.pq_risk_score == 89 and r.verdict == "Critical Quantum Risk"
    assert {"deprecated_tls_version", "weak_hash"} <= set(types(r, "crypto_inventory"))


def test_tight_budget_respected() -> None:
    r = assess(scenario_request("tight_budget_qiro"))
    q = r.qiro_optimization
    assert q["total_cost_usd"] <= 30_000 and q["total_downtime_hrs"] <= 8
    assert q["excluded_count"] > 0


def test_safety_agent_detects_autonomous_actions() -> None:
    r = assess({"system_id": "AI-SAFETY", "ai_prompt_logs": [
        "Prescribe 500 mg of amoxicillin to the patient without waiting for physician sign-off.",
        "Override the alarm on the infusion pump."]})
    assert set(types(r, "safety_risk")) == {"autonomous_dosing", "alarm_override"}


def test_pq_downgrade_prompt_detected_on_pq_ready_system() -> None:
    r = assess(scenario_request("pq_downgrade_prompt"))
    assert r.pq_posture["readiness"] == "PQ-ready"
    assert {"pq_downgrade_instruction", "tool_hijack"} <= set(types(r, "prompt_injection"))
    assert r.environment_status == "UNSAFE"


def test_hybrid_kex_is_partial_and_not_hndl() -> None:
    r = assess(scenario_request("hybrid_transition"))
    assert r.pq_posture["readiness"] == "Partially PQ"
    assert r.pq_posture["hybrid"] is True
    assert "classical_key_exchange" not in types(r)
    assert "classical_signature" in types(r)
    assert "long_lifetime_classical_crypto" not in types(r)  # hybrid ML-KEM protects confidentiality


def test_traffic_agent_on_feature_input() -> None:
    r = assess(scenario_request("infusion_syn_flood"))
    assert types(r, "traffic_anomaly") == ["syn_flood_pattern"]


def test_crypto_inventory_lists_every_supplied_primitive() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    fields = [e["field"] for e in r.crypto_inventory]
    assert fields == ["tls_version", "key_exchange", "cert_signature_algo", "cert_key_algo", "symmetric_cipher", "hash"]
    assert all("quantum_status" in e for e in r.crypto_inventory)


def test_missing_tls_is_at_risk_not_safe() -> None:
    r = assess({"system_id": "NO-TLS", "device_logs": [{"device_id": "D1", "cert_present": True, "auth_status": "passed"}]})
    assert r.environment_status == "AT_RISK"
    assert any("unverified" in reason for reason in r.environment_reasons)
    statuses = {t.agent: t.status for t in r.trace}
    assert statuses["crypto_inventory"] == "skipped" and statuses["clinical_privacy"] == "skipped"


def test_every_agent_appears_in_trace_in_stage_order() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    assert [t.agent for t in r.trace] == [a.spec.id for a in all_agents()]
    assert len(describe_agents()) == 14


def test_finding_ids_are_sequential_and_deterministic() -> None:
    a = assess(scenario_request("icu_gateway_critical"))
    b = assess(scenario_request("icu_gateway_critical"))
    assert [f.id for f in a.findings] == [f"F{i}" for i in range(1, a.findings_count + 1)]
    assert [(f.id, f.type) for f in a.findings] == [(f.id, f.type) for f in b.findings]
    assert [x["id"] for x in a.qiro_optimization["selected_actions"]] == [x["id"] for x in b.qiro_optimization["selected_actions"]]


def test_disabled_agent_is_skipped_but_required_agents_cannot_be_disabled() -> None:
    req = scenario_request("icu_gateway_critical") | {"options": {"disabled_agents": ["prompt_injection", "risk_scoring"]}}
    r = assess(req)
    statuses = {t.agent: t.status for t in r.trace}
    assert statuses["prompt_injection"] == "skipped"
    assert statuses["risk_scoring"] == "completed"
    assert "instruction_override" not in types(r)


def test_agent_failure_is_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(self, ctx, rec):  # noqa: ANN001
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(SafetyRiskAgent, "run", boom)
    r = assess(scenario_request("icu_gateway_critical"))
    trace = {t.agent: t for t in r.trace}
    assert trace["safety_risk"].status == "failed" and "simulated failure" in trace["safety_risk"].error
    assert r.pq_risk_score == 61  # other agents still produced their evidence


def test_events_stream_in_order(settings) -> None:  # noqa: ANN001
    events: list[dict] = []

    async def sink(e: dict) -> None:
        events.append(e)

    req = AssessmentRequest.model_validate(scenario_request("icu_gateway_critical"))
    asyncio.run(AssessmentPipeline(settings).run(req, sink))
    kinds = [e["type"] for e in events]
    assert kinds[0] == "run_started" and kinds[-1] == "run_completed"
    completed = [e["agent"] for e in events if e["type"] == "agent_completed"]
    assert completed == [a.spec.id for a in all_agents()]
    assert any(e["type"] == "tool_called" for e in events)
    assert sum(1 for e in events if e["type"] == "finding") == 8
