"""The standards map must stay consistent with the rules the agents actually apply."""

from __future__ import annotations

from fastapi.testclient import TestClient

from safeguard_pq.agents.scoring import PILLAR_DEDUCT, WEIGHTS
from safeguard_pq.api.app import create_app
from safeguard_pq.domain.models import PILLARS
from safeguard_pq.knowledge import patterns, standards_map, traffic_rules

CRYPTO_TYPES = {
    "deprecated_tls_version": "critical", "classical_key_exchange": "high", "classical_signature": "high",
    "classical_certificate_key": "high", "weak_hash": "critical", "weak_symmetric_cipher": "high",
    "pq_migration_required": "high", "long_lifetime_classical_crypto": "critical", "mosca_hndl_exposure": "medium",
}
IDENTITY_TYPES = {"missing_certificate": "high", "authentication_failed": "critical"}


def test_every_pattern_rule_is_mapped_with_matching_severity_and_pillars() -> None:
    expected_pillars = {
        "phi": tuple(patterns.PHI_PILLARS), "injection": tuple(patterns.INJECTION_PILLARS),
        "secrets": tuple(patterns.SECRET_PILLARS), "unsafe": tuple(patterns.UNSAFE_PILLARS),
    }
    for table, pillars in expected_pillars.items():
        for rule in patterns.rule_table(table):
            row = standards_map.BY_TYPE[rule.type]
            if rule.type == "pq_downgrade_instruction":
                assert row.pillars == tuple(patterns.PQ_INJECTION_PILLARS)
            else:
                assert row.pillars == pillars, rule.type
            # the privacy agent raises every PHI type as "high" except sensitive_diagnosis (critical)
            expected = ("critical" if rule.type == "sensitive_diagnosis" else "high") if table == "phi" else rule.severity
            assert row.severity == expected, rule.type


def test_traffic_crypto_and_identity_types_are_mapped() -> None:
    for rule in traffic_rules.TRAFFIC_RULES:
        row = standards_map.BY_TYPE[rule.type]
        assert row.severity == rule.severity and row.pillars == rule.pillars
    for t, sev in CRYPTO_TYPES.items():
        assert standards_map.BY_TYPE[t].severity == sev
    for t, sev in IDENTITY_TYPES.items():
        assert standards_map.BY_TYPE[t].severity == sev


def test_deductions_weights_and_pillars_are_consistent() -> None:
    for row in standards_map.STANDARDS_MAP:
        assert row.pillar_deduction == PILLAR_DEDUCT[row.severity]
        assert set(row.pillars) <= set(PILLARS) and row.pillars
        assert row.references, row.finding_type
        if row.score_category:
            assert row.score_weight == WEIGHTS[row.score_category]
    assert len({r.finding_type for r in standards_map.STANDARDS_MAP}) == len(standards_map.STANDARDS_MAP)
    coverage = standards_map.pillar_coverage()
    assert all(coverage[p]["finding_types"] > 0 for p in PILLARS)


def test_markdown_table_and_api() -> None:
    md = standards_map.markdown_table()
    assert md.count("\n") == len(standards_map.STANDARDS_MAP) + 1 and "`weak_hash`" in md
    with TestClient(create_app()) as client:
        body = client.get("/api/v1/standards-map").json()
    assert body["standard"].startswith("IEEE/UL 2933-2024")
    assert all(r["tippss_2933_clause"] is None for r in body["rows"])  # clause numbers are not public
    assert {r["finding_type"] for r in body["rows"]} == set(standards_map.BY_TYPE)
