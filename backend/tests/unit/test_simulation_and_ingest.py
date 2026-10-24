"""Simulator mechanics and CSV ingest adapters."""

from __future__ import annotations

import csv
import io

import pytest

from safeguard_pq.ingest.csv_adapters import IngestError, build_request, detect_format
from safeguard_pq.knowledge.remediation import ACTION_TEMPLATES
from safeguard_pq.simulation import Simulation, SimulationError
from safeguard_pq.simulation import catalog as cat

from ..conftest import assess


def test_catalog_is_internally_consistent() -> None:
    for a in cat.ATTACKS.values():
        assert a.blocked_by and all(m in cat.MITIGATIONS for m in a.blocked_by), a.id
    for t in ACTION_TEMPLATES.values():
        assert t.mitigation is None or t.mitigation in cat.MITIGATIONS
    for tpl in cat.TEMPLATES.values():
        assert all(kind in cat.PROFILES for _, kind, _, _ in tpl.devices)


def test_same_seed_same_telemetry() -> None:
    a, b = Simulation(seed=11), Simulation(seed=11)
    for _ in range(3):
        a.step(), b.step()
    assert list(a.devices["ECG-ICU-007"].window) == list(b.devices["ECG-ICU-007"].window)


def test_baseline_fleet_has_no_traffic_alerts() -> None:
    sim = Simulation(seed=3)
    for _ in range(5):
        sim.step()
    for d in sim.devices.values():
        assert not [x for x in sim.live_status(d)["alerts"] if x.endswith("_pattern") or x.endswith("_anomaly")], d.id


@pytest.mark.parametrize("attack", ["syn_flood", "ddos_volumetric", "port_scan", "mqtt_malformed", "arp_spoofing"])
def test_network_attacks_are_detected_by_traffic_agent(attack: str) -> None:
    sim = Simulation(seed=5)
    sim.inject("ECG-ICU-007", attack)
    sim.step()
    expected = {"syn_flood": "syn_flood_pattern", "ddos_volumetric": "volumetric_flood_pattern", "port_scan": "port_scan_pattern",
                "mqtt_malformed": "protocol_flag_anomaly", "arp_spoofing": "protocol_mix_anomaly"}[attack]
    r = assess(sim.to_request("ECG-ICU-007").model_dump())
    assert expected in [f.type for f in r.findings if f.agent == "traffic_anomaly"]


@pytest.mark.parametrize(("attack", "device", "agent", "ftype"), [
    ("tls_downgrade", "GW-EDGE-01", "crypto_inventory", "deprecated_tls_version"),
    ("pq_strip", "GW-EDGE-01", "crypto_inventory", "classical_key_exchange"),
    ("hndl_capture", "EHR-API-01", "pq_identification", "long_lifetime_classical_crypto"),
    ("cert_spoof", "PUMP-ICU-A12", "device_identity", "authentication_failed"),
    ("secret_leak", "PUMP-ICU-A12", "secret_exposure", "stripe_live_key"),
    ("prompt_injection", "AI-ASSIST-01", "prompt_injection", "instruction_override"),
    ("pq_downgrade_prompt", "AI-ASSIST-01", "prompt_injection", "pq_downgrade_instruction"),
    ("phi_leak", "AI-ASSIST-01", "clinical_privacy", "medical_record_number"),
    ("unsafe_command", "AI-ASSIST-01", "safety_risk", "autonomous_dosing"),
])
def test_each_injection_is_detected_by_its_agent(attack: str, device: str, agent: str, ftype: str) -> None:
    sim = Simulation(seed=2)
    before = assess(sim.to_request(device).model_dump())
    assert ftype not in [f.type for f in before.findings if f.agent == agent]
    sim.inject(device, attack)
    after = assess(sim.to_request(device).model_dump())
    assert ftype in [f.type for f in after.findings if f.agent == agent]


def test_hndl_is_neutralised_by_pq_key_exchange() -> None:
    sim = Simulation(seed=2)
    ev = sim.inject("GW-EDGE-01", "hndl_capture")
    assert "protected by ML-KEM" in ev["message"]
    r = assess(sim.to_request("GW-EDGE-01").model_dump())
    assert "long_lifetime_classical_crypto" not in [f.type for f in r.findings]


def test_mitigation_blocks_reinjection_and_clears_attack() -> None:
    sim = Simulation(seed=2)
    sim.inject("PUMP-ICU-A12", "syn_flood")
    sim.mitigate("PUMP-ICU-A12", "rate_limiting")
    assert "syn_flood" not in sim.devices["PUMP-ICU-A12"].active_attacks
    ev = sim.inject("PUMP-ICU-A12", "syn_flood")
    assert ev.get("blocked") is True


def test_clear_attack_restores_configuration() -> None:
    sim = Simulation(seed=2)
    original = dict(sim.devices["GW-EDGE-01"].tls)
    sim.inject("GW-EDGE-01", "tls_downgrade")
    assert sim.devices["GW-EDGE-01"].tls["tls_version"] == "TLS1.0"
    sim.clear_attack("GW-EDGE-01", "tls_downgrade")
    assert sim.devices["GW-EDGE-01"].tls == original


