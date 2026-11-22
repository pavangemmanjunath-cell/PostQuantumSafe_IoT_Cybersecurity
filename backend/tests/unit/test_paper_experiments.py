"""benchmarks/paper_experiments.py: every number the revised paper states for E1-E5 is reproduced by the shipped software."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
BENCH = ROOT / "benchmarks"
RESULTS = BENCH / "results"
VOLATILE = ("date", "python", "software_version")

# Listing 1 of the original draft (the worked example of Section III).
LISTING_1 = {
    "system_id": "ICU-PUMP-GW",
    "tls_config": {"tls_version": "TLS1.2", "key_exchange": "ECDHE-P256", "cert_signature_algo": "ECDSA-P256",
                   "data_lifetime_years": 25},
    "assumptions": {"migration_years": 5, "years_to_crqc": 10},
    "constraints": {"budget_usd": 60000, "max_downtime_hrs": 12},
}
# The 'defended profile' of the v0.1.0 experiment script behind the draft's E2 and E3 numbers.
V010_DEFENCE = {"tls_version": "TLS1.3", "key_exchange": "X25519MLKEM768", "cert_signature_algo": "ML-DSA-65",
                "cert_key_algo": "ML-DSA-65", "symmetric_cipher": "AES-256-GCM", "hash": "SHA-384"}


@pytest.fixture(scope="module")
def pe():
    if str(BENCH) not in sys.path:
        sys.path.insert(0, str(BENCH))
    return importlib.import_module("paper_experiments")


@pytest.fixture(scope="module")
def artifacts(pe) -> dict[str, dict[str, Any]]:
    return pe.run(list(pe.EXPERIMENTS))


@pytest.mark.parametrize("key", ["e1", "e2", "e3", "e4", "e5"])
def test_every_stated_value_is_reproduced(artifacts: dict[str, dict[str, Any]], key: str) -> None:
    data = artifacts[key]
    for field in ("software_version", "python", "seed", "inputs", "method", "results", "paper_check", "date"):
        assert field in data, field
    assert data["seed"] == 2026 and data["paper_experiment"] == key.upper()
    block = data["paper_check"]
    mismatches = [(c["id"], c["expected"], c["reproduced"]) for c in block["checks"] if not c["match"]]
    assert mismatches == []
    assert block["summary"]["all_match"] is True and block["summary"]["stated_values"] == len(block["checks"]) > 0
    assert all({"id", "source", "statement", "expected", "reproduced", "match"} <= set(c) for c in block["checks"])


def test_paper_check_covers_every_cell_of_table_ii(artifacts: dict[str, dict[str, Any]]) -> None:
    ids = {c["id"] for c in artifacts["e1"]["paper_check"]["checks"]}
    cells = [i for i in ids if i.startswith("E1.table_ii.")]
    assert len(cells) == 10 * 11  # ten systems x (PQ, S, status, M, P, findings, critical, plan, proj. S, reass. S, status)
    for scenario in ("icu_gateway_critical", "hybrid_transition", "infusion_syn_flood"):
        assert f"E1.table_ii.{scenario}.reassessed_status" in ids


def test_committed_artifacts_match_a_fresh_run(pe, artifacts: dict[str, dict[str, Any]]) -> None:
    for key, name in pe.ARTIFACTS.items():
        committed = json.loads((RESULTS / name).read_text(encoding="utf-8"))
        fresh = json.loads(json.dumps(artifacts[key], ensure_ascii=False))
        for field in VOLATILE:
            committed.pop(field), fresh.pop(field)
        assert committed == fresh, f"{name} is out of date: run python benchmarks/paper_experiments.py"


def test_e2_conditions_are_the_simulator_attacks_and_the_v0_1_0_profiles(pe, artifacts: dict[str, dict[str, Any]]) -> None:
    spec = json.loads(pe.E2_FILE.read_text(encoding="utf-8"))
    migrated = pe.migrated_gateway(spec["base_gateway"], spec["countermeasures"])
    assert {k: migrated["tls_config"][k] for k in V010_DEFENCE} == V010_DEFENCE
    conditions = artifacts["e2"]["results"]["conditions"]
    assert [c["id"] for c in conditions] == [c["id"] for c in spec["conditions"]]
    assert [c["simulator_attack"] for c in conditions] == [None, "hndl_capture", "tls_downgrade", "pq_strip", "cert_spoof",
                                                           "pq_downgrade_prompt"]
    for c in conditions[1:]:
        assert c["simulator_effect"]["matches_condition"] is True and c["simulator_effect"]["blocked"] is False, c["id"]
    # the countermeasures turn every attacked configuration into the v0.1.0 defended profile
    actions = pe.countermeasure_actions(spec["countermeasures"])
    for c in conditions:
        req, _ = pe.apply_plan(pe.AssessmentRequest.model_validate(c["configuration"]), actions)
        assert {k: getattr(req.tls_config, k) for k in V010_DEFENCE} == V010_DEFENCE, c["id"]
        assert all(d["auth_status"] == "passed" and d["cert_present"] and not d["failed_login_count"] for d in req.device_logs)
        assert req.ai_prompt_logs == spec["base_gateway"]["ai_prompt_logs"]


def test_worked_example_file_is_listing_1(pe) -> None:
    assert json.loads(pe.WORKED_EXAMPLE_FILE.read_text(encoding="utf-8")) == LISTING_1


def test_e3_uses_seven_data_classes_and_three_migration_times(artifacts: dict[str, dict[str, Any]]) -> None:
    res = artifacts["e3"]["results"]
    assert res["lifetimes"] == [5, 8, 10, 15, 20, 25, 30] and res["horizons"] == list(range(4, 31, 2))
    assert [s["migration_years"] for s in res["series"]] == [2, 5, 8, 8]
    assert res["series"][-1]["key_exchange"] == "X25519MLKEM768"


def test_e4_solver_quality_artifact_matches_table_iii() -> None:
    """The other half of paper E4 (500 instances, exhaustive optimum) lives in qiro_optimality.json."""
    q = json.loads((RESULTS / "qiro_optimality.json").read_text(encoding="utf-8"))
    assert q["instances_with_nonzero_optimum"] == 500
    sa, ls = q["annealing_only"], q["annealing_plus_local_search"]
    assert (round(100 * sa["optimal_share"], 1), round(sa["mean_gap_pct"], 3), round(sa["max_gap_pct"], 2)) == (94.8, 0.191, 20.16)
    assert (round(100 * ls["optimal_share"], 1), round(ls["mean_gap_pct"], 3), round(ls["max_gap_pct"], 2)) == (97.6, 0.053, 6.06)


def test_main_writes_only_the_selected_artifacts(pe, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert pe.main(["--only", "e5,e4", "--out-dir", str(tmp_path), "--strict"]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["paper_e4_budget_sweep.json", "paper_e5_worked_example.json"]
    out = capsys.readouterr().out
    assert "E4" in out and "E5" in out and "all stated values reproduced" in out
    with pytest.raises(SystemExit):
        pe.main(["--only", "e9"])


def test_same_compares_numbers_by_value_but_booleans_strictly(pe) -> None:
    assert pe.same(8, 8.0) and pe.same([0, 0], [0.0, 0]) and pe.same({"a": 46.25}, {"a": 46.25})
    assert not pe.same(1, True) and not pe.same(False, 0) and not pe.same([1], [1, 2]) and not pe.same({"a": 1}, {"b": 1})
