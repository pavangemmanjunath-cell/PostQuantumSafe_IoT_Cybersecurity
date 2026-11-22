"""Reproduce experiments E1-E5 of the revised journal paper with the shipped software.

    python benchmarks/paper_experiments.py [--only e1,e2,e3,e4,e5] [--out-dir benchmarks/results] [--strict]

  E1  the ten built-in synthetic systems: every cell of Table II (PQ readiness, S / status, Mosca's test M, lifetime
      override P, findings (critical), plan size, projected S, reassessed S / status) and the principle scores of
      Section VII-A
  E2  a legacy infusion-pump gateway under six attack conditions, assessed before and after the countermeasures
      (inputs: examples/paper/e2_infusion_pump_conditions.json)
  E3  harvest-now-decrypt-later exposure of seven data classes (5-30 years) against the Q-Day horizon z = 4-30 years
      for migration times y = 2, 5 and 8 years, with classical and with hybrid ML-KEM key exchange
  E4  budget sweep 10,000-200,000 USD for the ICU gateway and the legacy system; the solver-quality half of E4 (500
      random instances against the exhaustive optimum) is benchmarks/qiro_optimality.py
  E5  the worked example of Section III (examples/paper/worked_example_gateway.json = Listing 1 of the original
      draft): attribution, counterfactual, plan, projection, reassessment, all feasible action subsets and the
      shared-root-cause mode

All assessments use seed 2026, no LLM and the default options (independent planner, y = 5, z = 10, L = 10 unless the
experiment varies them); the shared-root-cause planner is used only where the paper uses it (E5). Each artifact
(benchmarks/results/paper_e*.json) records software_version, python, seed, inputs, method, results and a paper_check
block that lists every number the paper states for the experiment with the expected value, the reproduced value and
whether they match. No timings are recorded, so the artifacts are deterministic apart from the date. The script
always writes the artifacts; --strict makes it exit with status 1 if any stated value was not reproduced.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import platform
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))

import plan_reassessment  # noqa: E402
from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.agents.crypto import TLS_FIELDS  # noqa: E402
from safeguard_pq.config import Settings  # noqa: E402
from safeguard_pq.domain.models import AssessmentRequest, AssessmentResult  # noqa: E402
from safeguard_pq.optimizer import qiro  # noqa: E402
from safeguard_pq.optimizer.reassess import apply_plan, evaluate_plan_by_reassessment, reassess  # noqa: E402
from safeguard_pq.orchestrator import run_assessment  # noqa: E402
from safeguard_pq.scenarios import load_scenarios  # noqa: E402
from safeguard_pq.simulation import Simulation  # noqa: E402
from safeguard_pq.simulation import catalog as cat  # noqa: E402

SEED = 2026
EXAMPLES = ROOT / "examples" / "paper"
WORKED_EXAMPLE_FILE = EXAMPLES / "worked_example_gateway.json"
E2_FILE = EXAMPLES / "e2_infusion_pump_conditions.json"
ARTIFACTS = {
    "e1": "paper_e1_systems.json",
    "e2": "paper_e2_attack_conditions.json",
    "e3": "paper_e3_qday_sweep.json",
    "e4": "paper_e4_budget_sweep.json",
    "e5": "paper_e5_worked_example.json",
}
SETTINGS = Settings(_env_file=None, llm_provider="none", online_tools_enabled=False)
PAPER = "revised paper"
DRAFT = "original draft"
HNDL_KINDS = {"long_lifetime_classical_crypto": "override", "mosca_hndl_exposure": "mosca"}
CAVEAT = ("Synthetic, hand-written configurations; configuration-level results of the framework's own rules, not "
          "evidence that an attack is prevented.")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------- paper check


def same(expected: Any, reproduced: Any) -> bool:
    """Equality for stated values: numbers by value (26 == 26.0), booleans only with booleans, containers recursively."""
    if isinstance(expected, bool) or isinstance(reproduced, bool):
        return type(expected) is type(reproduced) and expected == reproduced
    if isinstance(expected, int | float) and isinstance(reproduced, int | float):
        return expected == reproduced
    if isinstance(expected, list | tuple) and isinstance(reproduced, list | tuple):
        return len(expected) == len(reproduced) and all(same(a, b) for a, b in zip(expected, reproduced, strict=True))
    if isinstance(expected, dict) and isinstance(reproduced, dict):
        return expected.keys() == reproduced.keys() and all(same(v, reproduced[k]) for k, v in expected.items())
    return expected == reproduced


class PaperCheck:
    """Every number the paper states for one experiment: expected (paper), reproduced (this run), match."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, check_id: str, source: str, statement: str, expected: Any, reproduced: Any, note: str | None = None) -> None:
        item = {"id": check_id, "source": source, "statement": statement, "expected": expected, "reproduced": reproduced,
                "match": same(expected, reproduced)}
        if note:
            item["note"] = note
        self.items.append(item)

    def block(self) -> dict[str, Any]:
        matched = sum(i["match"] for i in self.items)
        return {"summary": {"stated_values": len(self.items), "matched": matched, "mismatched": len(self.items) - matched,
                            "all_match": matched == len(self.items)},
                "checks": self.items}


# ------------------------------------------------------------------------------------------------- assessments


def make_request(payload: dict[str, Any] | AssessmentRequest, seed: int, *, grouped: bool = False) -> AssessmentRequest:
    """Request with the experiment seed, no LLM narrative and the given planner mode (default: independent)."""
    if isinstance(payload, AssessmentRequest):
        req = payload.model_copy(deep=True)
    else:
        req = AssessmentRequest.model_validate(copy.deepcopy(payload))
    req.seed = seed
    req.options.llm_report = False
    req.options.group_shared_root_causes = grouped
    return req


async def assess(payload: dict[str, Any] | AssessmentRequest, seed: int) -> tuple[AssessmentRequest, AssessmentResult]:
    req = make_request(payload, seed)
    return req, await run_assessment(req, settings=SETTINGS)


def critical_count(r: AssessmentResult) -> int:
    return sum(f.severity == "critical" for f in r.findings)


def outcome(r: AssessmentResult) -> dict[str, Any]:
    return {
        "pq_risk_score": r.pq_risk_score, "verdict": r.verdict, "environment_status": r.environment_status,
        "pq_readiness": r.pq_posture.get("readiness"), "findings_count": r.findings_count,
        "critical_findings": critical_count(r), "detected_by": sorted({f.agent for f in r.findings}),
        "findings": [{"id": f.id, "agent": f.agent, "type": f.type, "severity": f.severity} for f in r.findings],
    }


