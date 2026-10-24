# Use Cases

Status legend: **Implemented** (works in v0.1.0) · **Conceptual** (possible with current code, not validated) · **Proposed** (future).

## 1. PQ readiness check of a clinical gateway — Implemented

- **Problem:** Is this gateway's TLS configuration exposed to harvest-now-decrypt-later?
- **Stakeholder:** hospital security engineer, researcher.
- **Inputs:** `tls_config` incl. data lifetime; optional Mosca assumptions.
- **Workflow:** Assessment Lab or `POST /assessments` → Crypto Inventory → PQ Identification → scoring → plan.
- **Outputs:** per-primitive quantum status, NIST replacements, PQ readiness, HNDL finding, plan, PDF.
- **Expected value:** clear, referenced explanation of why "TLS 1.3" alone is not PQ-safe.
- **Assumptions:** configuration supplied accurately.
- **Limitations:** no active scanning.

## 2. Budget-constrained remediation planning — Implemented

- **Problem:** Which fixes fit this quarter's budget and maintenance window?
- **Inputs:** any assessment + `constraints`.
- **Workflow:** adjust budget/downtime sliders and rerun; compare selected/deferred actions and phases.
- **Outputs:** QIRO plan, deferral reasons, binding constraint, gap to optimum.
- **Limitations:** illustrative costs; replace with organisation estimates.

## 3. AI-assistant privacy and safety review — Implemented

- **Problem:** Do prompts reaching a clinical AI contain PHI, injection, PQ-downgrade or unsafe autonomous instructions?
- **Inputs:** `ai_prompt_logs` (or Synthea-derived prompts via upload).
- **Outputs:** findings with redacted evidence; remediation (redaction, prompt firewall, approval gate).
- **Limitations:** English regex rules; not a DLP product.

## 4. Fleet attack-and-defence simulation — Implemented

- **Problem:** Teaching / exploring how quantum-layer, network, identity and AI attacks change a fleet's risk, and how
  defences change it back.
- **Workflow:** Fleet Simulation → inject attacks → run agents per device → assess fleet → apply QIRO plan → re-assess.
- **Outputs:** live 3D state, event log, fleet verdict, fleet PDF.
- **Limitations:** discrete-time abstraction with synthetic telemetry.

## 5. Replay of recorded IoMT traffic — Conceptual

- **Workflow:** set `REPLAY_DATA_DIR` to user-downloaded CICIoMT2024 CSVs and create a simulation with `data_source=replay`.
- **Limitations:** replay maps attack types to files by name; not validated beyond smoke tests.

## 6. External agents using the tool APIs — Conceptual

- **Workflow:** an LLM tool-calling agent or another service calls `/api/v1/tools/*` to classify algorithms or scan text.
- **Limitations:** no authentication; local use only.

## 7. CBOM / scan-output ingestion — Proposed

Import CycloneDX CBOMs or TLS-scanner JSON to replace hand-written configurations.

## 8. Practitioner-validated planning study — Proposed

Evaluate plan usefulness with hospital security teams under appropriate governance.
