# Clinical deployment feasibility (Release 3)

This appendix discusses legacy medical-device compatibility, computational overhead, memory needs, certificate
lifecycle management and operational downtime. **No device measurements were performed in this work.**
This section collects published, publicly verifiable figures and states what they imply for the remediation actions
the planner proposes. Every number below was read from the cited public page on 2026-11-22; derived values are
marked.

## 1. Object sizes: classical versus NIST PQC

| Primitive | Public / encapsulation key | Private key | Ciphertext or signature | Source |
|---|---|---|---|---|
| X25519 key share (TLS 1.3) | 32 B | 32 B | — | RFC 7748 |
| RSA-2048 | 256 B modulus (derived: 2048/8) | — | 256 B signature | RFC 8017 §2, §8.2.1 |
| ECDSA P-256 | 65 B uncompressed / 33 B compressed (derived) | 32 B | 64 B raw (RFC 7518 §3.4); 70–72 B DER (derived) | RFC 5480, RFC 7518 |
| ML-KEM-512 | 800 B | 1 632 B | 768 B ciphertext | OQS liboqs ML-KEM page (FIPS 203 parameter sets) |
| **ML-KEM-768** | **1 184 B** | 2 400 B | **1 088 B** ciphertext | same |
| ML-KEM-1024 | 1 568 B | 3 168 B | 1 568 B ciphertext | same |
| ML-DSA-44 | 1 312 B | 2 560 B | 2 420 B signature | OQS liboqs ML-DSA page (FIPS 204 parameter sets) |
| **ML-DSA-65** | **1 952 B** | 4 032 B | **3 309 B** signature | same |
| ML-DSA-87 | 2 592 B | 4 896 B | 4 627 B signature | same |

Implications for the planner's actions:

- *Hybrid ML-KEM key exchange* (`enable_hybrid_mlkem`, X25519MLKEM768): the key-share payload grows from 32 B to
  32 + 1 184 = 1 216 B in the ClientHello and from 32 B to 32 + 1 088 = 1 120 B in the ServerHello (derived). A
  ClientHello above the typical 1 500-byte MTU is split across TCP segments; middleboxes that assume a single-segment
  ClientHello are a known compatibility risk (this is exactly the "classical-only group fallback" the simulator models).
- *ML-DSA certificates* (`pq_certificates`): one ML-DSA-65 certificate carries 1 952 + 3 309 = 5 261 B of key and
  signature material versus about 65 + 72 = 137 B for ECDSA P-256 (derived). A three-certificate chain therefore adds
  roughly 15 kB to every full handshake, which matters for low-bandwidth wearables and for devices that cache
  certificates in small flash partitions.

## 2. Computational cost on a constrained microcontroller (pqm4, Cortex-M4)

Source: the pqm4 project benchmark tables (`benchmarks.md`; cycle counts at 24 MHz with Arm GNU Toolchain 11.3,
board NUCLEO-L4R5ZI; stack figures exclude key, ciphertext and signature buffers). The project announced in its README
that it is no longer actively maintained and will be archived in or after January 2027; the figures are nevertheless
the most widely cited public reference for this class of device.

| Operation | Cycles (m4f optimised) | ≈ ms at 24 MHz (derived) | Stack (m4f optimised) | Stack (m4fstack variant) |
|---|---|---|---|---|
| ML-KEM-768 keygen | 642 096 | 26.8 | 5 396 B | 2 820 B |
| ML-KEM-768 encaps | 658 754 | 27.4 | 6 468 B | 2 860 B |
| ML-KEM-768 decaps | 707 827 | 29.5 | 6 452 B | 2 844 B |
| ML-DSA-65 keygen | 2 516 006 | 104.8 | 60 824 B | 4 408 B |
| ML-DSA-65 sign (average; min–max) | 6 193 171 (2 918 295 – 26 008 621) | 258 (122 – 1 084) | 68 872 B | 6 616 B |
| ML-DSA-65 verify | 2 415 944 | 100.7 | 9 888 B | 2 712 B |

Implications:

- A TLS 1.3 client on a Cortex-M4-class wearable or sensor pays about 27 ms (encapsulation) per hybrid handshake for
  ML-KEM-768 and about 100 ms per ML-DSA-65 signature verification; with a three-certificate chain this is ≈ 0.3 s of
  CPU per full handshake at 24 MHz (derived). Session resumption keeps this cost off the critical path of periodic
  telemetry.
- ML-DSA-65 *signing* with the speed-optimised code needs about 69 kB of stack, more than the 64 kB closely coupled
  memory of some Cortex-M4 parts; the stack-optimised variant needs 6.6 kB at the price of roughly four times the
  cycles. Devices that only *verify* signatures (most sensors) need ≤ 10 kB.
- Devices below this class (8-bit controllers, legacy pumps with fixed firmware) cannot run ML-KEM/ML-DSA at all.

## 3. Legacy devices: the gateway pattern

Where a device cannot be re-flashed, the practical remediation is to terminate TLS at a PQ-capable gateway on the
clinical VLAN (the simulator's `GW-EDGE-01` role) and to isolate the legacy segment (`network_segmentation`). The
device-to-gateway hop then remains classical and must be treated as a physically protected link; the framework records
this as remaining exposure because the device's own configuration is unchanged (experiment E9 reports such systems
with a non-zero reassessed score).

## 4. Certificate lifecycle

Migrating to ML-DSA certificates (`pq_certificates`) requires a PQ-capable issuing CA, re-enrolment of every device
identity, trust-store updates on every peer, and a rollover period in which both classical and PQ chains are trusted.
NIST's PQC project page states that NIST "will deprecate and ultimately remove quantum-vulnerable algorithms from its
standards by 2035" (NIST IR 8547, final version published October 2026, supersedes the November 2024 draft). The
planner's phase plan (immediate 0–6 months, transitional 6–18 months, full PQ 18–36 months) is an illustrative
schedule within that window, not a measured one.

## 5. Operational downtime

The downtime figures in the remediation catalogue (1–12 h per action; see `backend/src/safeguard_pq/knowledge/remediation.py`)
are illustrative placeholders. The planner enforces the operator's maintenance-window constraint, so the *sum* of the
selected actions' downtimes never exceeds the configured window, but the individual values must be replaced with
site-specific estimates before any real planning use.

## 6. What this section does not claim

No throughput, latency, energy or memory measurement was made on any device in this work; the figures above are
third-party public measurements of the primitives, and the implications are arithmetic consequences of them. Real
deployment feasibility must be established per device model on the hospital's own network.

## References (public)

- NIST FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA), August 2024.
- Open Quantum Safe, liboqs algorithm pages for ML-KEM and ML-DSA (parameter-set summaries).
- Kannwischer et al., pqm4: post-quantum crypto library for the ARM Cortex-M4 — `benchmarks.md` and `results/`.
- NIST IR 8547, *Transition to Post-Quantum Cryptography Standards*, final (October 2026); NIST PQC project page.
- IETF RFC 7748 (X25519), RFC 8017 (RSA), RFC 5480 / RFC 7518 (ECDSA encodings), RFC 8446 (TLS 1.3).
