# Benchmarks

Machine-readable results live in [`results/`](results/). Every number reported in the README, in
[`docs/release-3/README.md`](../docs/release-3/README.md) and in the web application's Research Results tab comes from
these files. Experiment identifiers E1–E10 are those of the revised journal paper; E11 and E12 are supplementary
(not reported in the paper). Figures are generated from the same files by `make_figures.py` (optional `benchmark`
extra: `pip install -e "backend[benchmark]"`).

| Id | Script | Artifact | Question |
|---|---|---|---|
| E1–E5 | `paper_experiments.py` | `paper_e1_systems.json`, `paper_e2_attack_conditions.json`, `paper_e3_qday_sweep.json`, `paper_e4_budget_sweep.json`, `paper_e5_worked_example.json` | the paper's E1 (Table II), E2 (attack conditions), E3 (Q-Day sweep), E4 budget sweep and E5 (worked example), each checked against every number the paper states |
| E4 | `qiro_optimality.py` | `qiro_optimality.json` | solver quality (second part of E4): gap of the planner to the exhaustive optimum, n ≤ 14 |
| E6 | `traffic_rules_eval.py` | `traffic_rules_eval.json` | window-level rule behaviour on the CICIoMT2024 test split (same split as threshold selection) |
| E7 | `sensitivity_analysis.py` | `sensitivity_analysis.json` | sensitivity of verdicts, scores and plans to the scoring constants and the lifetime threshold |
| E8 | `qiro_scalability.py` | `qiro_scalability.json` | planner versus greedy, local search and an ILP reference for n = 20…200 |
| E9 | `plan_reassessment.py` | `plan_reassessment.json` | summed benefit vs projected vs reassessed score; independent vs shared-root-cause planner |
| E10 | `traffic_rules_holdout.py` | `traffic_rules_holdout*.json` | rules evaluated on windows not used for threshold selection, with CIs and baselines |
| E11 | `attack_simulation_eval.py` | `attack_simulation.json` | supplementary (not reported in the paper): attacker-versus-defender outcomes on the hospital-ward simulator |
| E12 | `../scripts/gen_standards_map_doc.py` | `../docs/release-3/standards_mapping.md` | supplementary (not reported in the paper): finding type → principles → deduction → score category → references |
| — | `make_synthetic_traffic_dataset.py` | `../datasets/synthetic_holdout/` | synthetic development split for E10 |
| — | `make_figures.py` | `../docs/release-3/figures/` | result figures |
| — | `run_all.py` | all of the above | runs every step in order; `--check` compares the regenerated artifacts with the committed ones |

Environment for all recorded artifacts: Python 3.13.5, Windows 11, software version 0.3.0, 2026-11-22 (E6:
2026-10-17, v0.1.0). Runtimes are single-machine wall-clock values and vary with hardware and load.

## E1–E5. Paper experiments (`paper_experiments.py`)

One command reruns the five experiments of the journal paper that have no script of their own, with the shipped
software (seed 2026, no LLM, default options; the shared-root-cause planner only in E5, as in the paper):
`python benchmarks/paper_experiments.py` (a few seconds; `--only e1,e5` selects experiments, `--out-dir` the folder,
`--strict` exits with status 1 if a stated value is not reproduced). Each artifact records the inputs, the method
with every input assumption, the results and a `paper_check` block that lists each number the paper states with
`expected`, `reproduced` and `match`.

| Id | Paper content | Inputs | Artifact | Stated values reproduced |
|---|---|---|---|---|
| E1 | Table II (every cell) and the principle scores of Section VII-A | the ten built-in scenarios | `paper_e1_systems.json` | 128 / 128 |
| E2 | six attack conditions on a legacy infusion-pump gateway, before and after the countermeasures | `examples/paper/e2_infusion_pump_conditions.json` | `paper_e2_attack_conditions.json` | 42 / 42 |
| E3 | HNDL exposure of seven data classes (5–30 years) against z = 4–30 years for y = 2, 5, 8; hybrid ML-KEM | E2 base gateway (classical) and migrated gateway (hybrid) | `paper_e3_qday_sweep.json` | 12 / 12 |
| E4 | budget sweep 10 000–200 000 USD in steps of 10 000 for the ICU gateway and the legacy system | `icu_gateway_critical`, `legacy_worst_case`, downtime 40 h | `paper_e4_budget_sweep.json` | 9 / 9 |
| E5 | worked example of Section III: attribution, counterfactual, plan, projection, reassessment, all feasible subsets, shared-root-cause mode | `examples/paper/worked_example_gateway.json` (Listing 1 of the original draft) | `paper_e5_worked_example.json` | 25 / 25 |