def plan_view(r: AssessmentResult) -> dict[str, Any]:
    q = r.qiro_optimization
    sel = q.get("selected_actions", [])
    return {"planner_mode": q.get("planner_mode"), "candidate_actions": q.get("total_candidate_actions", 0),
            "selection_count": q.get("selection_count", 0), "selected_action_ids": [a["id"] for a in sel],
            "selected_finding_types": [a["finding_type"] for a in sel],
            "mitigations": sorted({a["mitigation"] for a in sel if a.get("mitigation")}),
            "total_cost_usd": q.get("total_cost_usd", 0), "total_downtime_hrs": q.get("total_downtime_hrs", 0),
            "total_risk_reduction": q.get("total_risk_reduction", 0)}


def projection(r: AssessmentResult) -> dict[str, Any]:
    after = r.explanation["plan_projection"]["after"]
    return {"pq_risk_score": after["pq_risk_score"], "environment_status": after["environment_status"]}


def envelope(exp: str, title: str, seed: int, inputs: Any, method: Any, results: Any, check: PaperCheck) -> dict[str, Any]:
    return {
        "benchmark": ARTIFACTS[exp].removesuffix(".json"),
        "paper_experiment": exp.upper(),
        "title": title,
        "software_version": __version__,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "seed": seed,
        "inputs": inputs,
        "method": method,
        "results": results,
        "paper_check": check.block(),
        "caveat": CAVEAT,
    }


# ------------------------------------------------------------------------------------------------- E1


READINESS = {"Vuln.": "Quantum-vulnerable", "Ready": "PQ-ready", "Partial": "Partially PQ"}
STATUS = {"Safe": "SAFE", "At risk": "AT_RISK", "Unsafe": "UNSAFE"}
# Table II of the revised paper, row by row: scenario id, system, PQ, S, status, M, P, findings, critical, plan,
# projected S, reassessed S, reassessed status.
TABLE_II: tuple[tuple[Any, ...], ...] = (
    ("icu_gateway_critical", "ICU gateway", "Vuln.", 61, "Unsafe", 1, 1, 8, 3, 5, 26, 0, "Safe"),
    ("nextgen_pq_safe", "PQ-ready edge gateway", "Ready", 0, "Safe", 1, 0, 0, 0, 0, 0, 0, "Safe"),
    ("ehr_tls13_classical", "EHR API (TLS 1.3)", "Vuln.", 26, "At risk", 1, 0, 5, 0, 3, 26, 0, "Safe"),
    ("clinical_ai_phi", "Clinical AI (PHI)", "Ready", 0, "Unsafe", 0, 0, 4, 1, 4, 0, 0, "Safe"),
    ("secret_exposure", "Credential leak", "Ready", 10, "Unsafe", 0, 0, 2, 2, 2, 0, 0, "Safe"),
    ("legacy_worst_case", "Legacy TLS 1.0", "Vuln.", 89, "Unsafe", 1, 1, 9, 4, 5, 46, 43, "Unsafe"),
    ("tight_budget_qiro", "ICU gateway, $30k", "Vuln.", 61, "Unsafe", 1, 1, 8, 3, 2, 58, 46, "Unsafe"),
    ("pq_downgrade_prompt", "AI PQ-downgrade", "Ready", 0, "Unsafe", 1, 0, 2, 1, 2, 0, 0, "Safe"),
    ("hybrid_transition", "Hybrid PACS gateway", "Partial", 23, "At risk", 1, 0, 2, 0, 2, 0, 0, "Safe"),
    ("infusion_syn_flood", "Pump under SYN flood", "Vuln.", 46, "Unsafe", 1, 1, 6, 2, 3, 26, 0, "Unsafe"),
)
E1_METHOD = {
    "assessment": "Each of the ten built-in scenarios (backend/src/safeguard_pq/data/scenarios.json) is assessed once "
                  "with seed 2026, the default options (independent planner, y = 5, z = 10, L = 10) and no LLM.",
    "M": "Mosca's test: pq_posture.mosca.at_risk, i.e. x + y > z with x = data lifetime, y = 5, z = 10 years "
         "(reported whatever the key exchange).",
    "P": "Lifetime override: 1 if the critical long_lifetime_classical_crypto finding is raised (x >= L = 10 years "
         "and the key exchange is neither PQ nor hybrid), else 0.",
    "plan, projected S": "Selected actions of the shipped planner and the explainer's plan_projection, which removes "
                         "only the findings of the selected actions.",
    "reassessed S / status": "optimizer.reassess.evaluate_plan_by_reassessment: the plan's catalogue mitigations are "
                             "applied to the configuration by code and the pipeline is re-run with the same seed (as "
                             "in E9, benchmarks/plan_reassessment.py, plan A).",
    "principle scores": "tippss_scores of the baseline assessment (the six IEEE/UL 2933-2024 principles, called "
                        "pillars in the code).",
    "not reproduced": "The timing in the note of Table III (6.31 ms per E1 assessment) is machine-dependent and is "
                      "not re-measured here.",
}


