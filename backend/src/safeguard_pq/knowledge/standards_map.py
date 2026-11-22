"""Traceable mapping: finding type → TIPPSS pillar(s) → pillar deduction / score category → public references.

A table that shows, for every finding the agents can raise, which of the six IEEE/UL
2933-2024 principles (called pillars in the code) it affects, how many pillar points it
deducts, which PQ-risk category (and weight) it feeds, and which public standard or
guidance supports the rule.

Honesty notes
-------------
* IEEE/UL 2933-2024 ("Standard for Clinical Internet of Things (IoT) Data and Device
  Interoperability with TIPPSS", published 2024-09-30) defines the six pillars Trust,
  Identity, Privacy, Protection, Safety and Security.  Its clause numbering is not
  publicly available, so this table maps findings to *pillars*, never to clause
  numbers.  ``tippss_2933_clause`` is therefore ``None`` everywhere and must be filled
  from the licensed text by whoever cites the standard.
* The pillar deductions and the score weights are the framework's own design choices
  (see ``agents/scoring.py``); the references explain *why* a finding is a risk, they
  do not mean the standard prescribes these numbers.
* Pillar scores do not imply conformance with IEEE/UL 2933-2024 or any certification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..agents.scoring import PILLAR_DEDUCT, WEIGHTS
from ..domain.models import PILLARS

STANDARD_TITLE = (
    "IEEE/UL 2933-2024 — Standard for Clinical Internet of Things (IoT) Data and Device Interoperability "
    "with TIPPSS (Trust, Identity, Privacy, Protection, Safety, Security)"
)
STANDARD_NOTE = (
    "Mapping is at pillar level. Clause numbers of IEEE/UL 2933-2024 are not public and must be taken from the "
    "licensed text. Pillar scores do not imply conformance with the standard or any certification."
)


@dataclass(frozen=True)
class Reference:
    standard: str
    ref: str
    note: str = ""


@dataclass(frozen=True)
class MappingRow:
    finding_type: str
    agent: str
    severity: str
    pillars: tuple[str, ...]
    score_category: str | None
    rationale: str
    references: tuple[Reference, ...] = field(default_factory=tuple)
    attack_technique: str | None = None  # MITRE ATT&CK or OWASP LLM identifier where one exists

    @property
    def pillar_deduction(self) -> int:
        return PILLAR_DEDUCT.get(self.severity, 5)

    @property
    def score_weight(self) -> float | None:
        return WEIGHTS.get(self.score_category) if self.score_category else None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pillars"] = list(self.pillars)
        d["references"] = [asdict(r) for r in self.references]
        d["pillar_deduction"] = self.pillar_deduction
        d["score_category"] = self.score_category
        d["score_weight"] = self.score_weight
        d["tippss_2933_pillars"] = list(self.pillars)
        d["tippss_2933_clause"] = None
        return d


# Public references reused across rows
FIPS203 = Reference("NIST FIPS 203 (2024)", "Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM)")
FIPS204 = Reference("NIST FIPS 204 (2024)", "Module-Lattice-Based Digital Signature Standard (ML-DSA)")
IR8547 = Reference("NIST IR 8547 (final, Oct 2026)", "Transition to Post-Quantum Cryptography Standards",
                   "quantum-vulnerable public-key algorithms to be deprecated and then disallowed; see the report")
MOSCA = Reference("Mosca (2018)", "IEEE Security & Privacy 16(5): x + y > z (data lifetime + migration time > time to CRQC)")
RFC8996 = Reference("IETF RFC 8996 (2021)", "Deprecating TLS 1.0 and TLS 1.1")
SP80052 = Reference("NIST SP 800-52 Rev. 2 (2019)", "Guidelines for the Selection, Configuration, and Use of TLS Implementations")
SP800131 = Reference("NIST SP 800-131A Rev. 2 (2019)", "Transitioning the Use of Cryptographic Algorithms and Key Lengths",
                     "SHA-1 disallowed for digital signature generation; 3DES deprecated")
CWE327 = Reference("MITRE CWE-327", "Use of a Broken or Risky Cryptographic Algorithm")
CWE328 = Reference("MITRE CWE-328", "Use of Weak Hash")
CWE295 = Reference("MITRE CWE-295", "Improper Certificate Validation")
CWE287 = Reference("MITRE CWE-287", "Improper Authentication")
CWE532 = Reference("MITRE CWE-532", "Insertion of Sensitive Information into Log File")
CWE798 = Reference("MITRE CWE-798", "Use of Hard-coded Credentials")
HIPAA_ID = Reference("HIPAA Privacy Rule, 45 CFR 164.514(b)(2)", "the 18 identifiers of protected health information")
HIPAA_TS = Reference("HIPAA Security Rule, 45 CFR 164.312", "technical safeguards: access control, integrity, "
                     "person or entity authentication, transmission security")
OWASP_LLM01 = Reference("OWASP Top 10 for LLM Applications", "LLM01 Prompt Injection")
OWASP_LLM06 = Reference("OWASP Top 10 for LLM Applications", "LLM06 Sensitive Information Disclosure")
OWASP_LLM08 = Reference("OWASP Top 10 for LLM Applications", "LLM08 Excessive Agency")
FDA_CYBER = Reference("FDA guidance (2023)", "Cybersecurity in Medical Devices: Quality System Considerations and Content "
                      "of Premarket Submissions")
CIC = Reference("Dadkhah et al. (2024)", "CICIoMT2024: attack vectors in healthcare devices — a multi-protocol dataset "
                "(Internet of Things, vol. 28)", "heuristic rule thresholds were calibrated on this dataset")

_CRYPTO = ("Security", "Protection")
_SIG = ("Security", "Identity", "Protection")


def _rows() -> list[MappingRow]:
    phi = ("Privacy", "Protection", "Trust")
    inj = ("Safety", "Security", "Trust")
    pq_inj = ("Security", "Protection", "Trust")
    sec = ("Protection", "Security")
    unsafe = ("Safety", "Trust")
    return [
        # --- cryptographic inventory (tls_config)
        MappingRow("deprecated_tls_version", "crypto_inventory", "critical", _CRYPTO, "tls",
                   "TLS 1.0/1.1 (RFC 8996) or SSL is negotiable: downgrade and known protocol attacks",
                   (RFC8996, SP80052, CWE327), "ATT&CK T1557 (adversary-in-the-middle) precondition"),
        MappingRow("classical_key_exchange", "crypto_inventory", "high", _CRYPTO, "pkc",
                   "ECDHE/RSA/DH key establishment is breakable by Shor's algorithm on a CRQC; sessions recorded "
                   "today become readable", (FIPS203, IR8547, CWE327), "ATT&CK T1040 (network sniffing) + future CRQC"),
        MappingRow("classical_signature", "crypto_inventory", "high", _SIG, "pkc",
                   "ECDSA/RSA certificate signatures can be forged once a CRQC exists (device impersonation)",
                   (FIPS204, IR8547, CWE327), "ATT&CK T1556 (modify authentication process) via forged identity"),
        MappingRow("classical_certificate_key", "crypto_inventory", "high", _SIG, "pkc",
                   "Classical certificate key pair; same exposure as a classical signature",
                   (FIPS204, IR8547, CWE327)),
        MappingRow("weak_hash", "crypto_inventory", "critical", _CRYPTO, "pkc",
                   "MD5/SHA-1 are collision-vulnerable today (no quantum computer needed)",
                   (SP800131, CWE328)),
        MappingRow("weak_symmetric_cipher", "crypto_inventory", "high", _CRYPTO, "pkc",
                   "DES/3DES/RC4 deprecated; Grover's algorithm also halves effective symmetric key length",
                   (SP800131, CWE327)),
        # --- post-quantum identification
        MappingRow("pq_migration_required", "pq_identification", "high", _CRYPTO, "pkc",
                   "At least one quantum-vulnerable public-key primitive has no PQC replacement in place",
                   (FIPS203, FIPS204, IR8547)),
        MappingRow("long_lifetime_classical_crypto", "pq_identification", "critical", ("Privacy", "Protection", "Security"),
                   "lifetime", "Data lifetime ≥ threshold (default 10 y) with classical key exchange: harvest-now-"
                   "decrypt-later exposure", (MOSCA, IR8547, HIPAA_TS), "ATT&CK T1040 (network sniffing)"),
        MappingRow("mosca_hndl_exposure", "pq_identification", "medium", ("Privacy", "Protection"), "lifetime",
                   "Mosca's inequality x + y > z holds under the user's assumptions although the lifetime is below "
                   "the threshold", (MOSCA,), "ATT&CK T1040 (network sniffing)"),
        # --- protected health information in AI prompts
        MappingRow("medical_record_number", "clinical_privacy", "high", phi, None,
                   "Medical record number in a prompt or log reaching an AI service", (HIPAA_ID, OWASP_LLM06)),
        MappingRow("ssn", "clinical_privacy", "high", phi, None, "US social security number in a prompt",
                   (HIPAA_ID, OWASP_LLM06)),
        MappingRow("patient_identifier", "clinical_privacy", "high", phi, None, "Patient name / id label in a prompt",
                   (HIPAA_ID, OWASP_LLM06)),
        MappingRow("email", "clinical_privacy", "high", phi, None, "E-mail address (HIPAA identifier) in a prompt",
                   (HIPAA_ID, OWASP_LLM06)),
        MappingRow("sensitive_diagnosis", "clinical_privacy", "critical", phi, None,
                   "Sensitive diagnosis category disclosed to an AI service", (HIPAA_ID, OWASP_LLM06)),
        # --- prompt injection against clinical AI agents
        MappingRow("instruction_override", "prompt_injection", "critical", inj, None,
                   "Instruction override of the clinical assistant", (OWASP_LLM01,), "OWASP LLM01"),
        MappingRow("role_manipulation", "prompt_injection", "critical", inj, None,
                   "Role / jailbreak mode switching", (OWASP_LLM01,), "OWASP LLM01"),
        MappingRow("system_prompt_extraction", "prompt_injection", "high", inj, None,
                   "System prompt extraction attempt", (OWASP_LLM01,), "OWASP LLM01"),
        MappingRow("fake_system_message", "prompt_injection", "critical", inj, None,
                   "Fabricated system/admin message in user content", (OWASP_LLM01,), "OWASP LLM01"),
        MappingRow("fake_authorization", "prompt_injection", "critical", inj, None,
                   "Fabricated authorization / consent claim", (OWASP_LLM01, HIPAA_TS), "OWASP LLM01"),
        MappingRow("pq_downgrade_instruction", "prompt_injection", "critical", pq_inj, None,
                   "Instruction that makes an AI agent weaken post-quantum protection (crypto downgrade via agent)",
                   (OWASP_LLM01, OWASP_LLM08, IR8547), "OWASP LLM01 + LLM08"),
        MappingRow("delimiter_injection", "prompt_injection", "high", inj, None,
                   "Chat-template delimiter injection", (OWASP_LLM01,), "OWASP LLM01"),
        MappingRow("tool_hijack", "prompt_injection", "high", inj, None,
                   "Attempt to drive agent tool calls", (OWASP_LLM01, OWASP_LLM08), "OWASP LLM08"),
        MappingRow("encoded_payload", "prompt_injection", "medium", inj, None,
                   "Encoded payload smuggling", (OWASP_LLM01,), "OWASP LLM01"),
        # --- secrets in device logs
        MappingRow("stripe_live_key", "secret_exposure", "critical", sec, "secrets",
                   "Live payment secret written to a device log", (CWE532, CWE798), "ATT&CK T1552.001"),
        MappingRow("aws_access_key", "secret_exposure", "critical", sec, "secrets",
                   "Cloud access key id in a device log", (CWE532, CWE798), "ATT&CK T1552.001"),
        MappingRow("google_api_key", "secret_exposure", "critical", sec, "secrets",
                   "API key in a device log", (CWE532, CWE798), "ATT&CK T1552.001"),
        MappingRow("bearer_token", "secret_exposure", "high", sec, "secrets",
                   "Bearer token in a device log", (CWE532,), "ATT&CK T1552.001"),
        MappingRow("private_key", "secret_exposure", "critical", sec, "secrets",
                   "PEM private key in a device log", (CWE532, CWE798), "ATT&CK T1552.004"),
        MappingRow("github_token", "secret_exposure", "critical", sec, "secrets",
                   "Source-control token in a device log", (CWE532, CWE798), "ATT&CK T1552.001"),
        MappingRow("slack_token", "secret_exposure", "high", sec, "secrets",
                   "Collaboration-platform token in a device log", (CWE532,), "ATT&CK T1552.001"),
        # --- unsafe autonomous clinical actions
        MappingRow("autonomous_dosing", "safety_risk", "critical", unsafe, None,
                   "AI-driven medication dosing without clinician approval", (FDA_CYBER, OWASP_LLM08), "OWASP LLM08"),
        MappingRow("autonomous_discharge", "safety_risk", "critical", unsafe, None,
                   "Autonomous discharge decision", (FDA_CYBER, OWASP_LLM08), "OWASP LLM08"),
        MappingRow("clinician_bypass", "safety_risk", "critical", unsafe, None,
                   "Clinician sign-off bypass", (FDA_CYBER, OWASP_LLM08), "OWASP LLM08"),
        MappingRow("alarm_override", "safety_risk", "critical", unsafe, None,
                   "Clinical alarm override / silencing", (FDA_CYBER, OWASP_LLM08), "OWASP LLM08"),
        MappingRow("unauthorized_disclosure", "safety_risk", "critical", unsafe, None,
                   "Unauthorised disclosure workflow requested of the AI", (HIPAA_TS, OWASP_LLM06), "OWASP LLM06"),
        # --- device identity
        MappingRow("missing_certificate", "device_identity", "high", ("Identity", "Security"), "identity",
                   "Device presents no X.509 identity", (HIPAA_TS, CWE295)),
        MappingRow("authentication_failed", "device_identity", "critical", ("Identity", "Safety"), "identity",
                   "Device authentication failed (possible impersonation)", (HIPAA_TS, CWE287),
                   "ATT&CK T1078 (valid accounts) / forged identity"),
        # --- network traffic (heuristic rules calibrated on CICIoMT2024)
        MappingRow("volumetric_flood_pattern", "traffic_anomaly", "critical", ("Safety", "Security"), None,
                   "Handshake-less header-only TCP flood (DDoS-like) threatens device availability",
                   (CIC,), "ATT&CK T1498 (network denial of service)"),
        MappingRow("syn_flood_pattern", "traffic_anomaly", "critical", ("Safety", "Security"), None,
                   "SYN-dominated tiny packets (SYN flood / DoS-like)", (CIC,), "ATT&CK T1499 (endpoint denial of service)"),
        MappingRow("port_scan_pattern", "traffic_anomaly", "high", ("Security", "Trust"), None,
                   "SYN probes answered by RST (reconnaissance-like)", (CIC,), "ATT&CK T1046 (network service discovery)"),
        MappingRow("protocol_flag_anomaly", "traffic_anomaly", "medium", ("Security", "Protection"), None,
                   "Elevated control-flag share on TCP sessions (malformed MQTT-like)", (CIC,)),
        MappingRow("protocol_mix_anomaly", "traffic_anomaly", "high", ("Identity", "Trust", "Security"), None,
                   "UDP-heavy mid-size packets with low ACK share (MITM / ARP-spoofing-like; weak evidence)",
                   (CIC,), "ATT&CK T1557.002 (ARP cache poisoning)"),
    ]


STANDARDS_MAP: tuple[MappingRow, ...] = tuple(_rows())
BY_TYPE: dict[str, MappingRow] = {r.finding_type: r for r in STANDARDS_MAP}


def pillar_coverage() -> dict[str, dict[str, Any]]:
    """How many finding types touch each pillar and which agents feed it."""
    out: dict[str, dict[str, Any]] = {p: {"finding_types": 0, "agents": set()} for p in PILLARS}
    for r in STANDARDS_MAP:
        for p in r.pillars:
            out[p]["finding_types"] += 1
            out[p]["agents"].add(r.agent)
    return {p: {"finding_types": v["finding_types"], "agents": sorted(v["agents"])} for p, v in out.items()}


def standards_map() -> dict[str, Any]:
    return {
        "standard": STANDARD_TITLE,
        "note": STANDARD_NOTE,
        "pillar_deductions": dict(PILLAR_DEDUCT),
        "score_weights": dict(WEIGHTS),
        "rows": [r.as_dict() for r in STANDARDS_MAP],
        "pillar_coverage": pillar_coverage(),
    }


def markdown_table() -> str:
    """The same table as Markdown, used to generate the documentation."""
    lines = [
        "| Finding type | Agent | Severity | TIPPSS pillars (IEEE/UL 2933-2024) | Pillar deduction | Score category (weight) "
        "| Public reference(s) | Technique |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in STANDARDS_MAP:
        cat = f"{r.score_category} ({r.score_weight:.2f})" if r.score_category else "—"
        refs = "; ".join(f"{x.standard}: {x.ref}" for x in r.references)
        lines.append(f"| `{r.finding_type}` | {r.agent} | {r.severity} | {', '.join(r.pillars)} | −{r.pillar_deduction} "
                     f"| {cat} | {refs} | {r.attack_technique or '—'} |")
    return "\n".join(lines)
