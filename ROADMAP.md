# Roadmap

This roadmap describes intentions, not commitments. Items marked **Proposed** are research ideas that may change or be dropped.

## Current stable capabilities (v0.1.0)

- 14-agent assessment pipeline with live streaming, tool APIs and full traces
- Post-quantum identification (FIPS 203/204/205, NIST IR 8547 draft timeline, hybrid detection, Mosca's inequality)
- Privacy, prompt-injection (incl. PQ-downgrade), secret-exposure, clinical-safety, device-identity and traffic-anomaly detection
- QIRO constrained remediation planning with reported optimality gap
- Explainability: evidence, exact attributions, counterfactuals, plan projection
- IoT fleet simulator with attack injection and mitigations; React + three.js GUI; PDF reports; optional LLM narrative

## Near-term improvements

- Independent **train/test evaluation** of the traffic rules (calibrate on the CICIoMT2024 train split, report on test)
- **Real configuration ingestion**: parse TLS scan output (e.g. from openssl / sslyze / testssl.sh JSON) instead of hand-written configs
- CBOM import (CycloneDX cryptographic bill of materials)
- Persistent storage option for assessments (currently in memory)
- Authentication for multi-user deployments; Docker images
- Accessibility review of the GUI

## Research extensions

- **Proposed:** learned or expert-elicited weights for the PQ risk score, with sensitivity analysis
- **Proposed:** stochastic CRQC-arrival model replacing the single Mosca z assumption
- **Proposed:** multi-period (phased) optimisation with precedence constraints between actions
- **Proposed:** comparison of QIRO with ILP solvers and QUBO solvers on quantum-annealing hardware
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