Input reconstruction: the original draft names the E2 conditions and the seven E3 data classes but not their
configurations. They are taken from the v0.1.0 experiment script that produced the draft's numbers, and every E2
condition equals the effect of the simulator's own attack injection (`Simulation.inject`), which the script
re-checks on every run; the assumptions are listed in each artifact's `method`. All 216 stated values are reproduced
with v0.3.0, and the E2–E4 values equal those recorded with v0.1.0.

## E4 (solver quality). QIRO optimality, n ≤ 14 (`qiro_optimality.py`)

| Item | Value |
|---|---|
| Objective | How close the shipped heuristic gets to the exact optimum of the same objective |
| Baselines | simulated annealing alone; exhaustive search (exact) |
| Dataset | 500 random synthetic instances: n ∈ [3, 14] actions drawn from the remediation catalogue, budgets {20k, 50k, 100k} USD, downtime {4, 10, 40} h |
| Metrics | share of instances solved optimally; mean / p95 / max relative gap |
| Command | `python benchmarks/qiro_optimality.py --instances 500 --seed 0` |

| Method | Optimal | Mean gap | p95 gap | Max gap |
|---|---|---|---|---|
| Annealing only | 94.8 % | 0.19 % | 0.16 % | 20.16 % |
| Annealing + local search | 97.6 % | 0.05 % | 0.00 % | 6.06 % |

Mean run time per instance including the exhaustive solver: 8.62 ms in the recorded run. Limitation: synthetic
instances; exact solver limited to n ≤ 14.

## E8. Scalability against an integer-programming reference (`qiro_scalability.py`)

| Item | Value |
|---|---|
| Reference | HiGHS 1.16.0 MIP via `highspy`, zero MIP gap tolerance (proven optima); cross-checked against the exhaustive solver on 100 instances with n ≤ 14 (100/100 agree) |
| Dataset | 50 instances per size n ∈ {20, 50, 100, 200}; same finding distribution as E4; budget = τ · Σ cost, downtime = τ · Σ downtime, τ ∈ U{0.25, 0.5, 0.75} |
| Methods | greedy start only; greedy + local search; greedy + annealing; shipped (greedy + annealing + local search) |
| Command | `python benchmarks/qiro_scalability.py --sizes 20,50,100,200 --instances-per-size 50 --seed 0 --small-check 100` (≈ 100 s) |

Shipped planner, optimal share / mean / p95 / max gap to the ILP optimum, and mean runtime per instance:

| n | Greedy only | Shipped (greedy + SA + LS) | Shipped runtime | ILP runtime |
|---|---|---|---|---|
| 20 | 40 % / 1.19 / 3.37 / 5.00 % | 76 % / 0.30 / 1.67 / 3.04 % | 17 ms | 16 ms |
| 50 | 28 % / 0.43 / 1.22 / 1.82 % | 46 % / 0.19 / 0.77 / 1.05 % | 67 ms | 24 ms |
| 100 | 10 % / 0.29 / 0.71 / 1.17 % | 32 % / 0.09 / 0.27 / 0.36 % | 190 ms | 41 ms |
| 200 | 10 % / 0.16 / 0.48 / 0.62 % | 28 % / 0.06 / 0.16 / 0.28 % | 811 ms | 54 ms |

Findings: relative gaps shrink with n while the exactly-optimal share falls; simulated annealing improved on the
greedy start in 7 of 200 instances (all at n = 20) and never for n ≥ 50 — the deterministic local search closes the
gap; the tightest budgets (τ = 0.25) give the largest gaps; the MIP solver is exact and up to 15× faster than the
pure-Python heuristic at n = 200. Full tables by size and τ are in the JSON (`by_size`, `by_tau`).

## E7. Sensitivity of the scoring model (`sensitivity_analysis.py`)

Ten built-in scenarios, assessment seed 2026. Metrics per perturbed configuration: share of scenarios whose four-level
verdict changes, share whose SAFE / AT_RISK / UNSAFE status changes, mean and max |ΔS|, Spearman rank correlation of
the PQ-score ranking, and the Jaccard similarity of the selected-action sets where plans were recomputed.
Command: `python benchmarks/sensitivity_analysis.py --seed 2026`.

