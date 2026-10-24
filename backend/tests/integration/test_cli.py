from __future__ import annotations

import json
from pathlib import Path

from safeguard_pq.cli import main


def test_cli_assess_scenario_writes_pdf_and_json(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    pdf, js = tmp_path / "r.pdf", tmp_path / "r.json"
    assert main(["assess", "--scenario", "legacy_worst_case", "--pdf", str(pdf), "--json", str(js)]) == 0
    out = capsys.readouterr().out
    assert "UNSAFE" in out and "89/100" in out
    assert pdf.read_bytes()[:5] == b"%PDF-"
    assert json.loads(js.read_text(encoding="utf-8"))["pq_risk_score"] == 89


def test_cli_assess_file_and_scenarios(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    req = tmp_path / "req.json"
    req.write_text(json.dumps({"system_id": "CLI-1", "tls_config": {"key_exchange": "ML-KEM-768", "cert_signature_algo": "ML-DSA-65"}}))
    assert main(["assess", "--file", str(req)]) == 0
    assert "CLI-1: environment SAFE" in capsys.readouterr().out
    assert main(["scenarios"]) == 0
    assert "icu_gateway_critical" in capsys.readouterr().out
    assert main(["assess", "--scenario", "nope"]) == 2