async def e1(seed: int) -> dict[str, Any]:
    scenarios = {s["id"]: s for s in load_scenarios()}
    check = PaperCheck()
    systems: list[dict[str, Any]] = []
    for sid, label, pq, s, status, m, p, nf, nc, plan_n, proj, re_s, re_status in TABLE_II:
        req, r = await assess(scenarios[sid]["request"], seed)
        ev = await evaluate_plan_by_reassessment(req, r, settings=SETTINGS)
        tls = req.tls_config
        mosca = r.pq_posture.get("mosca") or {}
        hndl = next(({"type": f.type, "severity": f.severity} for f in r.findings if f.type in HNDL_KINDS), None)
        row = {
            "scenario": sid, "paper_label": label, "system_id": r.system_id, "title": scenarios[sid]["title"],
            "key_exchange": tls.key_exchange if tls else None, "cert_signature_algo": tls.cert_signature_algo if tls else None,
            "data_lifetime_years": tls.data_lifetime_years if tls else None,
            "pq_readiness": r.pq_posture.get("readiness"), "pq_key_exchange": r.pq_posture.get("pq_key_exchange"),
            "pq_signature": r.pq_posture.get("pq_signature"),
            "pq_risk_score": r.pq_risk_score, "verdict": r.verdict, "environment_status": r.environment_status,
            "mosca": {k: mosca.get(k) for k in ("x_data_lifetime_years", "y_migration_years", "z_years_to_crqc", "at_risk")},
            "lifetime_threshold_years": req.assumptions.lifetime_threshold_years,
            "M": int(bool(mosca.get("at_risk"))),
            "P": int(any(f.type == "long_lifetime_classical_crypto" for f in r.findings)),
            "hndl_finding": hndl,
            "findings_count": r.findings_count, "critical_findings": critical_count(r),
            "findings": outcome(r)["findings"],
            "pillar_scores": {k: v["score"] for k, v in r.tippss_scores.items()},
            "plan": plan_view(r), "projected": projection(r),
            "reassessed": {"pq_risk_score": ev["reassessed_pq_score"], "environment_status": ev["reassessed_status"],
                           "remaining_finding_types": ev["remaining_finding_types"],
                           "applied_mitigations": ev["applied"]["applied_mitigations"],
                           "unmodelled_mitigations": ev["applied"]["unmodelled_mitigations"]},
        }
        systems.append(row)
        cells = (
            ("pq_readiness", "PQ", pq, READINESS[pq], row["pq_readiness"]),
            ("pq_risk_score", "S", s, s, row["pq_risk_score"]),
            ("environment_status", "status", status, STATUS[status], row["environment_status"]),
            ("M", "M", m, m, row["M"]),
            ("P", "P", p, p, row["P"]),
            ("findings", "Find.", nf, nf, row["findings_count"]),
            ("critical_findings", "(crit.)", nc, nc, row["critical_findings"]),
            ("plan_size", "Plan", plan_n, plan_n, row["plan"]["selection_count"]),
            ("projected_pq_score", "Proj. S", proj, proj, row["projected"]["pq_risk_score"]),
            ("reassessed_pq_score", "Reass. S", re_s, re_s, row["reassessed"]["pq_risk_score"]),
            ("reassessed_status", "Reass. status", re_status, STATUS[re_status], row["reassessed"]["environment_status"]),
        )
        for key, column, text, expected, got in cells:
            check.add(f"E1.table_ii.{sid}.{key}", f"{PAPER}, Table II", f"{label}: {column} = {text}", expected, got)

    by_id = {r["scenario"]: r for r in systems}
    pillars = {sid: r["pillar_scores"] for sid, r in by_id.items()}
    counts = {k: sum(r["environment_status"] == k for r in systems) for k in ("UNSAFE", "AT_RISK", "SAFE")}
    top = max(systems, key=lambda r: r["pq_risk_score"])
    check.add("E1.status_counts", f"{PAPER}, Section VII-A",
              "The framework rated seven of the ten systems UNSAFE, two AT_RISK and one SAFE.",
              {"UNSAFE": 7, "AT_RISK": 2, "SAFE": 1}, counts)
    check.add("E1.highest_score", f"{PAPER}, Section VII-A", "The legacy TLS 1.0 system reached the highest PQ risk score (89).",
              {"scenario": "legacy_worst_case", "pq_risk_score": 89}, {"scenario": top["scenario"], "pq_risk_score": top["pq_risk_score"]})
    hyb = by_id["hybrid_transition"]
    check.add("E1.hybrid_partially_pq", f"{PAPER}, Section VII-A",
              "The hybrid imaging gateway was rated partially PQ because its certificates were still ECDSA.",
              {"pq_readiness": "Partially PQ", "pq_key_exchange": True, "pq_signature": False, "certificate_signature": "ECDSA"},
              {"pq_readiness": hyb["pq_readiness"], "pq_key_exchange": hyb["pq_key_exchange"], "pq_signature": hyb["pq_signature"],
               "certificate_signature": (hyb["cert_signature_algo"] or "").split("-")[0]})
    classical = [r for r in systems if r["pq_key_exchange"] is False]
    disagree = [r["scenario"] for r in classical if r["M"] != r["P"]]
    ehr = by_id["ehr_tls13_classical"]
    check.add("E1.mosca_vs_override", f"{PAPER}, Section VII-A",
              "Among the systems with classical key exchange, Mosca's test and the override disagree only for the "
              "health-record interface (x = 8 years), which therefore has a medium rather than a critical finding.",
              {"systems": ["ehr_tls13_classical"], "data_lifetime_years": 8, "hndl_finding": {"type": "mosca_hndl_exposure", "severity": "medium"}},
              {"systems": disagree, "data_lifetime_years": ehr["data_lifetime_years"], "hndl_finding": ehr["hndl_finding"]},
              note=f"systems with classical key exchange: {', '.join(r['scenario'] for r in classical)}")
    pq_unsafe = [r["scenario"] for r in systems if r["pq_readiness"] == "PQ-ready" and r["environment_status"] == "UNSAFE"]
    check.add("E1.pq_ready_but_unsafe", f"{PAPER}, Section VII-A", "Three systems with PQ-safe cryptography were still UNSAFE.",
              3, len(pq_unsafe), note=", ".join(pq_unsafe))
    ai = pillars["clinical_ai_phi"]
    for name, value in (("Trust", 30), ("Privacy", 55), ("Protection", 55)):
        check.add(f"E1.principles.clinical_ai_phi.{name.lower()}", f"{PAPER}, Section VII-A",
                  "The clinical AI assistant scored 30 on trust and 55 on privacy and protection.", value, ai[name])
    for sid, who, pair, value in (("secret_exposure", "the device that logged cloud credentials", ("Protection", "Security"), 50),
                                  ("pq_downgrade_prompt", "the gateway that received a PQ-downgrade instruction", ("Trust", "Security"), 60)):
        for name in pair:
            check.add(f"E1.principles.{sid}.{name.lower()}", f"{PAPER}, Section VII-A",
                      f"{who[0].upper()}{who[1:]} scored {value} on {pair[0].lower()} and {pair[1].lower()}.", value, pillars[sid][name])
    zero_security = [sid for sid, p in pillars.items() if p["Security"] == 0]
    for sid, who in (("icu_gateway_critical", "the ICU gateway"), ("tight_budget_qiro", "the ICU gateway, $30k"),
                     ("legacy_worst_case", "the legacy device"), ("infusion_syn_flood", "the flooded pump")):
        check.add(f"E1.principles.{sid}.security", f"{PAPER}, Section VII-A",
                  f"Security fell to 0 for both ICU gateway systems, the legacy device and the flooded pump ({who}).", 0,
                  pillars[sid]["Security"], note=f"all systems with security 0: {', '.join(zero_security)}")
    zero_protection = [sid for sid, p in pillars.items() if p["Protection"] == 0]
    check.add("E1.principles.legacy_worst_case.protection", f"{PAPER}, Section VII-A",
              "... and protection to 0 for the legacy device.", 0, pillars["legacy_worst_case"]["Protection"],
              note=f"all systems with protection 0: {', '.join(zero_protection)}")
    check.add("E1.reassessed_safe", f"{PAPER}, Section VII-C", "After re-assessment (E9, Table II) seven systems were SAFE.",
              7, sum(r["reassessed"]["environment_status"] == "SAFE" for r in systems))
    return envelope("e1", "Assessment of the ten synthetic clinical systems (Table II) and their principle scores", seed,
                    {"scenarios": rel(ROOT / "backend" / "src" / "safeguard_pq" / "data" / "scenarios.json"),
                     "scenario_ids": [row[0] for row in TABLE_II], "options": "defaults (independent planner, no LLM)",
                     "assumptions": "defaults: migration_years 5, years_to_crqc 10, lifetime_threshold_years 10"},
                    E1_METHOD, {"systems": systems}, check)


