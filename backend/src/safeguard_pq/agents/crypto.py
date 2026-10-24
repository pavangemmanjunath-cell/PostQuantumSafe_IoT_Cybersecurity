"""Cryptographic inventory and post-quantum identification agents."""

from __future__ import annotations

from datetime import date
from typing import Any

from ..domain.models import Evidence
from ..knowledge import pqc_catalog as pq
from ..optimizer.qiro import fmt_num
from .base import Agent, AgentRecorder, AgentSpec, RunContext

TLS_FIELDS = ("tls_version", "key_exchange", "cert_signature_algo", "cert_key_algo", "symmetric_cipher", "hash")

# v0 recommendation table (order matters: first key contained in the detected value wins),
# extended in 0.1.0 with additional classical families.
PQ_REC: dict[str, tuple[str, str]] = {
    "RSA": ("ML-KEM-768 (FIPS 203) + ML-DSA-65 (FIPS 204)", "high"),
    "ECDHE": ("X25519 + ML-KEM-768 hybrid first, then full ML-KEM-768", "high"),
    "ECDH": ("ML-KEM-768 (FIPS 203) hybrid first", "high"),
    "ECDSA": ("ML-DSA-65 (FIPS 204) hybrid first", "high"),
    "ECC": ("ML-KEM-768 + ML-DSA-65", "high"),
    "X25519": ("X25519 + ML-KEM-768 hybrid (X25519MLKEM768)", "high"),
    "X448": ("X448 + ML-KEM-1024 hybrid", "high"),
    "ED25519": ("ML-DSA-65 (FIPS 204)", "high"),
    "EDDSA": ("ML-DSA-65 (FIPS 204)", "high"),
    "DH": ("ML-KEM-768 (FIPS 203)", "high"),
}

NON_PKC_TYPES = {"weak_hash", "deprecated_tls_version", "weak_symmetric_cipher"}


def _ev(field: str, value: Any, prim: pq.Primitive) -> list[Evidence]:
    return [Evidence(source=f"tls_config.{field}", rule=f"pqc_catalog:{prim.key} ({prim.quantum_status})",
                     observed=str(value), reference="; ".join(prim.references) or None)]


class CryptoInventoryAgent(Agent):
    spec = AgentSpec(
        id="crypto_inventory",
        title="Crypto Inventory",
        description="Builds a cryptographic bill of materials from the TLS configuration and flags deprecated protocols, "
                    "weak hashes and quantum-vulnerable public-key algorithms.",
        layer="post-quantum",
        reads=("tls_config",),
        produces=("crypto_inventory",),
        tools=("pqc.classify_algorithm",),
    )

    def applicable(self, ctx: RunContext) -> tuple[bool, str]:
        return (ctx.request.tls_config is not None, "no tls_config supplied")

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        tls = ctx.request.tls_config
        assert tls is not None
        inventory: list[dict[str, Any]] = []
        prims: dict[str, pq.Primitive] = {}
        for field in TLS_FIELDS:
            value = getattr(tls, field)
            if not value:
                continue
            info = await rec.tool("pqc.classify_algorithm", name=str(value))
            prim = pq.classify(str(value))
            prims[field] = prim
            inventory.append({"field": field, "value": value, **info})
        ctx.artifacts["crypto_inventory"] = inventory

        if (p := prims.get("tls_version")) and p.quantum_status == pq.DEPRECATED:
            ref = "RFC 8996" if p.key == "tls_legacy" else "RFC 7568"
            detail = (f"{tls.tls_version} deprecated since 2020 (RFC 8996)" if p.key == "tls_legacy"
                      else f"{tls.tls_version} deprecated ({ref})")
            rec.finding(severity="critical", type="deprecated_tls_version", detail=detail, detected_value=tls.tls_version,
                        tippss_mapping=["Security", "Protection"], evidence=_ev("tls_version", tls.tls_version, p))

        sig_flagged = False
        if (p := prims.get("key_exchange")) and p.quantum_status == pq.VULNERABLE:
            rec.finding(severity="high", type="classical_key_exchange", detail=f"{tls.key_exchange} key exchange not PQ safe",
                        detected_value=tls.key_exchange, tippss_mapping=["Security", "Protection"],
                        evidence=_ev("key_exchange", tls.key_exchange, p))
        if (p := prims.get("cert_signature_algo")) and p.quantum_status == pq.VULNERABLE:
            sig_flagged = True
            rec.finding(severity="high", type="classical_signature",
                        detail=f"{tls.cert_signature_algo} certificate signature not PQ safe",
                        detected_value=tls.cert_signature_algo, tippss_mapping=["Security", "Identity", "Protection"],
                        evidence=_ev("cert_signature_algo", tls.cert_signature_algo, p))
        if (p := prims.get("cert_key_algo")) and p.quantum_status == pq.VULNERABLE and not sig_flagged:
            rec.finding(severity="high", type="classical_certificate_key",
                        detail=f"{tls.cert_key_algo} certificate key pair not PQ safe",
                        detected_value=tls.cert_key_algo, tippss_mapping=["Security", "Identity", "Protection"],
                        evidence=_ev("cert_key_algo", tls.cert_key_algo, p))
        if (p := prims.get("hash")) and p.quantum_status == pq.CLASSICALLY_BROKEN:
            rec.finding(severity="critical", type="weak_hash", detail=f"{tls.hash} collision-vulnerable",
                        detected_value=tls.hash, tippss_mapping=["Security", "Protection"], evidence=_ev("hash", tls.hash, p))
        if (p := prims.get("symmetric_cipher")) and p.quantum_status == pq.CLASSICALLY_BROKEN:
            rec.finding(severity="high", type="weak_symmetric_cipher", detail=f"{tls.symmetric_cipher} is a deprecated cipher",
                        detected_value=tls.symmetric_cipher, tippss_mapping=["Security", "Protection"],
                        evidence=_ev("symmetric_cipher", tls.symmetric_cipher, p))

        vulnerable = [e["value"] for e in inventory if e["quantum_status"] == pq.VULNERABLE]
        safe = [e["value"] for e in inventory if e["quantum_status"] in pq.PQ_SAFE_STATUSES]
        await rec.note(f"Inventoried {len(inventory)} primitive(s): {len(vulnerable)} quantum-vulnerable, {len(safe)} PQ-safe/hybrid.")
        if vulnerable:
            await rec.note(f"Quantum-vulnerable (Shor): {', '.join(map(str, vulnerable))}.")
        await rec.note(f"Raised {len(rec.staged)} crypto finding(s).")


