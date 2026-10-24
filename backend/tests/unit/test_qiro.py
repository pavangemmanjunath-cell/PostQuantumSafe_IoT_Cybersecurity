"""QIRO optimizer: determinism, feasibility and gap to the exact optimum."""

from __future__ import annotations

import random

import pytest

from safeguard_pq.knowledge.remediation import ACTION_TEMPLATES
from safeguard_pq.optimizer import qiro

TYPES = sorted(ACTION_TEMPLATES)
SEVS = ["critical", "high", "medium", "low"]
PILLARS = ["Trust", "Identity", "Privacy", "Protection", "Safety", "Security"]


def random_findings(rng: random.Random, n: int) -> list[dict]:
    return [{"id": f"F{i + 1}", "agent": rng.choice(["crypto_inventory", "clinical_privacy", "device_identity", "safety_risk"]),
             "type": rng.choice(TYPES), "severity": rng.choice(SEVS), "detail": "x",
             "tippss_mapping": rng.sample(PILLARS, rng.randint(1, 3))} for i in range(n)]


def test_empty_findings() -> None:
    r = qiro.optimize([], 50_000, 10, seed=1)
    assert r["status"] == "no_actions_needed" and r["selected_actions"] == []
    assert r["budget_remaining_usd"] == 50_000


def test_js_round_semantics() -> None:
    assert qiro.js_round(2.5) == 3 and qiro.js_round(-2.5) == -2 and qiro.js_round(61.25) == 61


def test_same_seed_same_plan() -> None:
    f = random_findings(random.Random(3), 12)
    a = qiro.optimize(f, 60_000, 15, seed=42)
    b = qiro.optimize(f, 60_000, 15, seed=42)
    assert [x["id"] for x in a["selected_actions"]] == [x["id"] for x in b["selected_actions"]]


@pytest.mark.parametrize("seed", range(25))
def test_plan_is_always_feasible_and_near_optimal(seed: int) -> None:
    rng = random.Random(seed)
    n = rng.randint(3, 12)
    budget, downtime = rng.choice([20_000, 50_000, 100_000]), rng.choice([4, 10, 40])
    r = qiro.optimize(random_findings(rng, n), budget, downtime, seed=seed)
    assert r["total_cost_usd"] <= budget and r["total_downtime_hrs"] <= downtime
    assert r["selection_count"] + r["excluded_count"] == n
    opt = r["optimality"]
    assert opt["exact_objective"] is not None
    assert opt["heuristic_objective"] <= opt["exact_objective"] + 1e-9
    assert opt["heuristic_objective"] >= opt["annealing_objective"]


def test_tight_budget_defers_expensive_actions_with_reason() -> None:
    findings = [{"id": "F1", "agent": "pq_identification", "type": "pq_migration_required", "severity": "high",
                 "detail": "RSA", "tippss_mapping": ["Security"]},
                {"id": "F2", "agent": "secret_exposure", "type": "aws_access_key", "severity": "critical",
                 "detail": "key", "tippss_mapping": ["Protection"]}]
    r = qiro.optimize(findings, 10_000, 40, seed=1)
    assert [a["finding_type"] for a in r["selected_actions"]] == ["aws_access_key"]
    assert "exceeds the total available budget" in r["excluded_actions"][0]["reason"]


def test_large_instance_skips_exact_solver() -> None:
    r = qiro.optimize(random_findings(random.Random(9), qiro.EXACT_SOLVER_MAX_N + 6), 200_000, 60, seed=1)
    assert r["optimality"]["exact_objective"] is None
    assert r["total_cost_usd"] <= 200_000


def test_phase_plan_partitions_selected_actions() -> None:
    r = qiro.optimize(random_findings(random.Random(5), 10), 500_000, 200, seed=5)
    phased = sum(len(v) for v in r["migration_phase_plan"].values())
    assert phased == r["selection_count"]
    ids = [a["id"] for v in r["migration_phase_plan"].values() for a in v]
    assert len(ids) == len(set(ids))
    for a in r["migration_phase_plan"]["phase_1_immediate_0_6mo"]:
        assert a["severity"] == "critical" or a["pqc_urgency"] >= 25