# ------------------------------------------------------------------------------------------------- E2


# Table II of the original draft and Section VII-A of the revised paper: condition id -> (S, status, detecting agents).
E2_BEFORE = {
    "classical_baseline": (26, "AT_RISK", ["crypto_inventory", "pq_identification"]),
    "hndl_capture": (46, "UNSAFE", ["crypto_inventory", "pq_identification"]),
    "legacy_fallback_downgrade": (54, "UNSAFE", ["crypto_inventory", "pq_identification"]),
    "classical_only_group_fallback": (23, "AT_RISK", ["crypto_inventory", "pq_identification"]),
    "certificate_forgery_attempt": (41, "UNSAFE", ["crypto_inventory", "device_identity", "pq_identification"]),
    "pq_downgrade_prompt_injection": (26, "UNSAFE", ["crypto_inventory", "pq_identification", "prompt_injection"]),
}
AGENT_NAMES = {"crypto_inventory": "Crypto Inventory", "pq_identification": "PQ Identification",
               "device_identity": "Device Identity", "prompt_injection": "Prompt Injection"}


def countermeasure_actions(mitigations: Sequence[str]) -> list[dict[str, Any]]:
    """The countermeasures as plan actions, so that apply_plan applies them exactly as it applies a QIRO plan."""
    return [{"id": f"C{i}", "mitigation": m, "finding_type": "countermeasure"} for i, m in enumerate(mitigations, 1)]


def migrated_gateway(base: dict[str, Any], mitigations: Sequence[str]) -> dict[str, Any]:
    """The base gateway after the countermeasures (TLS 1.3, hybrid ML-KEM, ML-DSA certificates, ...), produced by code."""
    req, _ = apply_plan(AssessmentRequest.model_validate(copy.deepcopy(base)), countermeasure_actions(mitigations))
    out = copy.deepcopy(base)
    out["tls_config"].update({k: getattr(req.tls_config, k) for k in TLS_FIELDS})
    out["device_logs"], out["ai_prompt_logs"] = copy.deepcopy(req.device_logs), copy.deepcopy(req.ai_prompt_logs)
    return out