| Design | Perturbation | Verdict changes | Status changes | Max \|ΔS\| | Spearman ρ |
|---|---|---|---|---|---|
| S1 | each category weight ×0.8 / ×1.2, renormalised (12 configs) | ≤ 1/10 (4 configs), else 0/10 | 0/10 | 4 | 1.000 |
| S2 | severity points ×0.8 / ×1.2 | 4/10 / 2/10 | 0/10 | 17 | 1.000 |
| S3 | pillar deductions ×0.8 / ×1.2 | 0/10 (PQ score unaffected by construction) | 0/10 | pillar scores: max \|ΔP\| 17 / 15; weakest pillar unchanged | 1.000 |
| S4 | lifetime threshold L = 5 / 15 / 20 y | 0/10 / 0/10 / 2/10 | 1/10 / 0/10 / 0/10 | 20 / 0 / 20 | 0.997 / 1.000 / 0.997 |
| S5 | optimizer pillar weights ×0.8 / ×1.2 (plans re-run) | — | — | — | plans identical 10/10 (Jaccard 1.0) |

Verdict flips are threshold crossings of scores that sit near 25 / 50 / 75 (23, 26, 46, 61, 89), not re-rankings; the
environment status is driven by critical and elevated findings and never flips under S1–S3. At L = 5 the 8-year
`ehr_tls13_classical` scenario becomes UNSAFE (26 → 46); at L = 20 the two 15-year scenarios lose the critical
long-lifetime finding (61 → 41) but stay UNSAFE on other findings. Plan Jaccard for L = 5 / 20: 0.95 / 0.88.

## E9. Plan evaluation by reassessment (`plan_reassessment.py`)

For each scenario the plan's mitigations are applied to the configuration by code (`optimizer/reassess.py`) and the
pipeline is re-run; every feasible subset of actions (n ≤ 10) is also reassessed to find the best attainable outcome
(413 pipeline runs). Plan A = shipped planner (independent per-finding actions); plan B = shared-root-cause planner
(actions with the same mitigation merged and costed once). Command: `python benchmarks/plan_reassessment.py --seed 2026`.

| Scenario | n | Baseline S / status | Plan A cost / ΣB / S_proj → S_reass / status | Plan B cost / S_proj → S_reass / status | Plan A best / cheapest-best |
|---|---|---|---|---|---|
| icu_gateway_critical | 8 | 61 UNSAFE | 98 k / 436 / 26 → 0 / SAFE | 88 k / 0 → 0 / SAFE | yes / no (58 k attains 0) |
| nextgen_pq_safe | 0 | 0 SAFE | — | — | yes / yes |
| ehr_tls13_classical | 5 | 26 AT_RISK | 95 k / 250 / 26 → 0 / SAFE | 70 k / 0 → 0 / SAFE | yes / no |
| clinical_ai_phi | 4 | 0 UNSAFE | 30 k / 255 / 0 → 0 / SAFE | 16 k / 0 → 0 / SAFE | yes / no |
| secret_exposure | 2 | 10 UNSAFE | 10 k / 130 / 0 → 0 / SAFE | 5 k / 0 → 0 / SAFE | yes / no |
| legacy_worst_case | 9 | 89 UNSAFE | 97 k / 415 / 46 → 43 / UNSAFE | 80 k / 54 → 30 / UNSAFE | no / no (0 SAFE attainable for 72 k) |
| tight_budget_qiro | 8 | 61 UNSAFE | 18 k / 189 / 58 → 46 / UNSAFE | 30 k / 46 → 43 / UNSAFE | no / no (best 38) |
| pq_downgrade_prompt | 2 | 0 UNSAFE | 18 k / 154 / 0 → 0 / SAFE | 10 k / 0 → 0 / SAFE | yes / no |
| hybrid_transition | 2 | 23 AT_RISK | 70 k / 175 / 0 → 0 / SAFE | 70 k / 0 → 0 / SAFE | yes / no |
| infusion_syn_flood | 6 | 46 UNSAFE | 77 k / 299 / 26 → 0 / UNSAFE | 82 k / 0 → 0 / UNSAFE | yes / no; `rate_limiting` unmodelled, `syn_flood_pattern` remains |