class PQIdentificationAgent(Agent):
    spec = AgentSpec(
        id="pq_identification",
        title="Post-Quantum Identification",
        description="Determines PQ readiness, maps each classical algorithm to its NIST PQC replacement, and evaluates "
                    "harvest-now-decrypt-later exposure (data lifetime, Mosca's inequality).",
        layer="post-quantum",
        reads=("tls_config", "crypto findings", "assumptions"),
        produces=("pq_posture",),
        tools=("pqc.classify_algorithm", "pqc.mosca_inequality"),
    )

    async def run(self, ctx: RunContext, rec: AgentRecorder) -> None:
        tls = ctx.request.tls_config
        classical = [f for f in ctx.findings if f.agent == "crypto_inventory" and f.type not in NON_PKC_TYPES]

        seen: set[str] = set()
        for f in classical:
            detected = str(getattr(f, "detected_value", "") or "").upper()
            algo = next((a for a in PQ_REC if a in detected), None)
            if algo and algo not in seen:
                seen.add(algo)
                recommendation, priority = PQ_REC[algo]
                rec.finding(
                    severity="high", type="pq_migration_required", detail=f"{algo} vulnerable to Shor's algorithm",
                    detected_algorithm=algo, recommendation=recommendation, priority=priority,
                    tippss_mapping=["Security", "Protection"],
                    evidence=[Evidence(source=f"finding:{f.id}", rule="Shor's algorithm breaks RSA/DH/ECC on a CRQC",
                                       observed=str(getattr(f, "detected_value", "")),
                                       reference="NIST IR 8547 ipd; FIPS 203/204/205")],
                )

        lifetime = tls.data_lifetime_years if tls else None
        has_classical = bool(classical)
        mosca = None
        if tls and lifetime:
            a = ctx.request.assumptions
            mosca = await rec.tool("pqc.mosca_inequality", data_lifetime_years=lifetime,
                                   migration_years=a.migration_years, years_to_crqc=a.years_to_crqc)
        # Correction vs v0: harvest-now-decrypt-later concerns confidentiality, so it applies only when the
        # key exchange is not PQ/hybrid protected (classical signatures cannot be "harvested" retroactively).
        kex_pq_safe = bool(tls and pq.is_pq_safe(tls.key_exchange))
        if tls and lifetime and lifetime >= 10 and has_classical and not kex_pq_safe:
            rec.finding(
                severity="critical", type="long_lifetime_classical_crypto",
                detail=f"{fmt_num(lifetime)}-year lifetime + classical crypto = severe harvest-now-decrypt-later exposure",
                tippss_mapping=["Privacy", "Protection", "Security"],
                evidence=[Evidence(source="tls_config.data_lifetime_years", rule="lifetime ≥ 10 years with classical public-key crypto",
                                   observed=fmt_num(lifetime), reference="Mosca's inequality; NIST IR 8547 ipd")],
            )

        # Mosca what-if: below the 10-year rule but at risk under the user's Q-Day assumptions.
        elif tls and mosca and mosca["at_risk"] and has_classical and not kex_pq_safe:
            rec.finding(
                severity="medium", type="mosca_hndl_exposure",
                detail=(f"Mosca's inequality: {fmt_num(mosca['x_data_lifetime_years'])}y data lifetime + "
                        f"{fmt_num(mosca['y_migration_years'])}y migration > {fmt_num(mosca['z_years_to_crqc'])}y to CRQC (assumed)"),
                tippss_mapping=["Privacy", "Protection"],
                evidence=[Evidence(source="assumptions + tls_config.data_lifetime_years", rule="x + y > z with classical key exchange",
                                   observed=f"x={fmt_num(mosca['x_data_lifetime_years'])}, y={fmt_num(mosca['y_migration_years'])}, z={fmt_num(mosca['z_years_to_crqc'])}",
                                   reference="Mosca (2018), IEEE Security & Privacy 16(5)")],
            )

        posture = self._posture(tls, mosca, has_classical)
        ctx.artifacts["pq_posture"] = posture
        await rec.note(f"PQ readiness: {posture['readiness']} — {posture['readiness_reason']}")
        if mosca:
            await rec.note(
                f"Mosca: x={mosca['x_data_lifetime_years']:g}y + y={mosca['y_migration_years']:g}y vs z={mosca['z_years_to_crqc']:g}y "
                f"(assumed) → {'AT RISK' if mosca['at_risk'] else 'within margin'}."
            )
        if posture["hndl_exposed"]:
            await rec.note(f"Data protected today must stay confidential until ~{posture['protect_until_year']}; "
                           "traffic captured now could be decrypted later.")
        for adv in posture["advisories"]:
            await rec.note(f"Advisory: {adv}")

    @staticmethod
    def _posture(tls: Any, mosca: dict | None, has_classical: bool) -> dict[str, Any]:
        if tls is None:
            return {"readiness": "Unknown", "readiness_reason": "no TLS configuration supplied", "pq_detected": False,
                    "pq_key_exchange": False, "pq_signature": False, "hybrid": False, "hndl_exposed": False,
                    "protect_until_year": None, "mosca": None, "advisories": []}
        kex, sig, ckey = pq.classify(tls.key_exchange), pq.classify(tls.cert_signature_algo), pq.classify(tls.cert_key_algo)
        pq_kex = kex.quantum_status in pq.PQ_SAFE_STATUSES
        pq_sig = sig.quantum_status in pq.PQ_SAFE_STATUSES or sig.quantum_status == pq.CANDIDATE
        hybrid = kex.quantum_status == pq.HYBRID
        if pq_kex and pq_sig and ckey.quantum_status != pq.VULNERABLE:
            readiness, reason = "PQ-ready", "key establishment and signatures use NIST PQC (or hybrid) algorithms"
        elif pq_kex or pq_sig:
            readiness, reason = "Partially PQ", (
                "confidentiality is PQ-protected but authentication is classical" if pq_kex
                else "signatures are PQ but key exchange is classical (traffic can be harvested now)"
            )
        else:
            readiness, reason = "Quantum-vulnerable", "public-key cryptography is classical"
        lifetime = tls.data_lifetime_years or 0
        advisories = []
        if pq.classify(tls.symmetric_cipher).key == "aes128":
            advisories.append("AES-128 remains NIST-approved; consider AES-256 for long-lived clinical data (CNSA 2.0).")
        if pq.classify(tls.tls_version).key == "tls12" and not pq_kex:
            advisories.append("Standardised hybrid ML-KEM groups target TLS 1.3; plan the TLS 1.3 upgrade first.")
        if hybrid:
            advisories.append("Hybrid key exchange in use: retain until pure ML-KEM is mandated by policy.")
        if sig.quantum_status == pq.CANDIDATE:
            advisories.append(f"{tls.cert_signature_algo} is selected by NIST but its standard is not yet final.")
        return {
            "readiness": readiness,
            "readiness_reason": reason,
            "pq_detected": pq_kex or pq_sig,
            "pq_key_exchange": pq_kex,
            "pq_signature": pq_sig,
            "hybrid": hybrid,
            "hndl_exposed": bool(not pq_kex and lifetime),
            "protect_until_year": date.today().year + int(lifetime) if lifetime else None,
            "mosca": mosca,
            "has_classical_pkc": has_classical,
            "advisories": advisories,
            "transition_reference": "NIST IR 8547 ipd proposes deprecating quantum-vulnerable algorithms after 2030 and disallowing them after 2035.",
        }
