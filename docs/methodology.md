# Methodology

## Research objective

Explore whether a transparent multi-agent pipeline can jointly assess post-quantum exposure and the other IEEE 2933-2024
TIPPSS risk dimensions of clinical IoT systems, explain its conclusions, and propose a remediation plan that respects
budget and downtime constraints.

## Inputs

| Field | Content |
|---|---|
| `tls_config` | `tls_version`, `key_exchange`, `cert_signature_algo`, `cert_key_algo`, `symmetric_cipher`, `hash`, `data_lifetime_years` |
| `device_logs` | per device: `device_id`, `cert_present`, `auth_status`, `failed_login_count`, optional `debug_log` |
| `ai_prompt_logs` | strings or `{prompt|text}` objects |
| `iot_traffic` | `window` (CICIoMT-style rows), `feature_summary` (per-column means), or precomputed `features` |
| `constraints` | `budget_usd`, `max_downtime_hrs` |
| `assumptions` | `migration_years` (y), `years_to_crqc` (z) for Mosca's inequality |

## Data preparation

Prompt/device fields are normalised to lists (`null → []`, scalar → `[scalar]`). Traffic features are window means of
binary/continuous CICIoMT columns. CSV uploads are detected by header (not file name); traffic CSVs carry no crypto
configuration, so none is assumed unless the user selects a profile.

## Features

Traffic: `syn_ratio`, `ack_ratio`, `rst_ratio`, `fin_ratio`, `tcp_ratio`, `udp_ratio`, `rate_mean`, `tot_size_mean`,
`header_length_mean`, `control_flag_ratio = syn + fin + rst`.
Crypto: catalogue classification of each primitive into `quantum_vulnerable` (Shor), `grover_weakened`,
`quantum_resistant`, `hybrid_pq`, `pq_candidate`, `classically_broken`, `deprecated_protocol`, `transitional_protocol`, `unknown`.

## Model / algorithm

### Detection
Rule tables (`knowledge/patterns.py`, `knowledge/traffic_rules.py`, `knowledge/pqc_catalog.py`). Each match becomes a
finding with severity, TIPPSS pillar mapping and redacted evidence.

### Harvest-now-decrypt-later (HNDL)
A critical `long_lifetime_classical_crypto` finding is raised when `data_lifetime_years ≥ 10`, at least one classical
public-key finding exists, **and** key establishment is not PQ/hybrid protected. Mosca's inequality is reported
alongside: data is at risk if `x + y > z` (x = data lifetime, y = migration time, z = years to a CRQC — a user assumption).

### TIPPSS pillar scores
Each pillar starts at 100; every mapped finding deducts critical 25 / high 15 / medium 8 / low 3; floor 0.

### PQ risk score

For categories *c* ∈ {pkc, tls, lifetime, identity, secrets, migration}:

```
v_c = max over findings f in category c of points(severity_f)      points: critical 100, high 75, medium 50, low 25
v_migration = 0 if a PQ/hybrid key exchange or PQ signature is detected, else 75
score = round( 0.30 v_pkc + 0.20 v_tls + 0.20 v_lifetime + 0.15 v_identity + 0.10 v_secrets + 0.05 v_migration )
verdict: ≤25 Safe, ≤50 Partially Safe, ≤75 Not Post-Quantum Safe, else Critical Quantum Risk
```

Weights and points are design choices carried over from the v0 prototype; they are not empirically fitted.

### Environment status
`UNSAFE` if any critical finding or score > 50; otherwise `AT_RISK` if any high/medium finding, score > 25, or no
crypto configuration was supplied; otherwise `SAFE`.

### QIRO — remediation optimisation

Each finding *i* becomes an action with cost `C_i`, downtime `D_i`, complexity `K_i` (illustrative templates) and benefit

```
B_i = round(r_i · m(sev_i)) + 25·[PQ-related] + 20·[Safety pillar] + round(10 · Σ_p w_p)
m: critical 1.5, high 1.0, medium 0.6, low 0.3;   w: Privacy 1.2, Safety 1.4, others 1.0
```

Objective:  `max Σ (B_i − 0.5 K_i) x_i`  s.t.  `Σ C_i x_i ≤ budget`, `Σ D_i x_i ≤ max_downtime`, `x_i ∈ {0,1}` —
a two-constraint 0/1 knapsack. Solver: greedy start by value density → simulated annealing
(`T₀ = 100`, cooling 0.995, `min(3000, 200 + 80n)` single-flip moves, only feasible moves accepted, seeded RNG) →
deterministic best-improvement local search over add/drop/swap moves. For `n ≤ 14` an exhaustive search gives the exact
optimum and the gap is reported. "Quantum-inspired" refers to the QUBO/Ising-style energy; everything runs on a classical CPU.

Selected actions are ordered by `pqc_urgency + safety_criticality + 100·m(sev) + tippss_weight` and partitioned into
phases: 0–6 months (critical or PQ-urgent, up to five), 6–18 months (remaining high/overflow), 18–36 months (rest).

### Explainability
- Exact additive attribution: contribution of category *c* = `w_c · v_c` (sums to the unrounded score).
- Pillar explanations: list of deductions per finding.
- Counterfactuals: remove all findings of one type and re-run the same scoring functions.
- Plan projection: remove findings addressed by selected actions (assumes complete remediation).
- Agent traces: notes, tool calls with summaries, timings.

## Training / optimisation

No model training. The only optimisation is QIRO at inference time. Traffic thresholds were set manually by inspecting
CICIoMT2024 test-split window statistics (see Threats to validity).

## Inference / execution

Deterministic given input and seed. Typical single-system assessment takes milliseconds of compute (agents) plus PDF
rendering on request.

## Outputs

`AssessmentResult`: environment status and reasons, PQ score and verdict, findings with evidence, TIPPSS scores, crypto
inventory, PQ posture, QIRO plan with optimality data, explanation object, narrative, agent traces, metadata (seed, version).

## Evaluation

| What | How | Where |
|---|---|---|
| Behavioural correctness | 148 unit/integration tests with hand-derived expectations | `backend/tests/` |
| Port fidelity | Parity with recorded v0 outputs | `tests/integration/test_reference_parity.py` |
| Optimiser quality | Gap to exhaustive optimum on 500 synthetic instances | `benchmarks/qiro_optimality.py` |
| Traffic rules | Window-level detection / false-positive rates on CICIoMT2024 test split | `benchmarks/traffic_rules_eval.py` |
| GUI | Playwright end-to-end tests in Chromium | `frontend/e2e/` |

## Baselines

Optimiser: greedy value-density start and annealing-only results are reported next to the shipped solver. No external
tool baseline has been evaluated yet.

## Metrics

Optimality share, mean/p95/max gap (%); window-level detection rate and false-positive rate.

## Experimental configuration

Window 100 rows; up to 2000 windows per file; QIRO seed = instance index; benchmark seed 0; Python 3.13.5.

## Assumptions

Supplied configurations are accurate; remediation fully removes a finding; cost/downtime templates are representative
only for illustration; a single CRQC-arrival horizon z.

## Threats to validity

- Traffic thresholds tuned and evaluated on the same split (optimistic); very few ARP/MQTT windows.
- Regex detectors are language- and format-specific.
- Scoring weights and severities are expert choices without empirical calibration.
- Synthetic scenarios may not reflect real hospital configurations.
- The optimality benchmark uses random synthetic instances that may differ from real finding mixes.
