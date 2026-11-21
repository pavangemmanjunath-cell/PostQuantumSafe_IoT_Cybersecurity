# Technical Positioning

## Existing approaches

- **Cryptographic discovery / CBOM tooling** — inventories algorithms in code, certificates or network traffic.
- **Vulnerability scanners and TLS scanners** — report protocol/cipher weaknesses, mostly against classical attackers.
- **Risk registers and severity ranking (e.g. CVSS-style)** — prioritise by severity, usually without cost/downtime optimisation.
- **PQ migration guidance** (NIST NCCoE, NIST IR 8547) — process and timelines rather than automated planning.
- **LLM-based security assistants** — flexible but hard to audit and non-deterministic.

## Limitations addressed

1. PQ exposure is usually assessed separately from identity, privacy and AI-safety risks of the same system.
2. Findings lists rarely say *what to do first under a fixed budget and maintenance window*.
3. Automated assessments are often hard to explain or reproduce.
4. Remediation plans are rarely checked against the assessment that produced them.

## Approach implemented in this repository

A deterministic multi-agent pipeline whose agents gather evidence only via registered tools, a single additive scoring
model mapped onto the six TIPPSS pillars, a constrained optimiser with a reported optimality gap, an explanation layer
(exact attributions, counterfactuals, traces) and, since Release 3, a reassessment stage that applies a plan to the
configuration by code and re-runs the pipeline. An LLM, if configured, only phrases the narrative.

## Technical differences

| Aspect | Typical practice | Here |
|---|---|---|
| Scope | crypto *or* privacy *or* device identity | one pipeline across six TIPPSS pillars incl. AI prompt risks |
| PQ classification | protocol version / cipher strength | per-primitive quantum status, hybrid awareness, NIST replacement, Mosca evaluation with explicit assumptions |
| AI-layer PQ risk | not considered | detection of prompts asking agents to downgrade PQ crypto |
| Prioritisation | severity order | two-constraint knapsack with budget and downtime; gap to the exact / ILP optimum reported |
| Plan validation | none | reassessment of the remediated configuration; shared-root-cause planner |
| Explainability | narrative | exact decomposition + counterfactuals + tool-call trace |
| Traceability | informal | finding type → pillar → deduction → public reference (42 types) |

## Research hypothesis

A transparent, constraint-aware multi-agent assessment yields remediation plans that are (a) auditable and (b) materially
different from severity-ordered lists under realistic budget/downtime constraints, while remaining fast enough for
interactive what-if analysis.

## Evidence currently available (Release 3, all artifacts in `benchmarks/results/`)

- **Optimiser quality (E3, E8).** Annealing + local search reaches the exact optimum on 97.6 % of 500 instances with
  n ≤ 14 (mean gap 0.05 %). Against a HiGHS integer-programming reference the shipped planner stays within a mean
  gap of 0.30 % (n = 20) to 0.055 % (n = 200), max 3.0 % to 0.28 %; the annealing stage adds nothing beyond the greedy
  start for n ≥ 50, and the MIP solver is exact and up to 15× faster at n = 200.
- **Scoring robustness (E7).** The SAFE / AT_RISK / UNSAFE status of the ten scenarios never changes under ±20 %
  perturbations of weights, points or deductions (rank correlation 1.0); the four-level verdict flips in up to 4 of 10
  scenarios under severity-point scaling because scores sit near the thresholds; the ten-year rule changes one status
  at L = 5 and two verdicts at L = 20.
- **Plan validity (E9).** Reassessment reaches SAFE in 7 of 10 scenarios with the shipped plan; the projected score
  differs from the reassessed score by 9.3 points on average (max 26); the shared-root-cause planner reduces this to
  2.7 and is cheaper in 7 of 9 non-trivial scenarios. The worked example's plan is best by reassessment but not the
  cheapest plan attaining it. Network mitigations are unmodelled, so one scenario stays UNSAFE.
- **Traffic rules (E6, E10).** On CICIoMT2024 test windows not used for threshold selection the rules keep F1 ≈ 0.98
  with FPR 0–2.7 %; a packet-size baseline matches that F1 on this flood-dominated split, so the rules' value is the
  low FPR and attack-type attribution rather than raw F1. The CICIoMT2024 train split was not available.
- **Attack simulation (E11).** 234 of 249 exploitable (device, attack, seed) runs produce a new finding from the
  expected agent; the 15 misses are HNDL captures on devices already flagged at baseline; every re-injection after the
  catalogue mitigation is blocked by the simulator's model.
- **Determinism and correctness.** 148 backend tests of v0.1.0 plus the Release 3 tests (see
  [reproducibility.md](reproducibility.md)), including parity with the v0 prototype and byte-identical default planner
  output; 12 GUI end-to-end tests.

## Evidence still required

- Comparison of plans against severity-ordered baselines and expert plans on realistic environments.
- Capture-level train/test evaluation of the detection rules on the CICIoMT2024 train split and on other datasets;
  evaluation against adaptive adversaries.
- Configurations derived from real scanner output or device documentation instead of hand-written scenarios.
- Practitioner study on usefulness of the explanations.
- Calibration of scoring weights and cost templates on incident and project data.

## Limitations

See [limitations.md](limitations.md). No claim of novelty or superiority is made beyond the measurable differences above.
