# Traceable mapping: findings → TIPPSS pillars → deductions → references (Release 3)

Reviewer 2 asked for a traceable mapping from finding types to pillar deductions and to IEEE/UL 2933-2024
requirements, and for a statement that pillar scores do not imply standards compliance.

**Standard.** IEEE/UL 2933-2024 — Standard for Clinical Internet of Things (IoT) Data and Device Interoperability with TIPPSS (Trust, Identity, Privacy, Protection, Safety, Security).

**Scope of the mapping.** Mapping is at pillar level. Clause numbers of IEEE/UL 2933-2024 are not public and must be taken from the licensed text. Pillar scores do not imply conformance with the standard or any certification.

**How a finding changes the scores.** Each finding deducts `d(severity)` points from every pillar it maps to
(`{'critical': 25, 'high': 15, 'medium': 8, 'low': 3, 'info': 0}`; floor 0). Findings that belong to a PQ-risk category feed the PQ risk score
`S = round(Σ_c w_c · v_c)` with weights `{'pkc': 0.3, 'tls': 0.2, 'lifetime': 0.2, 'identity': 0.15, 'secrets': 0.1, 'migration': 0.05}`, where `v_c` is the highest severity value
(critical 100, high 75, medium 50, low 25) among the findings in category `c`; the `migration` category is 75 when
no PQ algorithm is detected and 0 otherwise. Findings without a score category (PHI, prompt injection, clinical safety,
traffic) affect the pillar scores and the SAFE / AT_RISK / UNSAFE status but not `S`.

The table is generated from `backend/src/safeguard_pq/knowledge/standards_map.py` by
`scripts/gen_standards_map_doc.py`; the same data is served at `GET /api/v1/standards-map` and shown in the web
application's Research Results tab.

## Pillar coverage

| Pillar | Finding types | Agents feeding the pillar |
|---|---|---|
| Trust | 21 | clinical_privacy, prompt_injection, safety_risk, traffic_anomaly |
| Identity | 5 | crypto_inventory, device_identity, traffic_anomaly |
| Privacy | 7 | clinical_privacy, pq_identification |
| Protection | 23 | clinical_privacy, crypto_inventory, pq_identification, prompt_injection, secret_exposure, traffic_anomaly |
| Safety | 16 | device_identity, prompt_injection, safety_risk, traffic_anomaly |
| Security | 30 | crypto_inventory, device_identity, pq_identification, prompt_injection, secret_exposure, traffic_anomaly |

## Mapping table

