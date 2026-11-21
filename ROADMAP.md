# Roadmap

This roadmap describes intentions, not commitments. Items marked **Proposed** are research ideas that may change or be dropped.

## Current stable capabilities (v0.3.0)

- 14-agent assessment pipeline with live streaming, tool APIs and full traces
- Post-quantum identification (FIPS 203/204/205, NIST IR 8547 draft timeline, hybrid detection, Mosca's inequality)
- Privacy, prompt-injection (incl. PQ-downgrade), secret-exposure, clinical-safety, device-identity and traffic-anomaly detection
- QIRO constrained remediation planning with reported optimality gap; ILP (HiGHS) reference benchmark up to n = 200
- Explainability: evidence, exact attributions, counterfactuals, plan projection; **reassessment** of the remediated
  configuration and an opt-in shared-root-cause planner (Release 3)
- Sensitivity analysis of the scoring constants and the lifetime threshold; held-out traffic evaluation (cross-source
  and temporal protocols); attack simulation on the hospital ward; standards traceability API (Release 3)
- IoT fleet simulator with attack injection and mitigations; React + three.js GUI with a Research Results tab; PDF
  reports; optional LLM narrative

## Near-term improvements

- **Capture-level train/test evaluation** of the traffic rules on the CICIoMT2024 train split (the protocol is
  implemented; the split was not available for Release 3)
- **Real configuration ingestion**: parse TLS scan output (e.g. from openssl / sslyze / testssl.sh JSON) instead of hand-written configs
- CBOM import (CycloneDX cryptographic bill of materials)
- Persistent storage option for assessments (currently in memory)
- Authentication for multi-user deployments; Docker images
- Accessibility review of the GUI

## Research extensions

- **Proposed:** learned or expert-elicited weights for the PQ risk score (the sensitivity analysis of Release 3 bounds,
  but does not calibrate, their effect)
- **Proposed:** stochastic CRQC-arrival model replacing the single Mosca z assumption
- **Proposed:** multi-period (phased) optimisation with precedence constraints between actions, optimising the
  reassessed outcome rather than summed benefit
- **Proposed:** replace the pure-Python local search by the ILP solver in the product (Release 3 showed it is exact and
  faster at n ≤ 200)
- **Proposed:** ML-based traffic detectors as an optional agent, evaluated against the transparent rule baseline
- **Proposed:** formal evaluation of PQ-downgrade prompt-injection detection on an open prompt-security benchmark

## Community contributions welcome

- Additional device profiles and fleet templates (e.g. smart building, energy/BESS)
- Dataset adapters for openly licensed IoT/IoMT datasets
- Translations of the GUI; documentation improvements
- Independent reproductions on Linux/macOS

## Long-term research direction

Investigate whether transparent, auditable multi-agent assessment can support realistic post-quantum migration planning
for safety-critical connected systems, and validate it with practitioners on real (appropriately governed) environments.
