"""Plan reassessment: apply a QIRO plan to the assessed configuration and re-run the pipeline.

The planner's projection (``explanation.plan_projection``) assumes that every selected action removes exactly
its own finding. Two things break that assumption: shared root causes (one mitigation removes several findings,
so the projection is pessimistic) and controls the configuration model cannot observe (network mitigations, so
the projection is optimistic). This module applies the *mitigations* of a plan to a deep copy of the original
request exactly as the fleet simulator's ``Simulation.mitigate`` changes a device, re-runs the same agent
pipeline on the result, and reports summed benefit, projected score and reassessed score side by side.

The "after" configuration is produced by code from the plan; nothing is edited by hand. Reassessment is
configuration-level only: it changes the TLS configuration, device records and AI prompt logs. It cannot
generate post-mitigation traffic, so network mitigations (rate limiting, segmentation) are reported as
unmodelled and the traffic findings they target remain in the reassessed result.
"""

from __future__ import annotations

from typing import Any

from ..agents.base import as_list
from ..agents.text import prompt_text
from ..config import Settings
from ..domain.models import AssessmentRequest, AssessmentResult
from ..knowledge import patterns
from ..knowledge.redaction import redact
from ..orchestrator.pipeline import run_assessment
from ..simulation.catalog import MITIGATIONS

METHOD = (
    "Configuration-level reassessment: the plan's mitigations are applied to a deep copy of the original request "
    "exactly as Simulation.mitigate changes a device (TLS configuration update, device re-authentication, "
    "certificate issuance, log scrubbing, prompt redaction or filtering); the same agent pipeline is then re-run "
    "with the same seed. The projected score assumes each selected action removes only its own finding."
)
CAVEAT = (
    "Network mitigations (rate limiting, segmentation) cannot be modelled at configuration level because the "
    "model cannot observe post-mitigation traffic: iot_traffic is left unchanged and traffic findings remain. "
    "Record-level PHI remediation of ehr_records is not modelled. Scenarios are synthetic."
)

NETWORK_MITIGATIONS: frozenset[str] = frozenset(m.id for m in MITIGATIONS.values() if m.layer == "network")
PROMPT_MITIGATIONS: frozenset[str] = frozenset({"phi_redaction", "prompt_firewall", "clinician_approval_gate"})
_PROMPT_FILTERS = {"prompt_firewall": patterns.INJECTION_RULES, "clinician_approval_gate": patterns.UNSAFE_RULES}


