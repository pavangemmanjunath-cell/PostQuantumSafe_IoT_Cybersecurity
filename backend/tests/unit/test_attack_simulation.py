"""Attacker-vs-defender simulation benchmark (benchmarks/attack_simulation_eval.py)."""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

BENCH = Path(__file__).resolve().parents[3] / "benchmarks"


@pytest.fixture(scope="module")
def sim_eval():
    if str(BENCH) not in sys.path:
        sys.path.insert(0, str(BENCH))
    return importlib.import_module("attack_simulation_eval")


def _keys(obj: Any, found: set[str]) -> set[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            _keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, found)
    return found


def test_syn_flood_on_pump_is_detected_and_blocked_after_mitigation(sim_eval) -> None:
    r = asyncio.run(sim_eval.run_one(7, "PUMP-ICU-A12", "syn_flood"))
    assert r["outcome"] == "exploitable" and r["detected"] is True
    assert "traffic_anomaly:syn_flood_pattern" in r["new_finding_types"]
    assert r["mitigations_applied"] == ["rate_limiting"] and r["mitigations_skipped"] == []
    assert r["reinjection_blocked"] is True and r["attack_active_after_mitigation"] is False
    assert "traffic_anomaly:syn_flood_pattern" in r["finding_types_removed_by_mitigation"]
    assert r["attack_succeeded_undetected"] is False
    assert r["after_attack"]["status"] == "UNSAFE"


def test_hndl_capture_on_pq_gateway_has_no_preconditions(sim_eval) -> None:
    r = asyncio.run(sim_eval.run_one(7, "GW-EDGE-01", "hndl_capture"))
    assert r["outcome"] == "preconditions_absent" and "PQ-safe" in r["precondition_note"]
    assert r["attack_succeeded_undetected"] is False  # not counted as an undetected success
    assert r["reinjection_blocked"] is True  # key exchange is PQ-safe after (and before) mitigation


def test_ai_attacks_apply_to_ai_devices_only(sim_eval) -> None:
    from safeguard_pq.simulation import catalog as cat

    tpl = cat.TEMPLATES["hospital_ward"]
    assert sim_eval.applicable_devices(tpl, cat.ATTACKS["prompt_injection"]) == ["AI-ASSIST-01"]
    assert len(sim_eval.applicable_devices(tpl, cat.ATTACKS["syn_flood"])) == 9


def test_main_runs_filtered_and_is_deterministic(sim_eval, tmp_path) -> None:
    out = tmp_path / "attack_simulation.json"
    argv = ["--seeds", "7", "--attacks", "syn_flood", "--devices", "PUMP-ICU-A12", "--out", str(out)]
    assert sim_eval.main(argv) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["benchmark"] == "attack_simulation_hospital_ward" and r["seeds"] == [7]
    assert r["attack_filter"] == ["syn_flood"] and r["device_filter"] == ["PUMP-ICU-A12"]
    assert len(r["runs"]) == 1 and r["runs"][0]["detected"] is True
    a = r["attacks"]["syn_flood"]
    assert a["detection_rate"] == 1.0 and a["reinjection_blocked_rate"] == 1.0 and a["exploitable_runs"] == 1
    assert r["attack_device_table"][0]["detected_runs"] == 1
    assert [s["id"] for s in r["kill_chain"]["steps"]] == [s["id"] for s in sim_eval.DRILL_STEPS]
    assert len(r["kill_chain"]["trajectory"]) == 8 and r["kill_chain"]["drill_device"] == "ECG-ICU-007"
    assert not {"ts", "timestamp", "created_at", "assessment_id", "simulation_id"} & _keys(r["runs"] + r["kill_chain"]["steps"], set())
    assert "synthetic" in r["caveat"].lower()

    out2 = tmp_path / "again.json"
    assert sim_eval.main([*argv[:-1], str(out2)]) == 0
    a1, a2 = json.loads(out.read_text(encoding="utf-8")), json.loads(out2.read_text(encoding="utf-8"))
    assert a1["runs"] == a2["runs"] and a1["kill_chain"] == a2["kill_chain"]


def test_main_rejects_unknown_filters(sim_eval, tmp_path) -> None:
    assert sim_eval.main(["--attacks", "nope", "--out", str(tmp_path / "x.json")]) == 2
    assert sim_eval.main(["--devices", "NOPE", "--out", str(tmp_path / "x.json")]) == 2
    assert sim_eval.main(["--template", "nope", "--out", str(tmp_path / "x.json")]) == 2
