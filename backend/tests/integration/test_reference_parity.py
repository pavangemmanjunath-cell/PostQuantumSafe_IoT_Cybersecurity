"""Regression parity with outputs recorded from the v0 JavaScript prototype (June 2026).

The fixtures pair an input payload with the result the prototype produced.
With the agents added in 0.1.0 disabled (traffic analysis), the Python
pipeline must reproduce findings, scores, pillar scores and the QIRO plan.
"""

from __future__ import annotations

import json

import pytest

from ..conftest import FIXTURES, assess

AGENT_RENAMES = {"pq_benchmark": "pq_identification"}
CASES = ["ARP_Spoofing_test", "Benign_test", "patients"]


def _load(name: str) -> tuple[dict, dict]:
    ref = FIXTURES / "reference"
    return (json.loads((ref / f"{name}_payload.json").read_text(encoding="utf-8")),
            json.loads((ref / f"{name}_result.json").read_text(encoding="utf-8")))


@pytest.mark.parametrize("name", CASES)
def test_parity_with_v0_reference(name: str) -> None:
    payload, expected = _load(name)
    payload["options"] = {"disabled_agents": ["traffic_anomaly"]}
    r = assess(payload)

    assert r.pq_risk_score == expected["pq_risk_score"]
    assert r.verdict == expected["verdict"]
    assert r.category_breakdown == expected["category_breakdown"]
    assert [(f.agent, f.type, f.severity, f.detail) for f in r.findings] == [
        (AGENT_RENAMES.get(f["agent"], f["agent"]), f["type"], f["severity"], f["detail"]) for f in expected["findings"]]
    assert {k: v["score"] for k, v in r.tippss_scores.items()} == {k: v["score"] for k, v in expected["tippss_scores"].items()}

    q, eq = r.qiro_optimization, expected["qiro_optimization"]
    assert [a["id"] for a in q["selected_actions"]] == [a["id"] for a in eq["selected_actions"]]
    for key in ("total_cost_usd", "total_downtime_hrs", "total_risk_reduction", "budget_remaining_usd", "message"):
        assert q[key] == eq[key], key
    if eq.get("optimization_score") is not None:
        assert q["optimization_score"] == eq["optimization_score"]


def test_traffic_agent_adds_evidence_on_attack_capture_only() -> None:
    attack, _ = _load("ARP_Spoofing_test")
    benign, _ = _load("Benign_test")
    assert [f.type for f in assess(attack).findings if f.agent == "traffic_anomaly"] == ["protocol_mix_anomaly"]
    assert [f.type for f in assess(benign).findings if f.agent == "traffic_anomaly"] == []