def _redact_obj(value: Any) -> Any:
    """Redact every string leaf of a prompt entry (the privacy agent scans the JSON of non-text entries)."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_obj(v) for v in value]
    return value


def _matching_rules(text: str, rules: list[patterns.Rule]) -> list[str]:
    return [r.type for r in rules if r.pattern.search(text)]


def _issue_certificate(d: dict[str, Any], mitigation: str, idx: int, changes: list[str]) -> None:
    if d.get("cert_present") is False:
        d["cert_present"] = True
        changes.append(f"device_logs[{idx}].cert_present: False -> True ({mitigation})")
    if "certificate" in d and d["certificate"] is None:
        d["certificate"] = {"issued_by": mitigation}
        changes.append(f"device_logs[{idx}].certificate: None -> issued ({mitigation})")


def _apply_config(req: AssessmentRequest, mitigation: str, config: dict[str, Any], changes: list[str],
                  notes: list[str]) -> None:
    if req.tls_config is None:
        notes.append(f"{mitigation}: the request has no tls_config, so its configuration change {config} "
                     "could not be applied (PQ posture stays unverified)")
        return
    for key, value in config.items():
        old = getattr(req.tls_config, key, None)
        if old == value:
            continue
        setattr(req.tls_config, key, value)
        changes.append(f"tls_config.{key}: {old!r} -> {value!r} ({mitigation})")


def _apply_devices(req: AssessmentRequest, mitigation: str, changes: list[str], notes: list[str]) -> None:
    entries = as_list(req.device_logs)
    records = [(i, d) for i, d in enumerate(entries) if isinstance(d, dict)]
    if len(records) < len(entries):
        notes.append(f"{mitigation}: {len(entries) - len(records)} non-record device log entr(y/ies) left unchanged")
    for i, d in records:
        if mitigation == "device_reauth":
            if d.get("auth_status") == "failed":
                d["auth_status"] = "passed"
                changes.append(f"device_logs[{i}].auth_status: 'failed' -> 'passed' (device_reauth)")
            fails = d.get("failed_login_count")
            if isinstance(fails, int | float) and fails > 0:
                d["failed_login_count"] = 0
                changes.append(f"device_logs[{i}].failed_login_count: {fails:g} -> 0 (device_reauth)")
            _issue_certificate(d, mitigation, i, changes)
        elif mitigation == "pq_certificates":
            _issue_certificate(d, mitigation, i, changes)
        elif mitigation == "secret_rotation":
            if d.get("debug_log"):
                d["debug_log"] = ""
                changes.append(f"device_logs[{i}].debug_log scrubbed (secret_rotation)")


def _apply_prompts(req: AssessmentRequest, mitigation: str, changes: list[str], notes: list[str]) -> None:
    prompts = as_list(req.ai_prompt_logs)
    if not prompts:
        notes.append(f"{mitigation}: no AI prompt logs to filter")
        return
    kept: list[Any] = []
    for i, p in enumerate(prompts):
        if mitigation == "phi_redaction":
            new = _redact_obj(p)
            if new != p:
                changes.append(f"ai_prompt_logs[{i}] redacted (phi_redaction)")
            kept.append(new)
            continue
        text = prompt_text(p, stringify_objects=False)
        hits = _matching_rules(text, _PROMPT_FILTERS[mitigation]) if text else []
        if hits:
            changes.append(f"ai_prompt_logs[{i}] dropped by {mitigation} ({', '.join(hits)})")
            continue
        kept.append(p)
    req.ai_prompt_logs = kept
    if mitigation == "phi_redaction" and req.ehr_records is not None:
        notes.append("phi_redaction: ehr_records left unchanged; record-level PHI remediation is not modelled")


def apply_plan(request: AssessmentRequest, selected_actions: list[dict[str, Any]]) -> tuple[AssessmentRequest, dict[str, Any]]:
    """Apply the plan's mitigations to a deep copy of ``request`` and describe what changed.

    Returns the modified request and a report with ``applied_mitigations`` (ids), ``unmodelled_mitigations``
    (ids), ``unmodelled_reasons`` (id -> why), ``changes`` (human-readable list of configuration edits) and
    ``notes`` (caveats such as inputs that were absent or not modelled).
    """
    req = request.model_copy(deep=True)
    report: dict[str, Any] = {"applied_mitigations": [], "unmodelled_mitigations": [], "unmodelled_reasons": {},
                              "changes": [], "notes": [], "plan_action_ids": [a.get("id") for a in selected_actions]}
    changes, notes = report["changes"], report["notes"]
    ordered: list[str] = []
    for a in selected_actions:
        m = a.get("mitigation")
        if m is None:
            report["unmodelled_mitigations"].append(f"{a.get('id')}:{a.get('finding_type')}")
            report["unmodelled_reasons"][f"{a.get('id')}:{a.get('finding_type')}"] = (
                "no simulator mitigation is mapped to this action, so it cannot be applied at configuration level")
        elif m not in ordered:
            ordered.append(m)
    for m in ordered:
        spec = MITIGATIONS.get(m)
        if spec is None:
            report["unmodelled_mitigations"].append(m)
            report["unmodelled_reasons"][m] = "unknown mitigation id"
            continue
        if m in NETWORK_MITIGATIONS:
            report["unmodelled_mitigations"].append(m)
            report["unmodelled_reasons"][m] = (
                f"{spec.label} is a network control; the configuration model cannot observe post-mitigation "
                "traffic, so iot_traffic is left unchanged and the traffic findings it targets remain")
            continue
        if spec.config:
            _apply_config(req, m, spec.config, changes, notes)
        if m in ("device_reauth", "pq_certificates", "secret_rotation"):
            _apply_devices(req, m, changes, notes)
        if m in PROMPT_MITIGATIONS:
            _apply_prompts(req, m, changes, notes)
        if not spec.config and m not in PROMPT_MITIGATIONS and m not in ("device_reauth", "pq_certificates", "secret_rotation"):
            notes.append(f"{m}: policy control with no configuration fields in the catalogue; applied as a no-op")
        report["applied_mitigations"].append(m)
    return req, report


async def reassess(request: AssessmentRequest, selected_actions: list[dict[str, Any]], *, settings: Settings | None = None,
                   seed: int | None = None) -> tuple[AssessmentResult, dict[str, Any]]:
    """Apply ``selected_actions`` to ``request`` and re-run the full pipeline (deterministic; no LLM narrative)."""
    req, report = apply_plan(request, selected_actions)
    req.options.llm_report = False
    if seed is not None:
        req.seed = seed
    result = await run_assessment(req, settings=settings)
    return result, report


def _summary(result: AssessmentResult) -> dict[str, Any]:
    return {"pq_risk_score": result.pq_risk_score, "environment_status": result.environment_status,
            "verdict": result.verdict,
            "findings": [{"id": f.id, "type": f.type, "severity": f.severity, "agent": f.agent} for f in result.findings]}


async def evaluate_plan_by_reassessment(request: AssessmentRequest | dict[str, Any], result: AssessmentResult | dict[str, Any],
                                        *, settings: Settings | None = None) -> dict[str, Any]:
    """Compare the planner's summed benefit and projected score with the score obtained by reassessment."""
    req = request if isinstance(request, AssessmentRequest) else AssessmentRequest.model_validate(request)
    res = result if isinstance(result, AssessmentResult) else AssessmentResult.model_validate(result)
    qiro = res.qiro_optimization or {}
    selected = list(qiro.get("selected_actions", []))
    seed = res.metadata.get("seed") if isinstance(res.metadata, dict) else None
    after, report = await reassess(req, selected, settings=settings, seed=seed if seed is not None else req.seed)
    projected = ((res.explanation or {}).get("plan_projection") or {}).get("after") or {}
    proj_score = projected.get("pq_risk_score")
    return {
        "planner_mode": qiro.get("planner_mode", "independent_actions"),
        "selected_action_ids": [a.get("id") for a in selected],
        "selected_finding_ids": [a.get("finding_id") for a in selected],
        "total_cost_usd": qiro.get("total_cost_usd", 0),
        "total_downtime_hrs": qiro.get("total_downtime_hrs", 0),
        "summed_benefit": sum(a.get("optimization_benefit", 0) for a in selected),
        "total_risk_reduction": qiro.get("total_risk_reduction", 0),
        "projected_pq_score": proj_score,
        "projected_status": projected.get("environment_status"),
        "reassessed_pq_score": after.pq_risk_score,
        "reassessed_status": after.environment_status,
        "reassessed_verdict": after.verdict,
        "projection_error": None if proj_score is None else after.pq_risk_score - proj_score,
        "remaining_finding_types": sorted({f.type for f in after.findings}),
        "remaining_findings": _summary(after)["findings"],
        "applied": report,
        "before": _summary(res),
        "method": METHOD,
        "caveat": CAVEAT,
    }
