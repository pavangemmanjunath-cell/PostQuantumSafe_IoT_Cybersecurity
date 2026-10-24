"""End-to-end API tests: REST, WebSocket streams, uploads, PDFs and the fleet simulation workflow."""

from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient

from safeguard_pq.agents import all_agents
from safeguard_pq.simulation import Simulation

from ..conftest import scenario_request


def test_health_and_catalogues(client: TestClient) -> None:
    h = client.get("/api/v1/health").json()
    assert h["status"] == "ok" and h["llm"]["provider"] == "none" and h["agents"] == 14
    agents = client.get("/api/v1/agents").json()
    assert [a["id"] for a in agents] == [a.spec.id for a in all_agents()]
    assert {"pqc_catalog", "rules", "remediation_templates"} <= set(client.get("/api/v1/knowledge").json())
    assert len(client.get("/api/v1/scenarios").json()) == 10
    assert client.get("/api/v1/scenarios/nope").status_code == 404


def test_tool_api(client: TestClient) -> None:
    tools = {t["name"]: t for t in client.get("/api/v1/tools").json()}
    assert "pqc.classify_algorithm" in tools and tools["openfda.device_recalls"]["online"] is True
    r = client.post("/api/v1/tools/pqc.classify_algorithm", json={"name": "ECDHE-P256"}).json()
    assert r["result"]["quantum_status"] == "quantum_vulnerable" and "Shor" in r["result"]["quantum_attack"]
    assert client.post("/api/v1/tools/pqc.classify_algorithm", json={}).status_code == 400
    assert client.post("/api/v1/tools/pqc.classify_algorithm", json={"name": "x", "bogus": 1}).status_code == 400
    assert client.post("/api/v1/tools/does.not.exist", json={}).status_code == 404
    off = client.post("/api/v1/tools/openfda.device_recalls", json={"query": "infusion pump"})
    assert off.status_code == 400 and "disabled" in off.json()["detail"]


