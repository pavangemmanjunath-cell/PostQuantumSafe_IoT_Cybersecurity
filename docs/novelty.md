# Technical Positioning

## Existing approaches

- **Cryptographic discovery / CBOM tooling** — inventories algorithms in code, certificates or network traffic.
- **Vulnerability scanners and TLS scanners** — report protocol/cipher weaknesses, mostly against classical attackers.
- **Risk registers and severity ranking (e.g. CVSS-style)** — prioritise by severity, usually without cost/downtime optimisation.
- **PQ migration guidance** (NIST NCCoE, NIST IR 8547 draft) — process and timelines rather than automated planning.
- **LLM-based security assistants** — flexible but hard to audit and non-deterministic.

## Limitations addressed

1. PQ exposure is usually assessed separately from identity, privacy and AI-safety risks of the same system.
2. Findings lists rarely say *what to do first under a fixed budget and maintenance window*.
3. Automated assessments are often hard to explain or reproduce.

## Approach implemented in this repository

A deterministic multi-agent pipeline whose agents gather evidence only via registered tools, a single additive scoring
model mapped onto TIPPSS pillars, a constrained optimiser (QIRO) with a reported optimality gap, and an explanation layer
(exact attributions, counterfactuals, traces). An LLM, if configured, only phrases the narrative.

## Technical differences

| Aspect | Typical practice | Here |
|---|---|---|
| Scope | crypto *or* privacy *or* device identity | one pipeline across six TIPPSS pillars incl. AI prompt risks |
| PQ classification | protocol version / cipher strength | per-primitive quantum status, hybrid awareness, NIST replacement, Mosca evaluation |
| AI-layer PQ risk | not considered | detection of prompts asking agents to downgrade PQ crypto |
| Prioritisation | severity order | knapsack optimisation with budget and downtime, gap to optimum reported |
| Explainability | narrative | exact decomposition + counterfactuals + tool-call trace |

## Research hypothesis

A transparent, constraint-aware multi-agent assessment yields remediation plans that are (a) auditable and (b) materially
different from severity-ordered lists under realistic budget/downtime constraints, while remaining fast enough for
interactive what-if analysis.

## Evidence currently available

- Optimiser: shipped solver reaches the exact optimum on 97.6 % of 500 synthetic instances (mean gap 0.05 %).
- Determinism and correctness: 148 backend tests including parity with the v0 prototype; 10 GUI end-to-end tests.
- Traffic rules: window-level rates on the CICIoMT2024 test split (optimistic; same data used for tuning).

## Evidence still required

- Comparison of plans against severity-ordered baselines and expert plans on realistic environments.
- Independent evaluation of detection rules (held-out data, other datasets).
- Practitioner study on usefulness of the explanations.
- Calibration or sensitivity analysis of scoring weights and cost templates.

## Limitations

See [limitations.md](limitations.md). No claim of novelty or superiority is made beyond the measurable differences above.