def attacked_configuration(spec: dict[str, Any], cond: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(start configuration, attacked configuration) of one condition."""
    base = spec["base_gateway"]
    start = copy.deepcopy(base if cond["start"] == "base_gateway" else migrated_gateway(base, spec["countermeasures"]))
    attacked = copy.deepcopy(start)
    attacked["tls_config"].update(cond["tls_config"])
    attacked["device_logs"][0].update(cond["device_log"])
    attacked["ai_prompt_logs"] = [*attacked.get("ai_prompt_logs", []), *cond["append_ai_prompt_logs"]]
    return start, attacked


def _device_state(d: Any) -> dict[str, Any]:
    return {"tls_config": {**d.tls, "data_lifetime_years": d.data_lifetime_years},
            "device_log": {"cert_present": d.cert_present, "auth_status": d.auth_status, "failed_login_count": d.failed_login_count},
            "prompts": list(d.prompts)}


def simulator_effect(start: dict[str, Any], attack_id: str) -> dict[str, Any]:
    """Apply the simulator's own attack injection (Simulation.inject) to a simulated device configured like ``start``
    and return the fields it changed, in the shape of a condition (tls_config, device_log, appended prompts)."""
    sim = Simulation("hospital_ward", seed=7)
    device_id = "AI-ASSIST-01" if cat.ATTACKS[attack_id].requires_ai else "PUMP-ICU-A12"
    d = sim.device(device_id)
    tls = dict(start["tls_config"])
    d.data_lifetime_years = float(tls.pop("data_lifetime_years"))
    d.tls = {k: tls.get(k) for k in TLS_FIELDS}
    log = start["device_logs"][0]
    d.cert_present, d.auth_status, d.failed_login_count = log["cert_present"], log["auth_status"], log["failed_login_count"]
    d.prompts = list(start.get("ai_prompt_logs", []))
    before = _device_state(d)
    event = sim.inject(device_id, attack_id)
    after = _device_state(d)
    return {
        "simulated_device": f"{device_id} ({d.kind})",
        "blocked": bool(event.get("blocked")),
        "tls_config": {k: v for k, v in after["tls_config"].items() if v != before["tls_config"].get(k)},
        "device_log": {k: v for k, v in after["device_log"].items() if v != before["device_log"][k]},
        "append_ai_prompt_logs": after["prompts"][len(before["prompts"]):],
    }


E2_METHOD = {
    "inputs": "Base gateway, conditions and countermeasures from examples/paper/e2_infusion_pump_conditions.json. The "
              "original draft names the six conditions and their detecting agents (Table II) but not their "
              "configurations; the file reproduces the configurations of the v0.1.0 experiment script that produced "
              "the draft's numbers (kept with the manuscript sources, not part of this repository).",
    "conditions": "Each attacked configuration is the start configuration with the condition's changes. Every change "
                  "set equals the effect of the simulator's attack injection named in simulator_attack "
                  "(simulation/engine.py: Simulation.inject), recomputed here on a simulated device configured like the "
                  "start configuration (results[].simulator_effect).",
    "assumptions": [
        "Base gateway: TLS 1.2, ECDHE-P256 key exchange, ECDSA-P256 certificate signature, RSA-2048 certificate key, "
        "AES-128-GCM, SHA-256, data lifetime 8 years, one authenticated device record and one benign AI prompt; default "
        "constraints (100,000 USD, 40 h) and assumptions (y = 5, z = 10, L = 10). The 8-year lifetime lies below L, so "
        "the classical baseline carries Mosca's medium finding (8 + 5 > 10) instead of the critical lifetime override.",
        "HNDL capture of long-lived data: data lifetime raised to 25 years (simulator hndl_capture: max(lifetime, 25)).",
        "Legacy-fallback downgrade: TLS 1.0, RSA key transport and SHA-1 (simulator tls_downgrade).",
        "Classical-only group fallback: starts from the migrated gateway (the base gateway after the countermeasures, "
        "applied by code) and drops the ML-KEM share, key exchange ECDHE-P256 (simulator pq_strip, which needs an "
        "ML-KEM share to drop).",
        "Certificate-forgery attempt (named 'Quantum certificate forgery' in the v0.1.0 script): device record without "
        "certificate, failed authentication, 6 failed logins; the certificate signature is already the classical "
        "ECDSA-P256 (simulator cert_spoof).",
        "PQ-downgrade prompt injection: the simulator's pq_downgrade_prompt text appended to the AI prompt log.",
        "Countermeasures (Section V-C): the catalogue mitigations enable_hybrid_mlkem, pq_certificates, upgrade_tls13, "
        "strong_hash, pq_policy_pinning, device_reauth and prompt_firewall, applied to every attacked configuration "
        "with optimizer.reassess.apply_plan. The result equals the v0.1.0 'defended profile' (TLS 1.3, X25519MLKEM768, "
        "ML-DSA-65 certificate signature and key, AES-256-GCM, SHA-384, re-authenticated device, downgrade prompt "
        "removed); pq_policy_pinning has no configuration fields and is applied as a no-op.",
    ],
    "assessment": "Before and after: one full pipeline run each, seed 2026, default options, no LLM. 'Detected by' "
                  "is the set of agents that raised at least one finding.",
}


async def e2(seed: int) -> dict[str, Any]:
    spec = load_json(E2_FILE)
    check = PaperCheck()
    rows: list[dict[str, Any]] = []
    for cond in spec["conditions"]:
        start, attacked = attacked_configuration(spec, cond)
        req, before = await assess(attacked, seed)
        after_req, report = apply_plan(req, countermeasure_actions(spec["countermeasures"]))
        _, after = await assess(after_req, seed)
        row: dict[str, Any] = {"id": cond["id"], "name": cond["name"], "simulator_attack": cond["simulator_attack"],
                               "start": cond["start"], "configuration": attacked}
        if cond["simulator_attack"]:
            attack = cat.ATTACKS[cond["simulator_attack"]]
            effect = simulator_effect(start, cond["simulator_attack"])
            declared = {k: cond[k] for k in ("tls_config", "device_log", "append_ai_prompt_logs")}
            effect["matches_condition"] = not effect["blocked"] and same(declared, {k: effect[k] for k in declared})
            row["simulator_effect"] = effect
            row["catalogue"] = {"label": attack.label, "detected_by": list(attack.detected_by), "blocked_by": list(attack.blocked_by)}
        row["before"] = outcome(before)
        row["countermeasures"] = {k: report[k] for k in ("applied_mitigations", "unmodelled_mitigations", "changes", "notes")}
        row["after"] = outcome(after)
        rows.append(row)

        s, status, agents = E2_BEFORE[cond["id"]]
        name = cond["name"]
        check.add(f"E2.{cond['id']}.before_pq_risk_score", f"{PAPER}, Section VII-A",
                  f"PQ risk score before mitigation: {s} for '{name}'.", s, before.pq_risk_score)
        check.add(f"E2.{cond['id']}.before_status", f"{PAPER}, Section VII-A",
                  f"'{name}' before mitigation: {status} (classical baseline and classical-only group fallback AT_RISK, "
                  "all others UNSAFE).", status, before.environment_status)
        check.add(f"E2.{cond['id']}.detected_by", f"{PAPER}, Section VII-A; {DRAFT}, Table II",
                  f"'{name}' detected by {', '.join(AGENT_NAMES[a] for a in agents)}.", agents, sorted({f.agent for f in before.findings}))
        check.add(f"E2.{cond['id']}.after_pq_risk_score", f"{PAPER}, Section VII-A",
                  "After the countermeasures re-assessment gave a score of 0.", 0, after.pq_risk_score)
        check.add(f"E2.{cond['id']}.after_pq_readiness", f"{PAPER}, Section VII-A",
                  "After the countermeasures re-assessment rated the configuration PQ-ready.", "PQ-ready", after.pq_posture.get("readiness"))
        check.add(f"E2.{cond['id']}.after_findings", f"{PAPER}, Section VII-A",
                  "After the countermeasures re-assessment raised no findings.", 0, after.findings_count)
        check.add(f"E2.{cond['id']}.after_status", f"{DRAFT}, Table II", "After: S / status = 0 / Safe.", "SAFE", after.environment_status)
    migrated = migrated_gateway(spec["base_gateway"], spec["countermeasures"])
    return envelope("e2", "Post-quantum attack conditions on a legacy infusion-pump gateway, before and after the countermeasures",
                    seed, {"file": rel(E2_FILE), "spec": spec, "migrated_gateway": migrated}, E2_METHOD, {"conditions": rows}, check)


# ------------------------------------------------------------------------------------------------- E3


E3_LIFETIMES = (5, 8, 10, 15, 20, 25, 30)  # the seven data classes (years), as in the v0.1.0 experiment script
E3_MIGRATION_YEARS = (2, 5, 8)
E3_HORIZONS = tuple(range(4, 31, 2))  # z = 4, 6, ..., 30 years
E3_HYBRID_MIGRATION_YEARS = 8
E3_METHOD = {
    "inputs": "Seven data classes with lifetimes x = 5, 8, 10, 15, 20, 25 and 30 years (the original draft: 'seven "
              "classes (5 to 30 years)'; the individual lifetimes are those of the v0.1.0 experiment script), migration "
              "time y = 2, 5 and 8 years and Q-Day horizon z = 4 to 30 years in steps of 2 years (v0.1.0 script).",
    "classical": "The E2 base gateway (ECDHE-P256 key exchange, examples/paper/e2_infusion_pump_conditions.json) with "
                 "data_lifetime_years = x and assumptions migration_years = y, years_to_crqc = z; lifetime threshold "
                 "L = 10 years (default).",
    "hybrid": "The E2 migrated gateway (the base gateway after the countermeasures: TLS 1.3, X25519MLKEM768 hybrid key "
              "exchange, ML-DSA-65 certificate) with y = 8 years.",
    "exposed": "A data class counts as exposed when the assessment raises long_lifetime_classical_crypto (the lifetime "
               "override, x >= L with classical key exchange; flag 'override') or mosca_hndl_exposure (Mosca's test "
               "x + y > z only; flag 'mosca'); 'none' otherwise. One full pipeline run per cell, seed 2026.",
}


async def e3_series(base: dict[str, Any], y: int, seed: int, label: str) -> dict[str, Any]:
    flags: list[list[str]] = []
    for z in E3_HORIZONS:
        row = []
        for x in E3_LIFETIMES:
            p = copy.deepcopy(base)
            p["tls_config"]["data_lifetime_years"] = x
            p["assumptions"] = {"migration_years": y, "years_to_crqc": z}
            _, r = await assess(p, seed)
            kinds = [HNDL_KINDS[f.type] for f in r.findings if f.type in HNDL_KINDS]
            row.append(kinds[0] if kinds else "none")
        flags.append(row)
    return {"label": label, "key_exchange": base["tls_config"]["key_exchange"], "migration_years": y,
            "exposed_classes": [sum(f != "none" for f in row) for row in flags], "flags_by_horizon": flags}


async def e3(seed: int) -> dict[str, Any]:
    spec = load_json(E2_FILE)
    base = spec["base_gateway"]
    hybrid_base = migrated_gateway(base, spec["countermeasures"])
    series = [await e3_series(base, y, seed, f"classical key exchange, y = {y}") for y in E3_MIGRATION_YEARS]
    hybrid = await e3_series(hybrid_base, E3_HYBRID_MIGRATION_YEARS, seed, f"hybrid ML-KEM, y = {E3_HYBRID_MIGRATION_YEARS}")
    check = PaperCheck()
    long_lived = [x for x in E3_LIFETIMES if x >= 10]
    first_drop = {}
    for s in series:
        y, counts = s["migration_years"], s["exposed_classes"]
        early = [counts[E3_HORIZONS.index(z)] for z in (4, 6)]
        check.add(f"E3.classical_y{y}.all_exposed_z4_z6", f"{PAPER}, Section VII-B",
                  "With classical key exchange, all seven data classes were exposed when Q-Day was assumed four or six "
                  f"years away (y = {y}).", [7, 7], early)
        check.add(f"E3.classical_y{y}.falls_with_z", f"{PAPER}, Section VII-B", f"Exposure fell as z grew (y = {y}).",
                  True, all(a >= b for a, b in zip(counts, counts[1:], strict=False)) and counts[-1] < counts[0])
        last = s["flags_by_horizon"][-1]
        check.add(f"E3.classical_y{y}.settles_at_long_lived", f"{PAPER}, Section VII-B",
                  "... and settled at the five classes with lifetimes of ten years or more "
                  f"(y = {y}, z = {E3_HORIZONS[-1]}).",
                  {"exposed_classes": 5, "lifetimes": long_lived},
                  {"exposed_classes": counts[-1], "lifetimes": [x for x, f in zip(E3_LIFETIMES, last, strict=True) if f != "none"]})
        first_drop[y] = next((z for z, c in zip(E3_HORIZONS, counts, strict=True) if c < len(E3_LIFETIMES)), None)
    drops = [first_drop[y] for y in E3_MIGRATION_YEARS]
    check.add("E3.earlier_for_shorter_migrations", f"{PAPER}, Section VII-B",
              "Exposure fell earlier for shorter migrations (first horizon with fewer than seven exposed classes "
              "increases with y).", True, None not in drops and drops == sorted(set(drops)),
              note="first horizon z with fewer than seven exposed classes: "
                   + ", ".join(f"y = {y}: z = {first_drop[y]}" for y in E3_MIGRATION_YEARS))
    always = all(row[E3_LIFETIMES.index(x)] == "override" for s in series for row in s["flags_by_horizon"] for x in long_lived)
    check.add("E3.override_always_flags_long_lived", f"{PAPER}, Section VII-B",
              "The classes with lifetimes of ten years or more are always flagged by the lifetime override (L = 10 years).",
              True, always)
    check.add("E3.hybrid_never_exposed", f"{PAPER}, Section VII-B",
              "Behind hybrid ML-KEM key exchange no class was exposed at any horizon, even with an eight-year migration.",
              [0] * len(E3_HORIZONS), hybrid["exposed_classes"])
    return envelope("e3", "Harvest-now decrypt-later exposure of seven data classes against the assumed Q-Day horizon",
                    seed, {"base_gateway": f"{rel(E2_FILE)}: base_gateway", "hybrid_gateway": f"{rel(E2_FILE)}: migrated gateway",
                           "data_class_lifetimes_years": list(E3_LIFETIMES), "migration_years": list(E3_MIGRATION_YEARS),
                           "years_to_crqc": list(E3_HORIZONS), "hybrid_migration_years": E3_HYBRID_MIGRATION_YEARS,
                           "lifetime_threshold_years": 10},
                    E3_METHOD, {"lifetimes": list(E3_LIFETIMES), "horizons": list(E3_HORIZONS), "series": [*series, hybrid]}, check)


# ------------------------------------------------------------------------------------------------- E4


E4_SCENARIOS = {"icu_gateway_critical": "ICU gateway", "legacy_worst_case": "legacy system"}
E4_BUDGETS = tuple(range(10_000, 200_001, 10_000))
E4_MAX_DOWNTIME_HRS = 40
E4_METHOD = {
    "inputs": "Scenarios icu_gateway_critical (ICU gateway) and legacy_worst_case (legacy TLS 1.0 system) with the "
              "budget set to 10,000 to 200,000 USD in steps of 10,000 USD and the downtime limit held at 40 h (the "
              "scenarios' own value, set explicitly as in the v0.1.0 experiment script); seed 2026, independent planner.",
    "reported": "total_risk_reduction of the selected actions (the sum of their template risk reductions, as plotted "
                "in the draft's Fig. 7a) and the explainer's projected PQ score after the plan (Fig. 7b).",
    "solver quality": "The other half of paper E4, QIRO against exhaustive search on 500 random instances of 3 to 14 "
                      "actions, is benchmarks/qiro_optimality.py --instances 500 --seed 0 (qiro_optimality.json).",
}


async def e4(seed: int) -> dict[str, Any]:
    scenarios = {s["id"]: s for s in load_scenarios()}
    sweeps: dict[str, Any] = {}
    for sid, label in E4_SCENARIOS.items():
        rows = []
        baseline = None
        for b in E4_BUDGETS:
            req = copy.deepcopy(scenarios[sid]["request"])
            req["constraints"] = {"budget_usd": b, "max_downtime_hrs": E4_MAX_DOWNTIME_HRS}
            _, r = await assess(req, seed)
            baseline = r.pq_risk_score
            p = plan_view(r)
            rows.append({"budget_usd": b, "selection_count": p["selection_count"], "selected_action_ids": p["selected_action_ids"],
                         "selected_finding_types": p["selected_finding_types"], "total_risk_reduction": p["total_risk_reduction"],
                         "total_cost_usd": p["total_cost_usd"], "total_downtime_hrs": p["total_downtime_hrs"],
                         "projected_pq_score": projection(r)["pq_risk_score"],
                         "projected_status": projection(r)["environment_status"]})
        sweeps[sid] = {"label": label, "baseline_pq_risk_score": baseline, "rows": rows}
    check = PaperCheck()
    at = {sid: {row["budget_usd"]: row for row in s["rows"]} for sid, s in sweeps.items()}
    for sid, label in E4_SCENARIOS.items():
        check.add(f"E4.{sid}.risk_reduction_10k", f"{PAPER}, Section VII-C",
                  f"Total risk reduction rose from 53 at 10,000 USD ({label}).", 53, at[sid][10_000]["total_risk_reduction"])
    for sid, value in (("icu_gateway_critical", 281), ("legacy_worst_case", 296)):
        check.add(f"E4.{sid}.risk_reduction_200k", f"{PAPER}, Section VII-C",
                  f"... to {value} ({E4_SCENARIOS[sid]}) at 200,000 USD.", value, at[sid][200_000]["total_risk_reduction"])
        rr = [row["total_risk_reduction"] for row in sweeps[sid]["rows"]]
        check.add(f"E4.{sid}.risk_reduction_rises", f"{PAPER}, Section VII-C",
                  f"Total risk reduction rose with the budget ({E4_SCENARIOS[sid]}; read as: never falls between steps).",
                  True, all(a <= b for a, b in zip(rr, rr[1:], strict=False)))
    icu = [row["projected_pq_score"] for row in sweeps["icu_gateway_critical"]["rows"]]
    check.add("E4.icu_gateway_critical.projected_monotonic", f"{PAPER}, Section VII-C",
              "The projected score was not monotonic (ICU gateway): projected S never rises with the budget = false.",
              False, all(a >= b for a, b in zip(icu, icu[1:], strict=False)))
    for b, value in ((100_000, 26), (110_000, 38)):
        check.add(f"E4.icu_gateway_critical.projected_{b // 1000}k", f"{PAPER}, Section VII-C",
                  f"ICU gateway: projected score {value} at {b:,} USD.", value, at["icu_gateway_critical"][b]["projected_pq_score"])
    return envelope("e4", "Budget sweep of the QIRO plan for the ICU gateway and the legacy system", seed,
                    {"scenarios": E4_SCENARIOS, "budgets_usd": list(E4_BUDGETS), "max_downtime_hrs": E4_MAX_DOWNTIME_HRS},
                    E4_METHOD, {"sweeps": sweeps}, check)


# ------------------------------------------------------------------------------------------------- E5


E5_METHOD = {
    "inputs": "The gateway of the worked example (Section III), i.e. Listing 1 of the original draft: TLS 1.2, "
              "ECDHE-P256 key exchange, ECDSA-P256 certificate signature, data lifetime x = 25 years, y = 5, z = 10, "
              "budget 60,000 USD, downtime 12 h; no device or prompt logs (examples/paper/worked_example_gateway.json).",
    "assessment": "One pipeline run with seed 2026 and the default (independent) planner; attribution, counterfactuals "
                  "and plan projection are the explainer's output.",
    "reassessment": "The plan's catalogue mitigations are applied to the configuration by code "
                    "(optimizer.reassess.reassess) and the pipeline is re-run, once with the plan's hybrid ML-KEM action "
                    "alone and once with the full plan.",
    "subsets": "Every subset of the candidate actions that is feasible under the budget and downtime limits is "
               "reassessed (benchmarks/plan_reassessment.py: exhaustive, independent cost accounting); the "
               "shared-root-cause planner (options.group_shared_root_causes) is run on the same request for "
               "comparison (plan B, grouped cost accounting).",
}


async def e5(seed: int) -> dict[str, Any]:
    request = load_json(WORKED_EXAMPLE_FILE)
    req, r = await assess(request, seed)
    q, ex = r.qiro_optimization, r.explanation
    plan = list(q["selected_actions"])
    mlkem = [a for a in plan if a["mitigation"] == "enable_hybrid_mlkem"]
    r_mlkem, rep_mlkem = await reassess(req, mlkem, settings=SETTINGS, seed=seed)
    r_full, rep_full = await reassess(req, plan, settings=SETTINGS, seed=seed)
    ev = await plan_reassessment.evaluate_scenario({"id": "worked_example_gateway", "title": "Worked example (Section III)",
                                                    "request": request}, seed, SETTINGS, 10)
    attribution = {a["category"]: a["contribution"] for a in ex["score_attribution"]}
    cfs = [{"removed_type": c["removed_type"], "after_pq_risk_score": c["after"]["pq_risk_score"],
            "after_status": c["after"]["environment_status"], "delta_pq_score": c["delta_pq_score"]} for c in ex["counterfactuals"]]
    best_cf = next((c for c in cfs if c["delta_pq_score"] < 0), None)
    candidates = [{k: a[k] for k in ("id", "finding_id", "finding_type", "mitigation", "cost_usd", "downtime_hrs", "complexity",
                                     "optimization_benefit")} for a in qiro.build_actions([f.model_dump() for f in r.findings])]
    independent = ev["exhaustive"]["independent_cost_model"]
    plan_b = ev["plan_b"]
    unit = next((g for g in plan_b["root_cause_groups"] if g["mitigation"] == "enable_hybrid_mlkem"), {})
    results = {
        "baseline": {**outcome(r), "raw_score": ex["raw_score"],
                     "score_attribution": [{k: a[k] for k in ("category", "label", "value", "weight", "contribution")}
                                           for a in ex["score_attribution"]],
                     "counterfactuals": cfs, "most_effective_fix": best_cf, "explanation_summary": ex["summary"]},
        "candidate_actions": candidates,
        "plan": {**plan_view(r), "optimality_gap_pct": (q.get("optimality") or {}).get("gap_pct")},
        "projection": projection(r),
        "reassessment": {
            "hybrid_mlkem_only": {**outcome(r_mlkem), "action_ids": [a["id"] for a in mlkem], "changes": rep_mlkem["changes"]},
            "full_plan": {**outcome(r_full), "action_ids": [a["id"] for a in plan], "changes": rep_full["changes"]},
        },
        "exhaustive": ev["exhaustive"],
        "shared_root_cause": {k: plan_b[k] for k in ("planner_mode", "selected_action_ids", "total_cost_usd", "total_downtime_hrs",
                                                    "projected_pq_score", "reassessed_pq_score", "reassessed_status",
                                                    "remaining_finding_types", "root_cause_groups")},
    }
    check = PaperCheck()
    sec = f"{PAPER}, Section VII-C"
    check.add("E5.findings", sec, "The framework raised five findings ...", 5, r.findings_count)
    check.add("E5.critical_findings", sec, "... one of them critical ...", 1, critical_count(r))
    check.add("E5.status", sec, "... and returned UNSAFE ...", "UNSAFE", r.environment_status)
    check.add("E5.pq_risk_score", sec, "... with S = 46.", 46, r.pq_risk_score)
    check.add("E5.raw_score", sec, "The exact attribution of the raw score 46.25 ...", 46.25, ex["raw_score"])
    for cat_key, value, text in (("pkc", 22.5, "22.5 points from classical public-key cryptography"),
                                 ("lifetime", 20.0, "20.0 from HNDL exposure"),
                                 ("migration", 3.75, "3.75 from the absence of any PQ algorithm")):
        check.add(f"E5.attribution.{cat_key}", sec, f"... was {text} ...", value, attribution[cat_key])
    check.add("E5.attribution.other", sec, "... and nothing from the other categories (deprecated TLS, device identity, "
              "secret exposure).", 0, sum(v for k, v in attribution.items() if k not in ("pkc", "lifetime", "migration")))
    check.add("E5.most_effective_fix", sec, "The counterfactuals named the HNDL finding as the single most effective fix (46 to 26).",
              {"removed_type": "long_lifetime_classical_crypto", "before": 46, "after": 26},
              {"removed_type": best_cf and best_cf["removed_type"], "before": r.pq_risk_score,
               "after": best_cf and best_cf["after_pq_risk_score"]})
    check.add("E5.plan_size", sec, "QIRO selected two of five candidate actions ...", {"selected": 2, "candidates": 5},
              {"selected": q["selection_count"], "candidates": q["total_candidate_actions"]})
    check.add("E5.plan_mitigations", sec, "... ML-DSA certificates and hybrid ML-KEM key exchange ...",
              ["enable_hybrid_mlkem", "pq_certificates"], plan_view(r)["mitigations"])
    check.add("E5.plan_cost_usd", sec, "... for 45,000 USD ...", 45_000, q["total_cost_usd"])
    check.add("E5.plan_downtime_hrs", sec, "... and 10 h of downtime.", 10, q["total_downtime_hrs"])
    check.add("E5.projected_pq_score", sec, "Its projection ... left S at 46.", 46, projection(r)["pq_risk_score"])
    check.add("E5.hybrid_only.pq_risk_score", sec, "Hybrid ML-KEM alone lowered S to 23 ...", 23, r_mlkem.pq_risk_score)
    check.add("E5.hybrid_only.pq_readiness", sec, "... (partially PQ).", "Partially PQ", r_mlkem.pq_posture.get("readiness"))
    check.add("E5.hybrid_only.hndl_finding", sec, "The HNDL finding disappeared because the key exchange that caused it had "
              "been replaced (long_lifetime_classical_crypto still raised = false).", False,
              any(f.type == "long_lifetime_classical_crypto" for f in r_mlkem.findings))
    check.add("E5.full_plan.pq_risk_score", sec, "... and the full plan to 0 ...", 0, r_full.pq_risk_score)
    check.add("E5.full_plan.findings", sec, "... with no findings.", 0, r_full.findings_count)
    check.add("E5.feasible_subsets", sec, "Of the seven feasible subsets of its five actions ...",
              {"subsets": 7, "actions": 5}, {"subsets": independent["feasible_subsets_reassessed"], "actions": len(candidates)},
              note=f"{independent['subsets_enumerated']} subsets enumerated; the feasible ones include the empty subset (no action)")
    check.add("E5.best_subset_outcome", sec, "... only this plan reaches 0 (SAFE): best reassessed outcome.",
              {"pq_risk_score": 0, "environment_status": "SAFE"},
              {k: independent["best_outcome"][k] for k in ("pq_risk_score", "environment_status")})
    check.add("E5.best_subset_is_plan", sec, "... only this plan reaches 0 (SAFE): one subset attains it and it is the plan.",
              {"subsets_attaining_best": 1, "is_the_plan": True},
              {"subsets_attaining_best": independent["subsets_attaining_best"],
               "is_the_plan": sorted(independent["cheapest_best_subset"]["action_ids"]) == sorted(a["id"] for a in plan)})
    check.add("E5.shared_root_cause.unit_cost_usd", sec, "The shared-root-cause mode, which costs the merged ML-KEM unit at "
              "50,000 USD ...", 50_000, unit.get("cost_usd"))
    check.add("E5.shared_root_cause.reassessed_pq_score", sec, "... reaches 23.", 23, plan_b["reassessed_pq_score"])
    return envelope("e5", "Worked example of Section III: explanation, plan, projection and re-assessment", seed,
                    {"file": rel(WORKED_EXAMPLE_FILE), "request": request}, E5_METHOD, results, check)


# ------------------------------------------------------------------------------------------------- main


EXPERIMENTS = {"e1": e1, "e2": e2, "e3": e3, "e4": e4, "e5": e5}


def run(which: Sequence[str], seed: int = SEED) -> dict[str, dict[str, Any]]:
    """Run the selected experiments in order and return {experiment: artifact}."""
    return {k: asyncio.run(EXPERIMENTS[k](seed)) for k in which}


def parse_only(text: str) -> list[str]:
    keys = [k.strip().lower() for k in text.split(",") if k.strip()]
    unknown = [k for k in keys if k not in EXPERIMENTS]
    if unknown or not keys:
        raise argparse.ArgumentTypeError(f"choose from {','.join(EXPERIMENTS)} (got {text!r})")
    return [k for k in EXPERIMENTS if k in keys]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", type=parse_only, default=list(EXPERIMENTS), help="comma-separated subset of e1,e2,e3,e4,e5 (default: all)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "benchmarks" / "results")
    ap.add_argument("--seed", type=int, default=SEED, help="assessment seed (the paper uses 2026)")
    ap.add_argument("--strict", action="store_true", help="exit with status 1 if any number stated in the paper is not reproduced")
    args = ap.parse_args(argv)
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:  # never fail on characters the console cannot encode
        reconfigure(errors="backslashreplace")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    mismatched = 0
    for key in args.only:
        data = run([key], args.seed)[key]
        out = args.out_dir / ARTIFACTS[key]
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        s = data["paper_check"]["summary"]
        mismatched += s["mismatched"]
        print(f"{key.upper()} {data['title']}: {s['matched']}/{s['stated_values']} stated values reproduced -> {out.name}")
        for c in data["paper_check"]["checks"]:
            if not c["match"]:
                print(f"  MISMATCH {c['id']}: expected {json.dumps(c['expected'])}, reproduced {json.dumps(c['reproduced'])}"
                      f" ({c['statement']})")
    print("all stated values reproduced" if not mismatched else f"{mismatched} stated value(s) not reproduced")
    return 1 if args.strict and mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
