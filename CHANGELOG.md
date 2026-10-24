# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Zenodo DOIs in `CITATION.cff`, README, release notes and the About page (all versions: 10.5281/zenodo.23618135).

## [0.1.0] - 2026-10-24

First public release of PostQuantumSafe IoT Cybersecurity (TIPPSS SafeGuard-PQ): a TIPPSS-based (IEEE 2933-2024) agentic testing framework that
checks whether IoT and edge-device environments are safe against post-quantum attacks. Complete re-implementation of
the hackathon prototype (v0) as an open, contributable research codebase.

### Added
- Python **FastAPI** backend (`safeguard_pq`) with **14 agents** in a staged pipeline; six detection agents run concurrently.
- **Post-quantum identification** knowledge base (FIPS 203/204/205, NIST IR 8547 draft timeline, hybrid groups, Grover
  margins, deprecated protocols), PQ-readiness levels and Mosca's-inequality evaluation with explicit assumptions.
- **Tool registry**: agents gather evidence through registered tools, also exposed as `GET/POST /api/v1/tools`.
- **Explainability**: per-finding evidence (redacted), exact score attribution, pillar deduction breakdowns,
  counterfactuals, projected effect of the remediation plan, and full agent traces.
- New detections: **PQ-downgrade prompt injection**, delimiter injection, tool hijacking, encoded payloads, GitHub/Slack
  tokens, deprecated symmetric ciphers, classical certificate keys, and **traffic-anomaly rules** over CICIoMT-style features.
- **QIRO** optimizer: seeded simulated annealing, deterministic local-search polish, exact solver for small instances and
  reported optimality gap.
- **IoT fleet simulator** (hospital ward, smart factory) with 14 attack injections across quantum, identity, network and AI
  layers, 12 mitigations, synthetic or replayed telemetry, fleet-wide shared-budget planning.
- **WebSocket** streams for live agent events and simulator telemetry.
- **PDF reports** stating whether the environment is safe (single system and fleet).
- Optional, provider-agnostic **LLM** narrative (`openai_compatible`, `anthropic`) configured via `.env`; redacted inputs only.
- **React + TypeScript + three.js** frontend: 3D fleet view, live agent pipeline, assessment lab, tool playground.
- CLI `safeguard-pq` (`serve`, `scenarios`, `assess`).
- **Q-Day what-if**: adjustable years-to-quantum-computer and migration time (Mosca); devices are re-classified as
  harvest-now-decrypt-later exposed, and a Mosca-based finding is raised by the PQ Identification agent.
- **One-click use case** "ICU Q-Day drill": record-now, weaken, Q-Day, AI misuse, detect, respond and verify steps.
- **Core-issue analysis**: fleet root causes (classical key exchange, classical certificates, exposed data, active
  attacks) with affected devices and a one-click fix; affected-devices table sorted by live risk.
- **Issue timeline**: fleet and device risk over time with markers for attacks, defences and agent findings.
- Single-screen simulation view with Lucide icons (ISC licence) for devices, the simulated adversary and the analyst.
- 148 backend tests (unit, integration, v0 parity) and 10 Playwright browser end-to-end tests; benchmark scripts.
- Research-software documentation: CITATION.cff, contributing, security, roadmap, methodology, reproducibility, limitations.

### Changed
- License is now **Apache-2.0** (the v0 README referenced MIT without a license file).
- CSV uploads are judged on their **content**; the v0 behaviour of inferring crypto settings and device failures from the
  file name was removed. Without an explicit crypto profile the PQ posture is reported as unverified.
- Harvest-now-decrypt-later is raised only when key establishment is not PQ/hybrid protected (v0 also raised it for
  classical signatures alone).
- Post-quantum attack simulations corrected: legacy-fallback downgrade and classical-only group fallback are described
  accurately for TLS 1.3, and "quantum certificate forgery (CRQC)" is refused for ML-DSA certificates.
- Migration phases now partition the selected actions (v0 could list an action twice or drop actions beyond the
  first five).

### Fixed
- v0 response path for scores above 75 returned empty result fields after the report step.
- Redaction now masks full patient names after a "patient name/id" label.

### Removed
- The low-code workflow-engine runtime and the Streamlit dashboard of the v0 prototype.
- Bundled third-party CICIoMT2024 CSV files (download instructions in `datasets/README.md`).

### Security
- Test and demo credentials are generated at runtime so no credential-shaped literals exist in the source tree.