Summary: plan A reaches SAFE in 7/10 systems (1 SAFE at baseline), projected = reassessed in 5/10, mean |S_proj −
S_reass| 9.3 (max 26), best by reassessment 8/10, cheapest-best 1/10. Plan B: SAFE 7/10, projected = reassessed 8/10,
mean error 2.7 (max 24), best by reassessment 9/10, cheapest-best 7/10 (compared with subsets of whole root-cause
groups under the grouped cost accounting). The projection is pessimistic where several findings share one mitigation
and optimistic where a mitigation cannot be verified at configuration level (network controls).

## E6. Traffic rules, same split (`traffic_rules_eval.py`)

| Item | Value |
|---|---|
| Dataset | CICIoMT2024 `WiFi_and_MQTT/attacks/CSV/test` (download separately; not redistributed) |
| Method | consecutive 100-row windows, up to 2000 per file; a window is flagged if any rule fires |
| Command | `python benchmarks/traffic_rules_eval.py --data-dir <folder> --window 100` |

| File | Windows | Flagged | Rate |
|---|---|---|---|
| Benign_test | 376 | 10 | 2.7 % (FPR) |
| ARP_Spoofing_test | 17 | 15 | 88.2 % |
| MQTT-Malformed_Data_test | 17 | 13 | 76.5 % |
| Recon-Port_Scan_test | 226 | 223 | 98.7 % |
| TCP_IP-DDoS-TCP_test | 1825 | 1750 | 95.9 % |
| TCP_IP-DoS-SYN_test | 985 | 985 | 100 % |

**Caveat:** the shipped thresholds were chosen by inspecting window statistics of this same split; these figures are
optimistic and not an estimate of generalisation. See E10.

## E10. Traffic rules on held-out windows (`traffic_rules_holdout.py`)

