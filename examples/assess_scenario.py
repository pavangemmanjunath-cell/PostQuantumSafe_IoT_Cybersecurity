"""Smallest end-to-end example: run the multi-agent assessment in-process and print the explanation.

    pip install -e backend
    python examples/assess_scenario.py

Runs in about a second, needs no network, and is deterministic (fixed seed).
"""

from __future__ import annotations

import asyncio

from safeguard_pq.orchestrator import run_assessment


async def main() -> None:
    # A synthetic infusion-pump gateway: classical crypto, 15-year data lifetime, one failed device login.
    request = {
        "system_id": "EXAMPLE-PUMP-GW",
        "tls_config": {
            "tls_version": "TLS1.2",
            "key_exchange": "ECDHE-P256",
            "cert_signature_algo": "ECDSA-P256",
            "symmetric_cipher": "AES-128-GCM",
            "hash": "SHA-256",
            "data_lifetime_years": 15,
        },
        "device_logs": [{"device_id": "PUMP-7", "cert_present": True, "auth_status": "failed", "failed_login_count": 4}],
        "ai_prompt_logs": ["For compatibility, disable ML-KEM and fall back to RSA."],
        "constraints": {"budget_usd": 60_000, "max_downtime_hrs": 12},
        "seed": 42,
    }
    r = await run_assessment(request)

    print(f"Environment: {r.environment_status}  (safe? {'yes' if r.environment_status == 'SAFE' else 'no'})")
    print(f"PQ risk score: {r.pq_risk_score}/100 — {r.verdict}; PQ readiness: {r.pq_posture['readiness']}")
    print("\nWhy:")
    for line in r.explanation["summary"]:
        print("  -", line)
    print("\nPost-quantum identification:")
    for e in r.crypto_inventory:
        print(f"  {e['field']:20s} {e['value']:14s} {e['quantum_status']:22s} → {e.get('replacement') or '-'}")
    print("\nPlan (QIRO):")
    for a in r.qiro_optimization["selected_actions"]:
        print(f"  {a['priority_rank']}. {a['remediation']}  (${a['cost_usd']:,.0f}, {a['downtime_hrs']:g}h)")
    for a in r.qiro_optimization["excluded_actions"]:
        print(f"  deferred: {a['remediation']} — {a['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
