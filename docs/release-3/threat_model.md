# Threat model (Release 3)

This section answers the reviewers' request for an explicit threat model: who the adversary is, what is protected,
what the framework can observe, and what is out of scope. It is written so that it can be pasted into Section V of the
paper with minimal editing.

## Assets

| Asset | Why it matters in a clinical IoT environment | Pillars most affected |
|---|---|---|
| Confidentiality of long-lived clinical data in transit | Patient records and physiological data must stay confidential for years (often ≥ 10 y); traffic recorded today can be decrypted once a cryptographically relevant quantum computer (CRQC) exists | Privacy, Protection, Security |
| Device identity and authenticity | Forged or missing device certificates allow impersonation of pumps, monitors and gateways | Identity, Trust |
| Patient safety of actuating devices | Infusion pumps, ventilators and alarm systems act on commands; unsafe autonomous AI actions or silenced alarms harm patients | Safety |
| Availability of monitoring and gateway services | Floods and scans degrade or interrupt telemetry | Safety, Security |
| Credentials and secrets held by devices | Leaked keys give an attacker cloud and service access | Protection, Security |

## Adversaries and capabilities

| Id | Adversary | Capability assumed | Simulated attack(s) | Precondition the framework checks |
|---|---|---|---|---|
| A1 | Passive network recorder with future CRQC access | Records ciphertext now; runs Shor's algorithm later | `hndl_capture` | classical key exchange and data lifetime ≥ L years, or Mosca x + y > z |
| A2 | Active on-path adversary | Forces weakest accepted suite or drops the PQ key share; relays traffic (ARP spoofing) | `tls_downgrade`, `pq_strip`, `arp_spoofing` | legacy TLS versions accepted; classical-only groups accepted; MITM-like flow mix |
| A3 | CRQC-equipped impersonator | Derives private keys of classical (ECDSA/RSA) certificates | `cert_spoof` | classical certificate signature or key algorithm |
| A4 | Prompt-channel adversary | Injects instructions into the clinical AI assistant's prompt channel | `prompt_injection`, `pq_downgrade_prompt`, `unsafe_command`, `phi_leak` | injection / unsafe-action / PHI patterns in prompt logs |
| A5 | Log reader | Reads device debug output or logs | `secret_leak` | credential-shaped strings in device logs |
| A6 | Network flooder / scanner | Generates floods and probes from inside the clinical VLAN | `syn_flood`, `ddos_volumetric`, `port_scan`, `mqtt_malformed` | flow-feature rule patterns over 100-row windows |

Adversaries are assumed to be rational and to know the framework's rules (Kerckhoffs's principle); the rules are
transparent heuristics and an adversary can shape traffic to evade the window-level thresholds (see
[limitations](../limitations.md)).

## What the framework observes

The framework evaluates **supplied snapshots**: a TLS configuration, a 100-row flow-feature window, AI prompt logs and
device log records, plus the operator's constraints (budget, downtime) and assumptions (years to CRQC, migration time,
lifetime threshold `L`). It does not connect to devices, scan networks, inspect firmware or read patient records. Every
finding is therefore a **precondition** for an attack, observable in the configuration or telemetry, not an observed
attack.

## In scope

- Post-quantum exposure of public-key cryptography in the configured TLS stack (key exchange, certificate signature,
  certificate key), deprecated protocol versions, weak hashes and ciphers.
- Harvest-now-decrypt-later exposure as a function of data lifetime and explicit Q-Day assumptions.
- Device identity preconditions visible in device logs (certificate present, authentication outcome).
- Prompt-channel risks to clinical AI assistants: instruction override, PQ-downgrade instructions, tool hijacking,
  PHI leakage, unsafe autonomous clinical actions.
- Secrets written to device logs.
- Flow-level anomalies that resemble DoS/DDoS, reconnaissance, malformed MQTT and MITM relays.
- Constraint-aware remediation planning and its evaluation by **reassessment** of the remediated configuration.

## Out of scope

- Firmware or memory-safety exploitation, physical access, side channels, supply-chain compromise.
- Cryptanalysis: the framework classifies algorithms against NIST FIPS 203/204/205 and NIST IR 8547; it does not
  attack them.
- Live discovery and scanning (configurations are supplied as input).
- Insider misuse that leaves no trace in the supplied logs.
- Real-world efficacy of a mitigation: a **reassessment** verifies that the remediated configuration satisfies the
  framework's own rules; it is not evidence that an attacker is stopped. Network mitigations (rate limiting,
  segmentation) are *not* modelled at configuration level and are reported as unmodelled.
- Clinical safety or conformance with IEEE/UL 2933-2024: pillar scores are the framework's own design, not a
  certification.

## Trust assumptions

- Supplied inputs are truthful snapshots of the system under test.
- The assessment host and the rule tables are trusted; the optional LLM narrative receives redacted facts only and
  cannot change a verdict, a score or a plan.
- Costs, downtimes and complexities in the remediation catalogue are illustrative placeholders, not measured effort.

## Attack → detector → mitigation table (simulator catalogue)

| Attack | Layer | Surface | Detected by (agents) | Blocked by (mitigations) |
|---|---|---|---|---|
| Harvest-now, decrypt-later capture | quantum | network link (passive recording) | pq_identification | enable_hybrid_mlkem |
| Legacy-fallback downgrade | quantum | TLS handshake | crypto_inventory, pq_identification | pq_policy_pinning |
| Classical-only group fallback | quantum | TLS key exchange | crypto_inventory, pq_identification | pq_policy_pinning |
| Quantum certificate forgery (CRQC) | quantum | device certificate key | device_identity, crypto_inventory | pq_certificates |
| SYN flood (DoS) | network | TCP | traffic_anomaly | rate_limiting |
| Volumetric TCP flood (DDoS) | network | TCP | traffic_anomaly | rate_limiting |
| Reconnaissance port scan | network | services | traffic_anomaly | network_segmentation |
| Malformed MQTT | network | MQTT | traffic_anomaly | network_segmentation |
| ARP spoofing / MITM relay | network | L2 | traffic_anomaly | network_segmentation |
| Prompt injection | ai | AI assistant | prompt_injection | prompt_firewall |
| PQ-downgrade prompt injection | ai | AI assistant | prompt_injection | prompt_firewall |
| PHI leakage into prompts | ai | AI assistant | clinical_privacy | phi_redaction |
| Unsafe autonomous clinical command | ai | AI assistant | safety_risk | clinician_approval_gate |
| Credential leak in device log | identity | debug logs | secret_exposure | secret_rotation |

Source: `backend/src/safeguard_pq/simulation/catalog.py`. The outcome of each attack against each device of the
hospital-ward template is measured in experiment E11 (`benchmarks/attack_simulation_eval.py`).
