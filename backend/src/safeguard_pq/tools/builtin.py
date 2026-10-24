"""Built-in tools used by the agents."""

from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings
from ..domain.models import PILLARS
from ..knowledge import patterns, pqc_catalog, remediation, traffic_rules
from ..knowledge.redaction import excerpt
from .registry import Tool, ToolError, ToolRegistry

_TEXT = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}


def scan_rules(rules: list[patterns.Rule], text: str) -> list[dict[str, Any]]:
    """Return one hit per rule that matches, with match count and a redacted excerpt."""
    hits = []
    for rule in rules:
        matches = list(rule.pattern.finditer(text))
        if matches:
            hits.append({
                "type": rule.type,
                "severity": rule.severity,
                "description": rule.description,
                "match_count": len(matches),
                "excerpt": excerpt(text, matches[0]),
                "rule": rule.pattern.pattern,
            })
    return hits


def _summ_hits(hits: list[dict]) -> str:
    return "no match" if not hits else ", ".join(f"{h['type']}×{h['match_count']}" for h in hits)


def mosca(data_lifetime_years: float, migration_years: float = 5, years_to_crqc: float = 10) -> dict[str, Any]:
    """Mosca's inequality: data is at risk if shelf-life x + migration time y > time-to-CRQC z."""
    x, y, z = float(data_lifetime_years), float(migration_years), float(years_to_crqc)
    return {
        "x_data_lifetime_years": x,
        "y_migration_years": y,
        "z_years_to_crqc": z,
        "at_risk": x + y > z,
        "margin_years": round(z - (x + y), 2),
        "note": "Mosca (2015/2018). z is a highly uncertain assumption supplied by the user, not a prediction.",
    }


def openfda_device_recalls(query: str, limit: int = 3) -> dict[str, Any]:
    if not get_settings().online_tools_enabled:
        raise ToolError("online tools are disabled (set ONLINE_TOOLS_ENABLED=true)")
    limit = max(1, min(int(limit), 10))
    url = "https://api.fda.gov/device/recall.json"
    params = {"search": f'product_description:"{query}"', "limit": limit}
    try:
        r = httpx.get(url, params=params, timeout=10)
    except httpx.HTTPError as exc:
        raise ToolError(f"openFDA request failed: {exc}") from exc
    if r.status_code == 404:
        return {"query": query, "results": [], "source": url}
    r.raise_for_status()
    items = []
    for it in r.json().get("results", []):
        items.append({
            "product_description": (it.get("product_description") or "")[:200],
            "reason_for_recall": (it.get("reason_for_recall") or "")[:300],
            "recall_status": it.get("recall_status"),
            "event_date_initiated": it.get("event_date_initiated"),
            "root_cause_description": it.get("root_cause_description"),
        })
    return {"query": query, "results": items, "source": url, "license": "openFDA data is public domain (CC0)"}


def register_builtin_tools(reg: ToolRegistry) -> None:
    reg.register(Tool(
        "pqc.classify_algorithm",
        "Classify a cryptographic algorithm / protocol name into its quantum-threat status (Shor, Grover, PQ-safe, hybrid…).",
        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        lambda name: pqc_catalog.classify(name).to_dict(),
        summarize=lambda r: f"{r['display']} → {r['quantum_status']}",
        category="post-quantum",
    ))
    reg.register(Tool(
        "pqc.catalog",
        "List the post-quantum identification knowledge base.",
        {"type": "object", "properties": {}},
        pqc_catalog.catalog,
        category="post-quantum",
    ))
    reg.register(Tool(
        "pqc.mosca_inequality",
        "Evaluate Mosca's inequality x + y > z for harvest-now-decrypt-later exposure using explicit assumptions.",
        {
            "type": "object",
            "properties": {
                "data_lifetime_years": {"type": "number"},
                "migration_years": {"type": "number"},
                "years_to_crqc": {"type": "number"},
            },
            "required": ["data_lifetime_years"],
        },
        mosca,
        summarize=lambda r: f"x+y={r['x_data_lifetime_years'] + r['y_migration_years']:g} vs z={r['z_years_to_crqc']:g} → {'AT RISK' if r['at_risk'] else 'ok'}",
        category="post-quantum",
    ))
    reg.register(Tool("privacy.scan_phi", "Detect PHI patterns (MRN, SSN, names, email, sensitive diagnoses) in text.",
                      _TEXT, lambda text: scan_rules(patterns.PHI_RULES, text), summarize=_summ_hits, category="privacy"))
    reg.register(Tool("security.scan_prompt_injection", "Detect prompt-injection, PQ-downgrade and tool-hijack instructions in text.",
                      _TEXT, lambda text: scan_rules(patterns.INJECTION_RULES, text), summarize=_summ_hits, category="security"))
    reg.register(Tool("security.scan_secrets", "Detect exposed credentials (cloud keys, tokens, private keys) in text.",
                      _TEXT, lambda text: scan_rules(patterns.SECRET_RULES, text), summarize=_summ_hits, category="security"))
    reg.register(Tool("safety.scan_unsafe_instructions", "Detect unsafe autonomous clinical instructions (dosing, alarm override…).",
                      _TEXT, lambda text: scan_rules(patterns.UNSAFE_RULES, text), summarize=_summ_hits, category="safety"))
    reg.register(Tool(
        "traffic.analyze_features",
        "Compute flow features from CICIoMT-style traffic (window, summary or features) and evaluate anomaly rules.",
        {"type": "object", "properties": {"iot_traffic": {"type": "object"}}, "required": ["iot_traffic"]},
        lambda iot_traffic: (lambda f: {"features": f, "rules": traffic_rules.evaluate(f) if f else []})(
            traffic_rules.extract_features(iot_traffic)
        ),
        summarize=lambda r: (", ".join(x["type"] for x in r["rules"] if x["hit"]) or "no rule fired") if r["features"] else "no usable features",
        category="network",
    ))
    reg.register(Tool(
        "remediation.lookup",
        "Look up the remediation action template (illustrative cost, downtime, risk reduction) for a finding type.",
        {"type": "object", "properties": {"finding_type": {"type": "string"}}, "required": ["finding_type"]},
        lambda finding_type: {"finding_type": finding_type, **remediation.template_for(finding_type).__dict__},
        summarize=lambda r: f"${r['cost']:,.0f}, {r['downtime']:g}h",
        category="planning",
    ))
    reg.register(Tool(
        "standards.tippss_pillars",
        "Return the IEEE 2933-2024 TIPPSS pillars used for mapping.",
        {"type": "object", "properties": {}},
        lambda: list(PILLARS),
        category="standards",
    ))
    reg.register(Tool(
        "openfda.device_recalls",
        "LIVE: query the public openFDA medical-device recall API (disabled unless ONLINE_TOOLS_ENABLED=true).",
        {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
        openfda_device_recalls,
        summarize=lambda r: f"{len(r['results'])} recall record(s)",
        online=True,
        category="live-data",
    ))
