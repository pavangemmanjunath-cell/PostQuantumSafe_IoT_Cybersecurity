"""Explainability outputs and LLM integration safety."""

from __future__ import annotations

import pytest

from safeguard_pq.agents import explain as explain_mod
from safeguard_pq.config import Settings
from safeguard_pq.llm import LLMError, get_provider
from safeguard_pq.llm.providers import AnthropicProvider, NullProvider, OpenAICompatibleProvider

from ..conftest import assess, scenario_request


def test_attribution_sums_to_raw_score() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    ex = r.explanation
    total = sum(a["contribution"] for a in ex["score_attribution"])
    assert total == pytest.approx(ex["raw_score"]) == pytest.approx(61.25)
    assert round(sum(a["share_pct"] for a in ex["score_attribution"])) == 100


def test_every_finding_has_evidence_and_a_remediation_decision() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    for f in r.explanation["findings"]:
        assert f["evidence"], f["finding_id"]
        assert f["remediation"]["decision"] in ("selected", "deferred")


def test_counterfactuals_and_plan_projection() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    cfs = {c["removed_type"]: c for c in r.explanation["counterfactuals"]}
    # removing the HNDL finding drops the lifetime category: 61.25 - 20 = 41.25 → 41
    assert cfs["long_lifetime_classical_crypto"]["after"]["pq_risk_score"] == 41
    proj = r.explanation["plan_projection"]
    assert proj["after"]["pq_risk_score"] <= proj["before"]["pq_risk_score"]


def test_pillar_deductions_explain_scores() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    for pillar, info in r.explanation["pillars"].items():
        assert info["score"] == max(0, 100 - sum(d["points"] for d in info["deductions"])), pillar


def test_agent_reasoning_is_attached() -> None:
    r = assess(scenario_request("ehr_tls13_classical"))
    agents = [a["agent"] for a in r.explanation["agent_reasoning"]]
    assert "pq_identification" in agents
    pq_notes = next(a["notes"] for a in r.explanation["agent_reasoning"] if a["agent"] == "pq_identification")
    assert any("PQ readiness" in n for n in pq_notes)


def test_provider_selection() -> None:
    assert isinstance(get_provider(Settings(_env_file=None)), NullProvider)
    assert isinstance(get_provider(Settings(_env_file=None, llm_provider="anthropic")), NullProvider)  # no model → disabled
    assert isinstance(get_provider(Settings(_env_file=None, llm_provider="anthropic", llm_model="m")), AnthropicProvider)
    assert isinstance(get_provider(Settings(_env_file=None, llm_provider="openai_compatible", llm_model="m")),
                      OpenAICompatibleProvider)


class _Capture:
    name, model = "fake", "fake-model"

    def __init__(self, fail: bool = False) -> None:
        self.fail, self.prompts = fail, []

    async def complete(self, system: str, user: str) -> str:
        self.prompts.append(user)
        if self.fail:
            raise LLMError("offline")
        return "## LLM summary\nAll good."


def test_llm_receives_only_redacted_aggregates(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = _Capture()
    monkeypatch.setattr(explain_mod, "get_provider", lambda s: cap)
    r = assess(scenario_request("clinical_ai_phi"))
    assert r.report["generator"] == "llm" and r.report["llm_model"] == "fake-model"
    sent = cap.prompts[0]
    for raw in ("Maria Santos", "4421867", "billing@hospital-vendor.com", "Ignore all previous"):
        assert raw not in sent


def test_llm_failure_falls_back_to_deterministic_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(explain_mod, "get_provider", lambda s: _Capture(fail=True))
    r = assess(scenario_request("icu_gateway_critical"))
    assert r.report["generator"] == "deterministic-template"
    assert r.report["llm_error"] == "offline"
    assert "Environment status: UNSAFE" in r.report["markdown"]


def test_llm_can_be_turned_off_per_request(monkeypatch: pytest.MonkeyPatch) -> None:
    cap = _Capture()
    monkeypatch.setattr(explain_mod, "get_provider", lambda s: cap)
    r = assess(scenario_request("icu_gateway_critical") | {"options": {"llm_report": False}})
    assert cap.prompts == [] and r.report["generator"] == "deterministic-template"