Windows are consecutive, non-overlapping, 100 rows, never spanning files. Thresholds are tuned on the development
windows only (each rule's thresholds × factors {0.5, 0.75, 1, 1.25, 1.5}, rule structure unchanged, best F1 for the
rule's target class vs benign), then evaluated once on the held-out windows: window-level precision / recall / F1 /
FPR (attack vs benign) with 1000-resample bootstrap 95 % CIs, per-class rates with Wilson 95 % intervals, and
baselines fitted on the development windows (majority class; mean `Rate` above the benign 99th percentile; packet
size outside the benign 1st–99th percentile band). The CICIoMT2024 *train* split was not available, so two
protocols that need only the test split were run:

| Protocol | Development | Held-out | Command |
|---|---|---|---|
| P1 cross-source | synthetic simulator dataset (120 windows) | CICIoMT2024 test split (3446 windows) | `--train-dir datasets/synthetic_holdout/train --test-dir <CIC test folder> --protocol cross_source` |
| P2 temporal split | first 50 % of each test capture's windows (1721) | last 50 % (1725) | `--test-dir <CIC test folder> --protocol temporal_split --dev-fraction 0.5` |
| demonstration | synthetic train (120) | synthetic test (120) | `--train-dir datasets/synthetic_holdout/train --test-dir datasets/synthetic_holdout/test` |

Held-out window-level results (95 % bootstrap CIs in brackets):

| Protocol | Predictor | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|
| P1 | tuned (= shipped: the synthetic dev set confirmed every shipped threshold) | 0.997 [0.995, 0.999] | 0.973 [0.967, 0.978] | 0.985 [0.982, 0.987] | 0.027 [0.011, 0.044] |
| P1 | baseline: majority class | 0.891 | 1.000 | 0.942 | 1.000 |
| P1 | baseline: Rate > benign p99 | 0.927 | 0.241 | 0.382 | 0.154 |
| P1 | baseline: size outside benign p1–p99 | 0.906 | 1.000 | 0.951 | 0.848 |
| P2 | shipped (not held-out: thresholds set on these captures) | 0.999 | 0.967 | 0.983 | 0.011 |
| P2 | tuned on dev half (4 of 5 rules changed) | 1.000 [1.000, 1.000] | 0.973 [0.965, 0.981] | 0.987 [0.982, 0.991] | 0.000 [0.000, 0.000] |
| P2 | baseline: majority class | 0.891 | 1.000 | 0.942 | 1.000 |
| P2 | baseline: Rate > benign p99 | 0.995 | 0.130 | 0.229 | 0.005 |
| P2 | baseline: size outside benign p1–p99 | 1.000 | 0.978 | 0.989 | 0.000 |

Per-class held-out detection (P2, tuned): DDoS 96.5 % [95.1, 97.5], SYN DoS 100 % [99.2, 100], port scan 96.5 %
[91.2, 98.6], MQTT malformed 88.9 % [56.5, 98.0] (n = 9), ARP spoofing 55.6 % [26.7, 81.1] (n = 9); benign FPR 0 %
[0, 2.0]. Rule attribution is also reported (`target_rule_rate`): for port scans the port-scan rule itself fires on
84.5 % (P1) / 90.3 % (P2) of windows, the rest are flagged by other rules.

**Interpretation.** The rules keep F1 ≈ 0.98 on windows not used for threshold selection, with near-zero false
positives. However, the CICIoMT2024 test split is 89 % attack windows dominated by small-packet floods, so a
packet-size band baseline reaches F1 0.95 (P1) and 0.99 (P2) and the majority-class baseline 0.94: window-level F1 on
this split is not a demanding target, and the rules' advantage lies in the low FPR and in attributing a window to an
attack type, not in raw F1. The two small classes have wide intervals. The synthetic demonstration run is perfectly
separable by construction and demonstrates the protocol only. Bootstrap intervals treat windows as independent
although consecutive windows of one capture are correlated.

## E11. Attack simulation on the hospital ward (`attack_simulation_eval.py`) — supplementary, not reported in the paper

One fresh simulation per (seed, device, attack): baseline assessment → inject → two ticks → assess → apply every
mitigation in the attack's `blocked_by` → two ticks → assess → re-inject. "Detected" = a new finding from the agent
the catalogue names for the attack; "blocked" = the simulator refused the re-injection. Seeds 7, 11, 23; 9 devices;
14 attacks; 282 runs (AI attacks on the AI-enabled device only). Command:
`python benchmarks/attack_simulation_eval.py --template hospital_ward --seeds 7,11,23`.

| Attack | Exploitable / absent | Detected | Mean ΔS | Status worsened | Mitigation restores | Re-injection blocked |
|---|---|---|---|---|---|---|
| hndl_capture | 18 / 9 | 17 % (100 % already flagged at baseline) | +3.3 | 17 % | 100 % | 100 % |
| tls_downgrade | 27 / 0 | 100 % | +39.9 | 44 % | 100 % | 100 % |
| pq_strip | 9 / 18 | 100 % | +36.3 | 100 % | 100 % | 100 % |
| cert_spoof | 21 / 6 | 100 % | +15.0 | 29 % | 100 % | 100 % |
| syn_flood, ddos_volumetric | 27 / 0 each | 100 % | 0 | 44 % | 100 % | 100 % |
| port_scan, mqtt_malformed, arp_spoofing | 27 / 0 each | 100 % | 0 | 22 % | 100 % | 100 % |
| prompt_injection, pq_downgrade_prompt, phi_leak, unsafe_command | 3 / 0 each | 100 % | 0 | 100 % | 100 % | 100 % |
| secret_leak | 27 / 0 | 100 % | +10.0 | 44 % | 100 % | 100 % |

Totals: 249 exploitable runs, 234 detected, 15 undetected (all harvest-now-decrypt-later captures on legacy devices
whose critical long-lifetime finding already existed at baseline, so the capture added no new finding), 249 re-injections
blocked. The PQ risk score is cryptography-only by design, so network, AI and identity attacks change the environment
status and pillar scores rather than S. "Status worsened" is below 100 % for most attacks because many legacy devices
are already UNSAFE at baseline. Kill chain (ICU Q-Day drill on ECG-ICU-007, seed 7): fleet mean S 31.0 → 35.2 and
UNSAFE devices 5 → 7 over capture / weaken / Q-Day / AI steps; after the catalogue mitigations 0.0 and 0 — a
configuration-consistency result, not evidence of real-world protection. The 33 non-exploitable runs are attacks whose
precondition is absent on PQ-ready devices (e.g. HNDL capture against ML-KEM key exchange).

## E12. Standards traceability — supplementary, not reported in the paper

`GET /api/v1/standards-map` and [`docs/release-3/standards_mapping.md`](../docs/release-3/standards_mapping.md)
(generated by `scripts/gen_standards_map_doc.py`): 42 finding types → TIPPSS pillars → pillar deduction → PQ-score
category and weight → public references. Pillar level only; IEEE/UL 2933-2024 clause numbers are not public.

No comparison with other tools has been made.