def test_full_hardening_makes_legacy_pump_safe() -> None:
    sim = Simulation(seed=2)
    for m in ("enable_hybrid_mlkem", "pq_certificates", "upgrade_tls13"):
        sim.mitigate("PUMP-ICU-A12", m)
    r = assess(sim.to_request("PUMP-ICU-A12").model_dump())
    assert r.environment_status == "SAFE", r.environment_reasons


def test_invalid_operations_raise() -> None:
    sim = Simulation(seed=1)
    with pytest.raises(SimulationError):
        sim.inject("PUMP-ICU-A12", "prompt_injection")  # pump has no AI
    with pytest.raises(SimulationError):
        sim.inject("NOPE", "syn_flood")
    with pytest.raises(SimulationError):
        Simulation(template="unknown")
    with pytest.raises(SimulationError):
        Simulation(data_source="replay", replay_dir=None)


def test_industrial_template_runs() -> None:
    sim = Simulation(template="smart_factory", seed=1)
    r = assess(sim.to_request("PLC-L3-01").model_dump())
    assert r.domain == "industrial" and r.pq_posture["readiness"] == "Quantum-vulnerable"


def _csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode()


def test_ciciomt_upload_uses_traffic_not_filename() -> None:
    sim = Simulation(seed=4)
    sim.inject("ECG-ICU-007", "syn_flood")
    raw = _csv(list(sim.devices["ECG-ICU-007"].window))
    payload = build_request("Benign_looking_name.csv", raw)  # misleading name must not matter
    assert payload["tls_config"] is None
    r = assess(payload)
    assert "syn_flood_pattern" in [f.type for f in r.findings]
    assert r.environment_status == "UNSAFE"


def test_benign_upload_without_tls_is_at_risk_not_safe() -> None:
    raw = _csv(list(Simulation(seed=4).devices["ECG-ICU-007"].window))
    r = assess(build_request("x.csv", raw))
    assert r.environment_status == "AT_RISK"
    r2 = assess(build_request("x.csv", raw, tls_profile="pq_ready"))
    assert r2.environment_status == "SAFE"


def test_synthea_style_patients_upload_detects_phi() -> None:
    rows = [{"Id": "1234abcd-0000", "BIRTHDATE": "1980-01-01", "FIRST": "Jamie", "LAST": "Testcase", "GENDER": "F"},
            {"Id": "5678efgh-0000", "BIRTHDATE": "1975-05-05", "FIRST": "Robin", "LAST": "Example", "GENDER": "M"}]
    payload = build_request("patients.csv", _csv(rows))
    r = assess(payload)
    assert "patient_identifier" in [f.type for f in r.findings]
    assert "instruction_override" not in [f.type for f in r.findings]  # probe is opt-in
    r2 = assess(build_request("patients.csv", _csv(rows), include_injection_probe=True))
    assert "instruction_override" in [f.type for f in r2.findings]


def test_unknown_csv_rejected() -> None:
    with pytest.raises(IngestError):
        detect_format(["a", "b"])
    with pytest.raises(IngestError):
        build_request("x.csv", b"")
    with pytest.raises(IngestError):
        build_request("x.csv", _csv([{"syn_flag_number": 1, "Rate": 2}]), tls_profile="bogus")


def test_quantum_forgery_is_refused_for_ml_dsa_certificates() -> None:
    sim = Simulation(seed=2)
    ev = sim.inject("GW-EDGE-01", "cert_spoof")  # gateway uses ML-DSA-87
    assert ev.get("blocked") is True and "cannot break" in ev["message"]
    sim.inject("PUMP-ICU-A12", "cert_spoof")      # ECDSA → forgery succeeds
    sim.mitigate("PUMP-ICU-A12", "device_reauth")  # re-authentication recovers
    assert "cert_spoof" not in sim.devices["PUMP-ICU-A12"].active_attacks
    sim.mitigate("PUMP-ICU-A12", "pq_certificates")
    assert sim.inject("PUMP-ICU-A12", "cert_spoof").get("blocked") is True


def test_q_day_what_if_changes_exposure_and_findings() -> None:
    sim = Simulation(seed=2)
    ehr = sim.devices["EHR-API-01"]  # 8-year data, classical ECDHE
    sim.set_assumptions(migration_years=1, years_to_crqc=20)
    assert not sim.hndl_exposed(ehr)
    relaxed = assess(sim.to_request("EHR-API-01").model_dump())
    assert "mosca_hndl_exposure" not in [f.type for f in relaxed.findings]
    sim.set_assumptions(migration_years=5, years_to_crqc=8)
    assert sim.hndl_exposed(ehr) and sim.live_status(ehr)["hndl_exposed"]
    strict = assess(sim.to_request("EHR-API-01").model_dump())
    assert "mosca_hndl_exposure" in [f.type for f in strict.findings]
    assert not sim.hndl_exposed(sim.devices["GW-EDGE-01"])  # ML-KEM: never exposed
    with pytest.raises(SimulationError):
        sim.set_assumptions(-1, 10)
