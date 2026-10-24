"""Pure scoring functions (TIPPSS pillars, PQ risk score, environment status).

Kept free of agent plumbing so the explainer can re-evaluate them on
counterfactual finding sets. Constants reproduce the v0 prototype.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ..domain.models import PILLARS, Finding
from ..optimizer.qiro import js_round

PILLAR_DEDUCT = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 0}
WEIGHTS = {"pkc": 0.30, "tls": 0.20, "lifetime": 0.20, "identity": 0.15, "secrets": 0.10, "migration": 0.05}
POINTS = {"critical": 100, "high": 75, "medium": 50, "low": 25}
CATEGORY_LABELS = {
    "pkc": "Classical public-key crypto",
    "tls": "Deprecated TLS",
    "lifetime": "Harvest-now-decrypt-later (data lifetime)",
    "identity": "Device identity",
    "secrets": "Secret exposure",
    "migration": "No PQ algorithm in use",
}


def tippss_pillars(findings: Iterable[Finding]) -> dict[str, dict[str, Any]]:
    pillars: dict[str, dict[str, Any]] = {p: {"score": 100, "finding_ids": [], "deductions": []} for p in PILLARS}
    for f in findings:
        ded = PILLAR_DEDUCT.get(f.severity, 5)
        for p in f.tippss_mapping:
            if p in pillars:
                pillars[p]["finding_ids"].append(f.id)
                pillars[p]["deductions"].append({"finding_id": f.id, "type": f.type, "severity": f.severity, "points": ded})
                pillars[p]["score"] = max(0, pillars[p]["score"] - ded)
    return pillars


def category_of(f: Finding) -> str | None:
    if f.agent == "crypto_inventory" and f.type == "deprecated_tls_version":
        return "tls"
    if f.agent == "pq_identification" and f.type == "long_lifetime_classical_crypto":
        return "lifetime"
    if f.agent in ("pq_identification", "crypto_inventory"):
        return "pkc"
    if f.agent == "device_identity":
        return "identity"
    if f.agent == "secret_exposure":
        return "secrets"
    return None


def pq_score(findings: Sequence[Finding], pq_detected: bool) -> dict[str, Any]:
    cat = {k: 0.0 for k in WEIGHTS}
    drivers: dict[str, list[str]] = {k: [] for k in WEIGHTS}
    for f in findings:
        c = category_of(f)
        if c is None:
            continue
        pts = POINTS.get(f.severity, 25)
        if pts > cat[c]:
            cat[c], drivers[c] = pts, [f.id]
        elif pts == cat[c] and pts > 0:
            drivers[c].append(f.id)
    cat["migration"] = 0 if pq_detected else 75
    raw = sum(cat[k] * WEIGHTS[k] for k in WEIGHTS)
    score = js_round(raw)
    return {"pq_risk_score": score, "raw_score": raw, "status": verdict(score), "category_breakdown": cat, "drivers": drivers}


def verdict(score: float) -> str:
    if score <= 25:
        return "Safe"
    if score <= 50:
        return "Partially Safe"
    if score <= 75:
        return "Not Post-Quantum Safe"
    return "Critical Quantum Risk"


def environment_status(findings: Sequence[Finding], score: int, has_tls: bool) -> tuple[str, list[str]]:
    """Overall SAFE / AT_RISK / UNSAFE across every TIPPSS dimension, with reasons."""
    crit = [f for f in findings if f.severity == "critical"]
    elevated = [f for f in findings if f.severity in ("high", "medium")]
    reasons: list[str] = []
    if crit:
        reasons.append(f"{len(crit)} critical finding(s): {', '.join(sorted({f.type for f in crit}))}")
    if score > 50:
        reasons.append(f"PQ risk score {score}/100 exceeds 50")
    if crit or score > 50:
        return "UNSAFE", reasons
    if elevated:
        reasons.append(f"{len(elevated)} high/medium finding(s): {', '.join(sorted({f.type for f in elevated}))}")
    if score > 25:
        reasons.append(f"PQ risk score {score}/100 exceeds 25")
    if not has_tls:
        reasons.append("no cryptographic configuration supplied, so PQ safety is unverified")
    if reasons:
        return "AT_RISK", reasons
    return "SAFE", ["no findings across the evaluated controls and PQ algorithms are in use"]
