"""Parameterised scoring constants, the adjustable lifetime threshold, and the sensitivity benchmark.

The benchmark lives outside the package (benchmarks/ is not a package), so its modules are loaded by path.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError

from safeguard_pq.agents import scoring
from safeguard_pq.domain.models import Assumptions
from safeguard_pq.optimizer import qiro

from ..conftest import assess, scenario_request, types

BENCHMARKS = Path(__file__).resolve().parents[3] / "benchmarks"
CLASSICAL_8Y = {
    "system_id": "EHR-8Y",
    "tls_config": {"tls_version": "TLS1.3", "key_exchange": "ECDHE-P384", "cert_signature_algo": "ECDSA-P384",
                   "cert_key_algo": "ECDSA-P384", "symmetric_cipher": "AES-256-GCM", "hash": "SHA-384",
                   "data_lifetime_years": 8},
}


def load_benchmark_module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, BENCHMARKS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- (a) parameterised scoring


def test_parameterised_scoring_with_explicit_defaults_equals_default_result() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    findings, pq = r.findings, bool(r.pq_posture["pq_detected"])
    default = scoring.pq_score(findings, pq)
    assert scoring.pq_score(findings, pq, weights=dict(scoring.WEIGHTS), points=dict(scoring.POINTS)) == default
    assert scoring.tippss_pillars(findings, deduct=dict(scoring.PILLAR_DEDUCT)) == scoring.tippss_pillars(findings)
    assert default["pq_risk_score"] == r.pq_risk_score == 61


def test_alternative_constant_tables_change_the_result_predictably() -> None:
    r = assess(scenario_request("icu_gateway_critical"))
    findings, pq = r.findings, bool(r.pq_posture["pq_detected"])
    base = scoring.pq_score(findings, pq)
    doubled = scoring.pq_score(findings, pq, weights={k: 2 * v for k, v in scoring.WEIGHTS.items()})
    assert doubled["raw_score"] == pytest.approx(2 * base["raw_score"])
    assert doubled["category_breakdown"] == base["category_breakdown"]
    # severity points enter every category except the fixed 75-point migration posture value
    scaled = scoring.pq_score(findings, pq, points={k: 0.5 * v for k, v in scoring.POINTS.items()})
    assert scaled["category_breakdown"]["pkc"] == base["category_breakdown"]["pkc"] / 2
    assert scaled["category_breakdown"]["migration"] == base["category_breakdown"]["migration"] == 75
    halved = scoring.tippss_pillars(findings, deduct={k: v / 2 for k, v in scoring.PILLAR_DEDUCT.items()})
    full = scoring.tippss_pillars(findings)
    assert all(halved[p]["score"] >= full[p]["score"] for p in full)
    assert halved["Protection"]["score"] > full["Protection"]["score"]
    assert scoring.WEIGHTS == {"pkc": 0.30, "tls": 0.20, "lifetime": 0.20, "identity": 0.15, "secrets": 0.10, "migration": 0.05}


# --------------------------------------------------------------------------- (b) lifetime threshold


def test_lifetime_threshold_default_is_ten_years_and_adjustable() -> None:
    default = assess(CLASSICAL_8Y)
    assert "long_lifetime_classical_crypto" not in types(default)
    assert "mosca_hndl_exposure" in types(default)  # 8 + 5 > 10 under the default Q-Day assumptions
    assert default.metadata["assumptions"]["lifetime_threshold_years"] == 10

    lowered = assess(CLASSICAL_8Y | {"assumptions": {"lifetime_threshold_years": 5}})
    assert "long_lifetime_classical_crypto" in types(lowered)
    assert "mosca_hndl_exposure" not in types(lowered)  # the critical rule supersedes the Mosca what-if
    hndl = next(f for f in lowered.findings if f.type == "long_lifetime_classical_crypto")
    assert hndl.severity == "critical"
    assert hndl.evidence[0].rule == "lifetime ≥ 5 years with classical public-key crypto"
    assert lowered.metadata["assumptions"]["lifetime_threshold_years"] == 5
    # pkc 75·.3 + lifetime 100·.2 + migration 75·.05 = 46.25 → 46, and the critical finding makes it UNSAFE
    assert (lowered.pq_risk_score, lowered.environment_status) == (46, "UNSAFE")
    assert (default.pq_risk_score, default.environment_status) == (26, "AT_RISK")


def test_assumptions_accept_simulator_payload_and_reject_out_of_range_threshold() -> None:
    assert Assumptions().lifetime_threshold_years == 10
    sim_shape = Assumptions.model_validate({"migration_years": 5.0, "years_to_crqc": 10.0})
    assert sim_shape.lifetime_threshold_years == 10
    assert Assumptions(lifetime_threshold_years=0).lifetime_threshold_years == 0
    with pytest.raises(ValidationError):
        Assumptions(lifetime_threshold_years=101)
    with pytest.raises(ValidationError):
        Assumptions(lifetime_threshold_years=-1)


# --------------------------------------------------------------------------- (c) statistics helpers


def test_spearman_with_average_ranks_and_jaccard() -> None:
    st = load_benchmark_module("_stats")
    assert st.average_ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]
    assert st.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert st.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert st.spearman([1, 2, 2, 3], [1, 3, 2, 4]) == pytest.approx(3 / math.sqrt(10))  # tie -> average rank 2.5
    assert st.spearman([5, 5, 5], [1, 2, 3]) is None  # undefined without rank variance
    assert st.spearman([1], [2]) is None
    with pytest.raises(ValueError):
        st.spearman([1, 2], [1])
    assert st.jaccard({"a", "b", "c"}, {"b", "c", "d"}) == pytest.approx(0.5)
    assert st.jaccard(["F1", "F2"], ["F2", "F1", "F1"]) == 1.0
    assert st.jaccard([], []) == 1.0
    assert st.jaccard(["F1"], []) == 0.0


# --------------------------------------------------------------------------- (d) benchmark end to end


def test_sensitivity_benchmark_runs_end_to_end(tmp_path: Path) -> None:
    sa = load_benchmark_module("sensitivity_analysis")
    out = tmp_path / "sensitivity_analysis.json"
    original_weights = dict(qiro.PILLAR_WEIGHTS)

    assert sa.main(["--out", str(out), "--seed", "2026"]) == 0

    assert qiro.PILLAR_WEIGHTS == original_weights  # S5 restores the patched module constant
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["benchmark"] == "scoring_sensitivity" and d["assessment_seed"] == 2026
    assert len(d["scenarios"]) == len(d["baseline"]) == 10
    assert set(d) >= {"software_version", "date", "python", "designs", "method", "caveat"}
    icu = next(b for b in d["baseline"] if b["scenario"] == "icu_gateway_critical")
    assert (icu["pq_risk_score"], icu["verdict"], icu["environment_status"]) == (61, "Not Post-Quantum Safe", "UNSAFE")
    assert icu["selected_action_finding_ids"] and icu["findings"] == 8

    designs = d["designs"]
    assert len(designs["S1_category_weights"]) == 12 and len(designs["S2_severity_points"]) == 2
    assert len(designs["S3_pillar_deductions"]) == 2 and len(designs["S5_optimizer_pillar_weights"]) == 2
    for row in designs["S1_category_weights"]:
        assert sum(row["weights"].values()) == pytest.approx(1.0, abs=1e-3)
        assert row["metrics"]["mean_plan_jaccard"] is None  # plans are not recomputed in S1
    s4 = designs["S4_lifetime_threshold"]
    assert [c["lifetime_threshold_years"] for c in s4["configs"]] == [5, 10, 15, 20]
    assert next(c for c in s4["configs"] if c["lifetime_threshold_years"] == 10)["identical_to_baseline"] is True
    assert len(s4["per_scenario"]) == 10 and set(s4["per_scenario"][0]["by_threshold"]) == {"5", "10", "15", "20"}
    rows = designs["S1_category_weights"] + designs["S2_severity_points"] + designs["S3_pillar_deductions"]
    rows += s4["configs"] + designs["S5_optimizer_pillar_weights"]
    for row in rows:
        m = row["metrics"]
        assert 0 <= m["verdict_change_share"] <= 1 and 0 <= m["status_change_share"] <= 1
        assert 0 <= m["mean_abs_delta_score"] <= m["max_abs_delta_score"] <= 100
        assert m["spearman_rank_correlation"] is None or -1 <= m["spearman_rank_correlation"] <= 1
    for row in s4["configs"] + designs["S5_optimizer_pillar_weights"]:
        assert 0 <= row["metrics"]["mean_plan_jaccard"] <= 1
    for row in designs["S3_pillar_deductions"]:
        assert row["pillar_metrics"]["max_abs_delta_pillar_score"] >= row["pillar_metrics"]["mean_abs_delta_pillar_score"] >= 0
