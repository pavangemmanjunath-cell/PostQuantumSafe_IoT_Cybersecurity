"""Remediation action templates used by the QIRO optimizer.

IMPORTANT: cost (USD), downtime (hours), complexity (1-10) and base risk
reduction values are ILLUSTRATIVE PLACEHOLDERS chosen for the prototype. They
are not market prices or measured effort data and must be replaced with
organisation-specific estimates before any real planning use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ActionTemplate:
    cost: float
    downtime: float
    complexity: int
    base_risk_reduction: int
    remediation: str
    mitigation: str | None = None  # simulator mitigation id that implements this action


T = ActionTemplate

ACTION_TEMPLATES: dict[str, ActionTemplate] = {
    # --- cryptography / post-quantum (v0 values)
    "classical_key_exchange": T(25000, 6, 7, 30, "Migrate key exchange to hybrid X25519 + ML-KEM-768, then full ML-KEM.", "enable_hybrid_mlkem"),
    "classical_signature": T(20000, 4, 6, 30, "Replace classical ECDSA/RSA signatures with ML-DSA-based certificates.", "pq_certificates"),
    "deprecated_tls_version": T(30000, 8, 8, 35, "Upgrade deprecated TLS to TLS 1.3 with modern cipher suites.", "upgrade_tls13"),
    "weak_hash": T(22000, 5, 6, 30, "Replace weak hash usage with SHA-384/SHA-512 aligned algorithms.", "strong_hash"),
    "pq_migration_required": T(50000, 12, 9, 45, "Execute PQC migration for classical public-key cryptography.", "enable_hybrid_mlkem"),
    "long_lifetime_classical_crypto": T(45000, 10, 8, 40, "Prioritize long-lifetime clinical data channels for PQ-safe migration.", "enable_hybrid_mlkem"),
    # --- privacy (v0 values)
    "medical_record_number": T(8000, 1, 3, 25, "Add PHI redaction and MRN masking before AI prompt processing.", "phi_redaction"),
    "sensitive_diagnosis": T(12000, 2, 4, 35, "Add sensitive-diagnosis policy guardrails and privacy filters.", "phi_redaction"),
    "patient_identifier": T(8000, 1, 3, 22, "Mask patient names and identifiers in AI prompt logs.", "phi_redaction"),
    "email": T(6000, 1, 2, 20, "Mask email addresses and restrict external disclosure paths.", "phi_redaction"),
    "ssn": T(10000, 1, 3, 30, "Add SSN detection, redaction, and privacy policy enforcement.", "phi_redaction"),
    # --- identity (v0 values)
    "missing_certificate": T(15000, 4, 5, 25, "Issue and rotate device certificates for unauthenticated medical IoT assets.", "pq_certificates"),
    "authentication_failed": T(10000, 2, 4, 35, "Enforce device re-authentication, certificate validation, and access lockout.", "device_reauth"),
    # --- prompt injection (v0 values)
    "instruction_override": T(8000, 1, 3, 25, "Add prompt-injection firewall and system instruction isolation.", "prompt_firewall"),
    "role_manipulation": T(8000, 1, 3, 25, "Block role escalation and jailbreak mode switching attempts.", "prompt_firewall"),
    "system_prompt_extraction": T(6000, 1, 2, 18, "Prevent system prompt leakage using output filtering and policy checks.", "prompt_firewall"),
    "fake_system_message": T(8000, 1, 3, 25, "Detect fake system/admin messages in AI prompt context.", "prompt_firewall"),
    "fake_authorization": T(8000, 1, 3, 28, "Validate authorization claims before processing healthcare AI actions.", "prompt_firewall"),
    # --- secrets (v0 values)
    "stripe_live_key": T(5000, 1, 2, 30, "Rotate exposed live key and enable secret scanning.", "secret_rotation"),
    "aws_access_key": T(5000, 1, 2, 30, "Rotate exposed AWS key and enforce secrets management.", "secret_rotation"),
    "google_api_key": T(5000, 1, 2, 28, "Rotate exposed Google API key and restrict key scope.", "secret_rotation"),
    "bearer_token": T(4000, 1, 2, 22, "Rotate bearer token and remove token logging.", "secret_rotation"),
    "private_key": T(8000, 2, 3, 35, "Revoke exposed private key and reissue certificates.", "secret_rotation"),
    # --- clinical safety (v0 values)
    "autonomous_dosing": T(15000, 2, 5, 40, "Require clinician approval for medication dosing recommendations.", "clinician_approval_gate"),
    "autonomous_discharge": T(12000, 2, 4, 35, "Block autonomous discharge decisions without clinical review.", "clinician_approval_gate"),
    "clinician_bypass": T(12000, 2, 4, 35, "Enforce clinician sign-off workflow.", "clinician_approval_gate"),
    "alarm_override": T(15000, 3, 5, 40, "Prevent AI or user prompts from disabling clinical safety alarms.", "clinician_approval_gate"),
    "unauthorized_disclosure": T(15000, 2, 4, 38, "Block unauthorized patient data disclosure workflows.", "phi_redaction"),
    # --- added in 0.1.0
    "mosca_hndl_exposure": T(25000, 6, 7, 25, "Schedule hybrid ML-KEM migration before the assumed Q-Day for this data class.", "enable_hybrid_mlkem"),
    "weak_symmetric_cipher": T(15000, 3, 5, 25, "Replace 3DES/DES with AES-256-GCM.", "upgrade_tls13"),
    "classical_certificate_key": T(20000, 4, 6, 30, "Re-key device certificates with ML-DSA key pairs.", "pq_certificates"),
    "pq_downgrade_instruction": T(10000, 1, 3, 30, "Pin PQ-only crypto policy so AI agents cannot request downgrades; alert on attempts.", "prompt_firewall"),
    "delimiter_injection": T(6000, 1, 2, 18, "Escape chat-template delimiters in untrusted input.", "prompt_firewall"),
    "tool_hijack": T(8000, 1, 3, 25, "Require allow-listed, human-approved tool calls for clinical agents.", "prompt_firewall"),
    "encoded_payload": T(6000, 1, 2, 15, "Decode-and-inspect encoded content before it reaches the model.", "prompt_firewall"),
    "github_token": T(4000, 1, 2, 25, "Revoke exposed GitHub token and enable push protection.", "secret_rotation"),
    "slack_token": T(4000, 1, 2, 20, "Revoke exposed Slack token.", "secret_rotation"),
    "volumetric_flood_pattern": T(18000, 3, 5, 35, "Deploy upstream rate limiting / DDoS scrubbing and segment the clinical VLAN.", "rate_limiting"),
    "syn_flood_pattern": T(12000, 2, 4, 35, "Enable SYN cookies, connection rate limits and gateway hardening.", "rate_limiting"),
    "port_scan_pattern": T(8000, 1, 3, 20, "Close unused services and alert on reconnaissance.", "network_segmentation"),
    "protocol_flag_anomaly": T(10000, 2, 4, 22, "Validate MQTT/TCP framing at the broker and drop malformed sessions.", "network_segmentation"),
    "protocol_mix_anomaly": T(12000, 2, 4, 28, "Enable dynamic ARP inspection, mutual device authentication and segmentation.", "network_segmentation"),
}

GENERIC_TEMPLATE = T(10000, 2, 4, 20, "Apply generic remediation control.")


def template_for(finding_type: str) -> ActionTemplate:
    return ACTION_TEMPLATES.get(finding_type, GENERIC_TEMPLATE)


def catalog() -> dict[str, dict]:
    return {k: asdict(v) for k, v in ACTION_TEMPLATES.items()}