def test_assessment_roundtrip_and_pdf(client: TestClient) -> None:
    res = client.post("/api/v1/assessments", json=scenario_request("icu_gateway_critical"))
    assert res.status_code == 200
    body = res.json()
    assert body["environment_status"] == "UNSAFE" and body["pq_risk_score"] == 61
    aid = body["assessment_id"]
    assert client.get(f"/api/v1/assessments/{aid}").json()["assessment_id"] == aid
    assert client.get("/api/v1/assessments").json()[0]["assessment_id"] == aid
    pdf = client.get(f"/api/v1/assessments/{aid}/report.pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-" and len(pdf.content) > 5000
    assert "attachment" in pdf.headers["content-disposition"]
    assert client.get("/api/v1/assessments/missing/report.pdf").status_code == 404


def test_safe_environment_pdf(client: TestClient) -> None:
    body = client.post("/api/v1/assessments", json=scenario_request("nextgen_pq_safe")).json()
    assert body["environment_status"] == "SAFE"
    assert client.get(f"/api/v1/assessments/{body['assessment_id']}/report.pdf").content[:5] == b"%PDF-"


def test_validation_errors(client: TestClient) -> None:
    assert client.post("/api/v1/assessments", json={"constraints": {"budget_usd": -5}}).status_code == 422
    assert client.post("/api/v1/assessments", json={"tls_config": {"data_lifetime_years": 1000}}).status_code == 422


def test_websocket_assessment_streams_every_agent(client: TestClient) -> None:
    events = []
    with client.websocket_connect("/api/v1/ws/assessments") as ws:
        ws.send_json({"scenario_id": "pq_downgrade_prompt"})
        while True:
            msg = ws.receive_json()
            events.append(msg)
            if msg["type"] in ("result", "error"):
                break
    kinds = [e["type"] for e in events]
    assert kinds[0] == "run_started" and kinds[-1] == "result"
    started = [e["agent"] for e in events if e["type"] == "agent_started"]
    completed = [e["agent"] for e in events if e["type"] == "agent_completed"]
    assert set(started) == set(completed) == {a.spec.id for a in all_agents()}
    assert any(e["type"] == "finding" and e["finding"]["type"] == "pq_downgrade_instruction" for e in events)
    assert events[-1]["result"]["environment_status"] == "UNSAFE"


def test_websocket_rejects_bad_message(client: TestClient) -> None:
    with client.websocket_connect("/api/v1/ws/assessments") as ws:
        ws.send_json({"hello": "world"})
        assert ws.receive_json()["type"] == "error"


def _csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode()


def test_csv_upload(client: TestClient) -> None:
    sim = Simulation(seed=8)
    sim.inject("PUMP-ICU-A12", "ddos_volumetric")
    raw = _csv(list(sim.devices["PUMP-ICU-A12"].window))
    r = client.post("/api/v1/uploads/assess", files={"file": ("capture.csv", raw, "text/csv")},
                    data={"tls_profile": "legacy", "budget_usd": "50000"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "volumetric_flood_pattern" in [f["type"] for f in body["findings"]]
    assert body["qiro_optimization"]["budget_constraint_usd"] == 50000
    bad = client.post("/api/v1/uploads/assess", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
    assert bad.status_code == 422


def test_simulation_workflow(client: TestClient) -> None:
    cat = client.get("/api/v1/simulations/catalog").json()
    assert {t["id"] for t in cat["templates"]} == {"hospital_ward", "smart_factory"}
    assert len(cat["attacks"]) == 14 and len(cat["mitigations"]) == 12

    sim = client.post("/api/v1/simulations", json={"template": "hospital_ward", "seed": 21}).json()
    sid = sim["id"]
    assert len(sim["devices"]) == 9
    assert client.post(f"/api/v1/simulations/{sid}/step?ticks=3").json()["tick"] == 3

    r = client.post(f"/api/v1/simulations/{sid}/attacks", json={"device_id": "PUMP-ICU-A12", "attack": "syn_flood"}).json()
    assert "syn_flood" in r["device"]["active_attacks"]
    assert client.post(f"/api/v1/simulations/{sid}/attacks", json={"device_id": "PUMP-ICU-A12", "attack": "phi_leak"}).status_code == 400

    dev = client.post(f"/api/v1/simulations/{sid}/devices/PUMP-ICU-A12/assess").json()
    assert "syn_flood_pattern" in [f["type"] for f in dev["findings"]]

    fleet = client.post(f"/api/v1/simulations/{sid}/assess", json={"budget_usd": 300000, "max_downtime_hrs": 100}).json()
    assert fleet["environment_status"] == "UNSAFE" and len(fleet["devices"]) == 9
    assert fleet["fleet_plan"]["total_cost_usd"] <= 300000
    pdf = client.get(f"/api/v1/simulations/{sid}/report.pdf")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"

    plan = [{"mitigation": a["mitigation"], "device_id": a["device_id"]} for a in fleet["fleet_plan"]["selected_actions"]]
    applied = client.post(f"/api/v1/simulations/{sid}/apply-plan", json={"action_mitigations": plan}).json()
    assert applied["events"]
    after = client.post(f"/api/v1/simulations/{sid}/assess", json={"budget_usd": 300000, "max_downtime_hrs": 100}).json()
    before_total = sum(d["findings_count"] for d in fleet["devices"])
    after_total = sum(d["findings_count"] for d in after["devices"])
    assert after_total < before_total

    cleared = client.post(f"/api/v1/simulations/{sid}/mitigations", json={"mitigation": "rate_limiting"}).json()
    assert all("syn_flood" not in d["active_attacks"] for d in cleared["snapshot"]["devices"])
    assert client.get("/api/v1/simulations/unknown").status_code == 404


def test_fleet_pdf_requires_assessment(client: TestClient) -> None:
    sid = client.post("/api/v1/simulations", json={}).json()["id"]
    assert client.get(f"/api/v1/simulations/{sid}/report.pdf").status_code == 409


def test_simulation_live_stream(client: TestClient) -> None:
    sid = client.post("/api/v1/simulations", json={"seed": 4}).json()["id"]
    with client.websocket_connect(f"/api/v1/simulations/{sid}/stream?interval_ms=200") as ws:
        first = ws.receive_json()
        second = ws.receive_json()
    assert first["type"] == "tick" and len(first["devices"]) == 9
    assert second["tick"] >= first["tick"]
    assert first["events"]  # the start-up event is delivered once


def test_websocket_device_assessment_updates_simulation(client: TestClient) -> None:
    sid = client.post("/api/v1/simulations", json={"seed": 4}).json()["id"]
    with client.websocket_connect("/api/v1/ws/assessments") as ws:
        ws.send_json({"simulation_id": sid, "device_id": "AI-ASSIST-01"})
        while (msg := ws.receive_json())["type"] != "result":
            pass
    dev = next(d for d in client.get(f"/api/v1/simulations/{sid}").json()["devices"] if d["id"] == "AI-ASSIST-01")
    assert dev["last_assessment"]["assessment_id"] == msg["result"]["assessment_id"]


def test_q_day_assumptions_endpoint(client: TestClient) -> None:
    sid = client.post("/api/v1/simulations", json={"seed": 3}).json()["id"]
    snap = client.post(f"/api/v1/simulations/{sid}/assumptions", json={"migration_years": 5, "years_to_crqc": 6}).json()
    assert snap["assumptions"] == {"migration_years": 5.0, "years_to_crqc": 6.0}
    exposed = [d["id"] for d in snap["devices"] if d["live"]["hndl_exposed"]]
    assert "EHR-API-01" in exposed and "GW-EDGE-01" not in exposed
    assert client.post(f"/api/v1/simulations/{sid}/assumptions", json={"years_to_crqc": 500}).status_code == 422