| Finding type | Agent | Severity | TIPPSS pillars (IEEE/UL 2933-2024) | Pillar deduction | Score category (weight) | Public reference(s) | Technique |
|---|---|---|---|---|---|---|---|
| `deprecated_tls_version` | crypto_inventory | critical | Security, Protection | −25 | tls (0.20) | IETF RFC 8996 (2021): Deprecating TLS 1.0 and TLS 1.1; NIST SP 800-52 Rev. 2 (2019): Guidelines for the Selection, Configuration, and Use of TLS Implementations; MITRE CWE-327: Use of a Broken or Risky Cryptographic Algorithm | ATT&CK T1557 (adversary-in-the-middle) precondition |
| `classical_key_exchange` | crypto_inventory | high | Security, Protection | −15 | pkc (0.30) | NIST FIPS 203 (2024): Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM); NIST IR 8547 (final, Oct 2026): Transition to Post-Quantum Cryptography Standards; MITRE CWE-327: Use of a Broken or Risky Cryptographic Algorithm | ATT&CK T1040 (network sniffing) + future CRQC |
| `classical_signature` | crypto_inventory | high | Security, Identity, Protection | −15 | pkc (0.30) | NIST FIPS 204 (2024): Module-Lattice-Based Digital Signature Standard (ML-DSA); NIST IR 8547 (final, Oct 2026): Transition to Post-Quantum Cryptography Standards; MITRE CWE-327: Use of a Broken or Risky Cryptographic Algorithm | ATT&CK T1556 (modify authentication process) via forged identity |
| `classical_certificate_key` | crypto_inventory | high | Security, Identity, Protection | −15 | pkc (0.30) | NIST FIPS 204 (2024): Module-Lattice-Based Digital Signature Standard (ML-DSA); NIST IR 8547 (final, Oct 2026): Transition to Post-Quantum Cryptography Standards; MITRE CWE-327: Use of a Broken or Risky Cryptographic Algorithm | — |
| `weak_hash` | crypto_inventory | critical | Security, Protection | −25 | pkc (0.30) | NIST SP 800-131A Rev. 2 (2019): Transitioning the Use of Cryptographic Algorithms and Key Lengths; MITRE CWE-328: Use of Weak Hash | — |
| `weak_symmetric_cipher` | crypto_inventory | high | Security, Protection | −15 | pkc (0.30) | NIST SP 800-131A Rev. 2 (2019): Transitioning the Use of Cryptographic Algorithms and Key Lengths; MITRE CWE-327: Use of a Broken or Risky Cryptographic Algorithm | — |
| `pq_migration_required` | pq_identification | high | Security, Protection | −15 | pkc (0.30) | NIST FIPS 203 (2024): Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM); NIST FIPS 204 (2024): Module-Lattice-Based Digital Signature Standard (ML-DSA); NIST IR 8547 (final, Oct 2026): Transition to Post-Quantum Cryptography Standards | — |
| `long_lifetime_classical_crypto` | pq_identification | critical | Privacy, Protection, Security | −25 | lifetime (0.20) | Mosca (2018): IEEE Security & Privacy 16(5): x + y > z (data lifetime + migration time > time to CRQC); NIST IR 8547 (final, Oct 2026): Transition to Post-Quantum Cryptography Standards; HIPAA Security Rule, 45 CFR 164.312: technical safeguards: access control, integrity, person or entity authentication, transmission security | ATT&CK T1040 (network sniffing) |
| `mosca_hndl_exposure` | pq_identification | medium | Privacy, Protection | −8 | lifetime (0.20) | Mosca (2018): IEEE Security & Privacy 16(5): x + y > z (data lifetime + migration time > time to CRQC) | ATT&CK T1040 (network sniffing) |
| `medical_record_number` | clinical_privacy | high | Privacy, Protection, Trust | −15 | — | HIPAA Privacy Rule, 45 CFR 164.514(b)(2): the 18 identifiers of protected health information; OWASP Top 10 for LLM Applications: LLM06 Sensitive Information Disclosure | — |
| `ssn` | clinical_privacy | high | Privacy, Protection, Trust | −15 | — | HIPAA Privacy Rule, 45 CFR 164.514(b)(2): the 18 identifiers of protected health information; OWASP Top 10 for LLM Applications: LLM06 Sensitive Information Disclosure | — |
| `patient_identifier` | clinical_privacy | high | Privacy, Protection, Trust | −15 | — | HIPAA Privacy Rule, 45 CFR 164.514(b)(2): the 18 identifiers of protected health information; OWASP Top 10 for LLM Applications: LLM06 Sensitive Information Disclosure | — |
| `email` | clinical_privacy | high | Privacy, Protection, Trust | −15 | — | HIPAA Privacy Rule, 45 CFR 164.514(b)(2): the 18 identifiers of protected health information; OWASP Top 10 for LLM Applications: LLM06 Sensitive Information Disclosure | — |
| `sensitive_diagnosis` | clinical_privacy | critical | Privacy, Protection, Trust | −25 | — | HIPAA Privacy Rule, 45 CFR 164.514(b)(2): the 18 identifiers of protected health information; OWASP Top 10 for LLM Applications: LLM06 Sensitive Information Disclosure | — |
| `instruction_override` | prompt_injection | critical | Safety, Security, Trust | −25 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection | OWASP LLM01 |
| `role_manipulation` | prompt_injection | critical | Safety, Security, Trust | −25 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection | OWASP LLM01 |
| `system_prompt_extraction` | prompt_injection | high | Safety, Security, Trust | −15 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection | OWASP LLM01 |
| `fake_system_message` | prompt_injection | critical | Safety, Security, Trust | −25 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection | OWASP LLM01 |
| `fake_authorization` | prompt_injection | critical | Safety, Security, Trust | −25 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection; HIPAA Security Rule, 45 CFR 164.312: technical safeguards: access control, integrity, person or entity authentication, transmission security | OWASP LLM01 |
| `pq_downgrade_instruction` | prompt_injection | critical | Security, Protection, Trust | −25 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection; OWASP Top 10 for LLM Applications: LLM08 Excessive Agency; NIST IR 8547 (final, Oct 2026): Transition to Post-Quantum Cryptography Standards | OWASP LLM01 + LLM08 |
| `delimiter_injection` | prompt_injection | high | Safety, Security, Trust | −15 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection | OWASP LLM01 |
| `tool_hijack` | prompt_injection | high | Safety, Security, Trust | −15 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection; OWASP Top 10 for LLM Applications: LLM08 Excessive Agency | OWASP LLM08 |
| `encoded_payload` | prompt_injection | medium | Safety, Security, Trust | −8 | — | OWASP Top 10 for LLM Applications: LLM01 Prompt Injection | OWASP LLM01 |
| `stripe_live_key` | secret_exposure | critical | Protection, Security | −25 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File; MITRE CWE-798: Use of Hard-coded Credentials | ATT&CK T1552.001 |
| `aws_access_key` | secret_exposure | critical | Protection, Security | −25 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File; MITRE CWE-798: Use of Hard-coded Credentials | ATT&CK T1552.001 |
| `google_api_key` | secret_exposure | critical | Protection, Security | −25 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File; MITRE CWE-798: Use of Hard-coded Credentials | ATT&CK T1552.001 |
| `bearer_token` | secret_exposure | high | Protection, Security | −15 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File | ATT&CK T1552.001 |
| `private_key` | secret_exposure | critical | Protection, Security | −25 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File; MITRE CWE-798: Use of Hard-coded Credentials | ATT&CK T1552.004 |
| `github_token` | secret_exposure | critical | Protection, Security | −25 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File; MITRE CWE-798: Use of Hard-coded Credentials | ATT&CK T1552.001 |
| `slack_token` | secret_exposure | high | Protection, Security | −15 | secrets (0.10) | MITRE CWE-532: Insertion of Sensitive Information into Log File | ATT&CK T1552.001 |
| `autonomous_dosing` | safety_risk | critical | Safety, Trust | −25 | — | FDA guidance (2023): Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions; OWASP Top 10 for LLM Applications: LLM08 Excessive Agency | OWASP LLM08 |
| `autonomous_discharge` | safety_risk | critical | Safety, Trust | −25 | — | FDA guidance (2023): Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions; OWASP Top 10 for LLM Applications: LLM08 Excessive Agency | OWASP LLM08 |
| `clinician_bypass` | safety_risk | critical | Safety, Trust | −25 | — | FDA guidance (2023): Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions; OWASP Top 10 for LLM Applications: LLM08 Excessive Agency | OWASP LLM08 |
| `alarm_override` | safety_risk | critical | Safety, Trust | −25 | — | FDA guidance (2023): Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions; OWASP Top 10 for LLM Applications: LLM08 Excessive Agency | OWASP LLM08 |
| `unauthorized_disclosure` | safety_risk | critical | Safety, Trust | −25 | — | HIPAA Security Rule, 45 CFR 164.312: technical safeguards: access control, integrity, person or entity authentication, transmission security; OWASP Top 10 for LLM Applications: LLM06 Sensitive Information Disclosure | OWASP LLM06 |
| `missing_certificate` | device_identity | high | Identity, Security | −15 | identity (0.15) | HIPAA Security Rule, 45 CFR 164.312: technical safeguards: access control, integrity, person or entity authentication, transmission security; MITRE CWE-295: Improper Certificate Validation | — |
| `authentication_failed` | device_identity | critical | Identity, Safety | −25 | identity (0.15) | HIPAA Security Rule, 45 CFR 164.312: technical safeguards: access control, integrity, person or entity authentication, transmission security; MITRE CWE-287: Improper Authentication | ATT&CK T1078 (valid accounts) / forged identity |
| `volumetric_flood_pattern` | traffic_anomaly | critical | Safety, Security | −25 | — | Dadkhah et al. (2024): CICIoMT2024: attack vectors in healthcare devices — a multi-protocol dataset (Internet of Things, vol. 28) | ATT&CK T1498 (network denial of service) |
| `syn_flood_pattern` | traffic_anomaly | critical | Safety, Security | −25 | — | Dadkhah et al. (2024): CICIoMT2024: attack vectors in healthcare devices — a multi-protocol dataset (Internet of Things, vol. 28) | ATT&CK T1499 (endpoint denial of service) |
| `port_scan_pattern` | traffic_anomaly | high | Security, Trust | −15 | — | Dadkhah et al. (2024): CICIoMT2024: attack vectors in healthcare devices — a multi-protocol dataset (Internet of Things, vol. 28) | ATT&CK T1046 (network service discovery) |
| `protocol_flag_anomaly` | traffic_anomaly | medium | Security, Protection | −8 | — | Dadkhah et al. (2024): CICIoMT2024: attack vectors in healthcare devices — a multi-protocol dataset (Internet of Things, vol. 28) | — |
| `protocol_mix_anomaly` | traffic_anomaly | high | Identity, Trust, Security | −15 | — | Dadkhah et al. (2024): CICIoMT2024: attack vectors in healthcare devices — a multi-protocol dataset (Internet of Things, vol. 28) | ATT&CK T1557.002 (ARP cache poisoning) |
