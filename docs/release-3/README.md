# SafeGuard-PQ Release 3 (v0.3.0): Evidence for the Revised Manuscript

**Purpose.** This document collects, for every point raised by the two reviewers, what the software now contains,
where the evidence is, and what remains a limitation. It is written so that its tables, formulas and figures can be
transferred into the revised paper and the point-by-point response letters without re-deriving any number. All
numbers are read from the machine-readable artifacts in `benchmarks/results/` and are reproducible with one command
each ([Section 12](#12-reproduction-commands)).

| Item | Value |
|---|---|
| Software | PostQuantumSafe IoT Cybersecurity (SafeGuard-PQ) v0.3.0, branch `feat/research-results-dashboard` |
| Date of all new artifacts | 2026-11-22 (Python 3.13.5, Windows 11) |
| Evidence folder | `docs/release-3/` (this file, `threat_model.md`, `formulas.md`, `deployment_feasibility.md`, `standards_mapping.md`, `figures/`) |
| Web application | Research Results tab (`/#results`): one section per experiment, reading the same artifacts |
| Archiving | tag `v0.3.0` and the GitHub release create the Zenodo version DOI; the paper should cite that DOI (concept DOI 10.5281/zenodo.23618135) |

**Claim boundary.** The evidence supports statements about the behaviour of the software on synthetic configurations,
synthetic optimisation instances and the CICIoMT2024 test captures. It does not support claims of real-world
protection, clinical safety, standards conformance or calibrated risk. Section 14 states these limits.

---

## 1. Summary of what Release 3 adds

| Experiment | Reviewer request addressed | Headline result | Artifact |
|---|---|---|---|
| E7 Scoring sensitivity | R1 #3, R2 #3 | status never changes under ±20 % weight / point / deduction perturbations (Spearman ρ = 1.0); verdict flips in ≤ 4/10 scenarios (severity points); lifetime threshold L changes one status at 5 y and two verdicts at 20 y | `sensitivity_analysis.json` |
| E8 Optimizer scalability vs ILP | R1 #4, R2 #4 | shipped planner within 0.30 % (n = 20) to 0.055 % (n = 200) mean gap of the HiGHS optimum; annealing adds nothing beyond greedy for n ≥ 50; MIP exact and up to 15× faster at n = 200 | `qiro_scalability.json` |
| E9 Plan evaluation by reassessment, shared-root-cause planner | R1 #5, R2 #1 | reassessed S and status for all ten systems; projected vs reassessed differ by 9.3 points on average (shipped planner) and 2.7 (root-cause planner); worked-example plan best by reassessment but not cheapest | `plan_reassessment.json` |
| E10 Held-out traffic evaluation | R1 #6, R2 #2 | on windows not used for threshold selection F1 = 0.985–0.987 with FPR ≤ 2.7 %; a packet-size baseline matches this F1 on the flood-dominated split; small classes have wide intervals | `traffic_rules_holdout*.json` |
| E11 Attack simulation | R2 #5 (configuration-level claims) | 234/249 exploitable attack runs produce a new finding from the expected agent; every re-injection after mitigation blocked by the simulator model; passive capture is invisible when the exposure is already flagged | `attack_simulation.json` |
| E12 Standards traceability | R2 #6 | 42 finding types → pillar → deduction → score category → public reference, served by the API and documented | `standards_mapping.md`, `GET /api/v1/standards-map` |
| Threat model, formulas, deployment feasibility | R1 #7, R2 #4, #7 | explicit adversary model; every formula transcribed from code; published PQC size and Cortex-M4 cost figures | `threat_model.md`, `formulas.md`, `deployment_feasibility.md` |

---

## 2. Point-by-point status for Reviewer 1

| # | Request | Release 3 status | Evidence | Suggested response text |
|---|---|---|---|---|
| 1 | Structured comparison with existing PQ-readiness, cryptographic-inventory and remediation-planning approaches | *Partly in software.* The repository documents the technical differences ([docs/novelty.md](../novelty.md)); concrete citations for the comparison table are a manuscript task. | `docs/novelty.md` | "Section II now compares … (cite named works per row)." |
| 2 | Validation in realistic clinical environments; independently built configurations | **Not done.** The ten configurations remain hand-written synthetic scenarios. Release 3 adds a simulated hospital ward (9 devices) and attack injection (E11), which is still synthetic. | `backend/src/safeguard_pq/data/scenarios.json`; E11 | "We acknowledge this limitation (Section VIII). The scenarios are synthetic; Release 3 adds a simulated ward and attack injection but no observed deployment." |
| 3 | Justify weights and deductions; sensitivity; ten-year rule | **Done.** Rationale in `formulas.md` §2–4 (design choices, not calibrated); E7 reports five designs with verdict / status / score / rank / plan metrics; L is now an explicit assumption (`assumptions.lifetime_threshold_years`) and swept over 5–20 y. | Table 2, Fig. 5, `sensitivity_analysis.json` | "Sensitivity experiments (Table 2) show that the environment status is invariant to ±20 % changes …; the four-level verdict changes only where a score lies within one severity step of a threshold." |
| 4 | Larger portfolios; comparison with integer programming and other techniques | **Done.** E8: n = 20, 50, 100, 200 (50 instances each) against HiGHS (proven optima, cross-checked on 100 small instances), with greedy-only, greedy + local search and greedy + annealing baselines and runtime. | Table 1, Fig. 4, `qiro_scalability.json` | "Table 1 reports gaps to the ILP optimum up to n = 200; the MIP solver is exact and faster, so the heuristic's value is portability, not speed." |
| 5 | Projected vs actual remediation outcomes; root causes and dependencies | **Done.** Reassessment applies the plan to the configuration by code and re-runs the pipeline; a shared-root-cause planner mode (`group_shared_root_causes`) merges findings fixed by one mitigation; the one catalogue-grounded dependency (hybrid ML-KEM implies TLS 1.3) is modelled; all ten systems report summed benefit, projected S and reassessed S; plans are compared with every feasible subset. | Table 3, Fig. 6, `plan_reassessment.json`, `POST /assessments/{id}/reassess` | "Table 3 reports summed benefit, projected and reassessed scores for every system; the projection error falls from 9.3 to 2.7 points with the root-cause planner. The worked-example plan remains best by reassessment but is not the cheapest plan attaining it." |
| 6 | Separate development and held-out data; precision, recall, F1 | **Done with a caveat.** E10 implements capture-level, cross-source and temporal protocols with bootstrap and Wilson intervals and three baselines. The CICIoMT2024 train split was not available, so the capture-level protocol could not be run; P1 and P2 use the test split only. | Table 4, Figs. 7–8, `traffic_rules_holdout_cic_p1.json`, `_p2.json` | "Table 4 reports held-out precision / recall / F1 with 95 % intervals under two protocols; on this flood-dominated split a packet-size baseline matches the rules' F1, so we claim low false-positive rate and attack-type attribution, not detection superiority." |
| 7 | Clinical deployment feasibility | **Discussed from published figures; no measurements.** Object sizes (ML-KEM-768 1 184 B key / 1 088 B ciphertext; ML-DSA-65 1 952 B key / 3 309 B signature), Cortex-M4 cycle and stack figures (pqm4), gateway pattern, certificate lifecycle, downtime placeholders. | `deployment_feasibility.md` | "Section VII-F discusses compatibility, overhead, memory, certificate lifecycle and downtime using published measurements; no device measurements were performed in this work." |
| 8 | Reproducibility; affiliations; figure readability | **Software side done.** Scenario generation, instance distributions, costs, versions, seeds and one command per experiment are documented; result figures are redrawn at printed width with ≥ 6.5 pt text as vector SVG/PDF; the two schematic figures still need simplification (Section 13). Affiliation and header placeholders are manuscript tasks. | `formulas.md` §9–10, `docs/reproducibility.md`, `figures/` | "All experiments are reproducible with the listed commands and seeds (Appendix); figures were re-exported as vector graphics." |

## 3. Point-by-point status for Reviewer 2

| # | Request | Release 3 status | Evidence | Suggested response text |
|---|---|---|---|---|
| 1 | Reconcile the planner's objective with remediation effects; shared root causes; report summed benefit, projected and reassessed S for every system; is the worked-example plan still best? | **Done.** See R1 #5. Shared root causes: actions with the same mitigation are one decision unit costed once; dependency hybrid ML-KEM → TLS 1.3 recorded. Worked example: plan A reassessed 0 / SAFE (best), cost 98 k vs 58 k for the cheapest subset reaching it; plan B 88 k, projection exact. | Table 3 | as R1 #5 |
| 2 | Traffic rules on data not used for threshold choice; window construction; no overlap; uncertainty for 17-window classes; baseline | **Done with a caveat** (train split unavailable). Windows: consecutive, non-overlapping, 100 rows, never spanning files; whole captures per partition in P1; temporal halves in P2. Wilson intervals for the 17-window classes; bootstrap intervals for P/R/F1; majority-class, rate and packet-size baselines. | Table 4 | as R1 #6 |
| 3 | Separate Mosca's inequality from the ten-year override; test weights, deductions, lifetime threshold; define SAFE from the evidence | **Done.** M and P are defined and reported separately (`formulas.md` §4; `pq_posture.mosca`); sensitivity in E7; SAFE is one rule (`formulas.md` §3): no finding of severity ≥ medium on the supplied evidence and S ≤ 25; no cryptographic configuration ⇒ never SAFE. | `formulas.md`, Table 2 | "SAFE is defined as … (Eq. X); Mosca's test M and the lifetime override P are reported independently in Table II." |
| 4 | Instance-generation distributions, constraint tightness, gap formula; greedy / local-search / IP baselines on larger instances; Ising/QUBO formulation or drop "quantum-inspired" | **Done.** Distributions and tightness τ in `formulas.md` §9 and E8; gap formula §7; baselines in E8. The energy actually minimised is linear with an inactive penalty (§6); **we recommend describing the method as simulated annealing with local-search polish and not claiming a QUBO formulation.** | Table 1, `formulas.md` §6–9 | "We no longer describe QIRO as quantum-inspired; it is simulated annealing with a deterministic local search (Eq. Y)." |
| 5 | Keep claims at configuration level; abstract, result labels, conclusion; or add an emulated TLS test | **Done at software level.** Reassessment is labelled a configuration-consistency check everywhere (UI, docs, artifacts); E11 measures attack *preconditions* and the simulator's mitigation model; no emulated TLS handshake test was added. | E9, E11, `threat_model.md` | "All results are configuration-level; Table III columns are renamed 'configuration condition' / 're-assessed status'; the abstract no longer states that exposure is removed." |
| 6 | Integration contribution; traceable mapping findings → pillar deductions → IEEE/UL 2933 requirements; no compliance claim | **Done at pillar level.** 42-row mapping with deduction, score category / weight and public references; clause numbers of IEEE/UL 2933-2024 are not public and are left to be filled from the licensed text; an explicit no-conformance statement accompanies the table. | `standards_mapping.md`, `GET /api/v1/standards-map` | "Table Z maps every finding type to its pillar, deduction and reference; pillar scores do not imply conformance." |
| 7 | Enlarge figure text; complete affiliation; full benefit formula and rounding; versions and commands for E1–E6 | **Software side done.** `B_i` with all constants and half-up rounding (`formulas.md` §5); versions and commands (`docs/reproducibility.md`); vector figures. Affiliation is a manuscript task. | `formulas.md` §5, §10 | "The benefit B_i is given in Eq. W with the rounding rule; one command per experiment is listed in Appendix A." |

---

## 4. Experimental design and threat model

*Figure 1* (`figures/fig1_evaluation_design.svg|pdf`) shows the inputs, the five-stage pipeline (detection, scoring,
planning, explanation, reassessment), the experiments E1–E12 with the stage each one exercises, the data sources and
the claim boundary. *Figure 2* (`figures/fig2_threat_model.svg|pdf`) shows the adversaries A1–A6, the simulated
attacks, the observable precondition each agent checks, the detecting agent and the catalogue mitigation, and the
measurement loop of E11. The written threat model is [threat_model.md](threat_model.md).

---

## 5. Optimizer: quality on small instances (E3) and scalability against an ILP reference (E8)

**Table 1.** Gap of the planner to the optimum. E3: 500 synthetic instances, n ∈ [3, 14], exhaustive optimum. E8: 50
instances per size, τ ∈ {0.25, 0.5, 0.75}, HiGHS 1.16.0 optimum (proven; 100/100 agreement with the exhaustive solver
on n ≤ 14). Gap = 100 (f* − f) / f*; "optimal" = gap ≤ 10⁻⁹.

| n | Method | Optimal share | Mean gap | p95 gap | Max gap | Mean runtime |
|---|---|---|---|---|---|---|
| 3–14 (E3) | annealing only | 94.8 % | 0.19 % | 0.16 % | 20.16 % | — |
| 3–14 (E3) | annealing + local search (shipped) | 97.6 % | 0.053 % | 0.000 % | 6.06 % | 8.6 ms incl. exhaustive solver |
| 20 | greedy only | 40 % | 1.19 % | 3.37 % | 5.00 % | < 0.1 ms |
| 20 | greedy + local search | 74 % | 0.36 % | 1.88 % | 3.13 % | 0.8 ms |
| 20 | shipped | 76 % | 0.30 % | 1.67 % | 3.04 % | 17 ms (ILP 16 ms) |
| 50 | greedy only | 28 % | 0.43 % | 1.22 % | 1.82 % | < 0.2 ms |
| 50 | shipped | 46 % | 0.20 % | 0.77 % | 1.05 % | 67 ms (ILP 24 ms) |
| 100 | greedy only | 10 % | 0.29 % | 0.71 % | 1.17 % | < 0.2 ms |
| 100 | shipped | 32 % | 0.089 % | 0.27 % | 0.36 % | 190 ms (ILP 41 ms) |
| 200 | greedy only | 10 % | 0.16 % | 0.48 % | 0.62 % | < 0.2 ms |
| 200 | shipped | 28 % | 0.055 % | 0.16 % | 0.28 % | 811 ms (ILP 54 ms) |

Greedy + annealing equals greedy only for n ≥ 50 (annealing improved 7 of 200 instances, all at n = 20). Tight
budgets (τ = 0.25) give the largest gaps (shipped mean 0.20 % vs 0.14 % at τ = 0.5). *Figure 3*
(`fig_e3_optimizer_small_n`) and *Figure 4* (`fig_e8_scalability`).

**Statement for the paper.** "The planner reaches the exact optimum on 97.6 % of 500 small instances (mean optimality
gap 0.053 %) and stays within a mean gap of 0.30 % (n = 20) to 0.055 % (n = 200) of the integer-programming optimum
on larger portfolios. The local-search polish, not the annealing stage, accounts for this quality; an off-the-shelf
MIP solver is exact and faster at these sizes." (This replaces the incorrect sentence "using on average 0.053 % of the
optimum number of candidate actions".)

---

## 6. Sensitivity of the scoring model (E7)

**Table 2.** Ten scenarios, seed 2026. Verdict = four levels; status = SAFE / AT_RISK / UNSAFE; ρ = Spearman rank
correlation of the PQ-score ranking; Jaccard = similarity of selected-action sets where plans were recomputed.

| Design | Perturbation | Verdict changes | Status changes | Mean \|ΔS\| | Max \|ΔS\| | ρ | Plan Jaccard |
|---|---|---|---|---|---|---|---|
| S1 | one category weight ×0.8 / ×1.2, renormalised (12 configurations) | 0/10 in 8 configurations; 1/10 in 4 | 0/10 | ≤ 1.3 | 4 | 1.000 | n/a |
| S2 | severity points ×0.8 | 4/10 | 0/10 | 5.8 | 17 | 1.000 | n/a |
| S2 | severity points ×1.2 | 2/10 | 0/10 | 6.1 | 17 | 1.000 | n/a |
| S3 | pillar deductions ×0.8 / ×1.2 | 0/10 | 0/10 | pillar scores: 4.8 / 4.5 (max 17 / 15); weakest pillar unchanged | — | 1.000 | n/a |
| S4 | L = 5 y | 0/10 | 1/10 (`ehr_tls13_classical`, 26 → 46, AT_RISK → UNSAFE) | 2.0 | 20 | 0.997 | 0.95 |
| S4 | L = 15 y | 0/10 | 0/10 | 0 | 0 | 1.000 | 1.00 |
| S4 | L = 20 y | 2/10 (61 → 41) | 0/10 | 6.0 | 20 | 0.997 | 0.88 |
| S5 | optimizer pillar weights ×0.8 / ×1.2 | — | — | — | — | — | 1.00 (plans identical 10/10) |

The verdict changes under S2 are threshold crossings of scores at 23, 26, 46, 61 and 89; the environment status is
driven by the presence of critical and elevated findings and is therefore invariant to the constants. *Figure 5*
(`fig_e7_sensitivity`).

---

## 7. Plan evaluation by reassessment (E9)

**Table 3.** For each system: candidate actions n; baseline S and status; plan A (shipped planner, independent
actions) and plan B (shared-root-cause planner) with cost, summed benefit ΣB, projected S_proj, reassessed S_reass and
status; best reassessed S over all feasible subsets (730 pipeline runs in total); whether plan A is best / cheapest-best.

| System | n | Baseline | Plan A: cost / ΣB / S_proj → S_reass / status | Plan B: cost / ΣB / S_proj → S_reass / status | Best S (independent) | Plan A best / cheapest |
|---|---|---|---|---|---|---|
| icu_gateway_critical | 8 | 61 UNSAFE | 98 000 / 436 / 26 → 0 / SAFE | 88 000 / 691 / 0 → 0 / SAFE | 0 (cheapest 58 000) | yes / no |
| nextgen_pq_safe | 0 | 0 SAFE | — | — | 0 | yes / yes |
| ehr_tls13_classical | 5 | 26 AT_RISK | 95 000 / 250 / 26 → 0 / SAFE | 70 000 / 402 / 0 → 0 / SAFE | 0 | yes / no |
| clinical_ai_phi | 4 | 0 UNSAFE | 30 000 / 255 / 0 → 0 / SAFE | 16 000 / 255 / 0 → 0 / SAFE | 0 | yes / no |
| secret_exposure | 2 | 10 UNSAFE | 10 000 / 130 / 0 → 0 / SAFE | 5 000 / 130 / 0 → 0 / SAFE | 0 | yes / no |
| legacy_worst_case | 9 | 89 UNSAFE | 97 000 / 415 / 46 → 43 / UNSAFE | 80 000 / 599 / 54 → 30 / UNSAFE | 0 (72 000) | no / no |
| tight_budget_qiro | 8 | 61 UNSAFE | 18 000 / 189 / 58 → 46 / UNSAFE | 30 000 / 227 / 46 → 43 / UNSAFE | 38 | no / no |
| pq_downgrade_prompt | 2 | 0 UNSAFE | 18 000 / 154 / 0 → 0 / SAFE | 10 000 / 154 / 0 → 0 / SAFE | 0 | yes / no |
| hybrid_transition | 2 | 23 AT_RISK | 70 000 / 175 / 0 → 0 / SAFE | 70 000 / 175 / 0 → 0 / SAFE | 0 | yes / no |
| infusion_syn_flood | 6 | 46 UNSAFE | 77 000 / 299 / 26 → 0 / UNSAFE | 82 000 / 554 / 0 → 0 / UNSAFE | 0 (status UNSAFE) | yes / no |

Summary: plan A reaches SAFE in 7/10 systems; projected = reassessed in 5/10; mean |S_proj − S_reass| 9.3 (max 26).
Plan B: SAFE 7/10; projected = reassessed in 8/10; mean 2.7 (max 24); cheaper in every multi-action system except
`tight_budget_qiro` and `infusion_syn_flood`. The projection is pessimistic where several findings share one mitigation
(the ICU gateway's deferred actions share `enable_hybrid_mlkem` and `pq_certificates` with selected ones) and
optimistic where a mitigation is not verifiable at configuration level (`rate_limiting`: the SYN-flood finding
remains, so the system stays UNSAFE at S = 0). `legacy_worst_case` shows that maximising summed benefit is not the same
as maximising the reassessed outcome: a 72 000 USD subset reaches 0 / SAFE but neither planner selects it.
*Figure 6* (`fig_e9_reassessment`).

**Why a score of 0 is not guaranteed by construction.** The "after" configuration is produced by code from the plan
(`optimizer/reassess.py`), not edited by hand; three of ten systems do not reach 0 / SAFE, and the exhaustive check
shows which subsets would.

---

## 8. Traffic rules: same-split behaviour (E6) and held-out evaluation (E10)

**Table 4.** Window-level attack-versus-benign metrics on held-out windows (100-row non-overlapping windows; 95 %
bootstrap intervals in brackets, 1000 resamples). P1: thresholds selected on the synthetic development set
(120 windows), evaluated once on the CICIoMT2024 test split (3 446 windows); the development set confirmed every
shipped threshold. P2: first half of each test capture's windows for development (1 721), last half held out (1 725);
four of five rules changed. Baselines are fitted on the development windows only.

| Protocol | Predictor | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|
| P1 | rules, tuned on development set | 0.997 [0.995, 0.999] | 0.973 [0.967, 0.978] | 0.985 [0.982, 0.987] | 0.027 [0.011, 0.044] |
| P1 | baseline: majority class | 0.891 | 1.000 | 0.942 | 1.000 |
| P1 | baseline: mean Rate > benign p99 | 0.927 | 0.241 | 0.382 | 0.154 |
| P1 | baseline: packet size outside benign p1–p99 | 0.906 | 1.000 | 0.951 | 0.848 |
| P2 | rules, shipped (not held-out) | 0.999 | 0.967 | 0.983 | 0.011 |
| P2 | rules, tuned on development half | 1.000 [1.000, 1.000] | 0.973 [0.965, 0.981] | 0.987 [0.982, 0.991] | 0.000 [0.000, 0.000] |
| P2 | baseline: majority class | 0.891 | 1.000 | 0.942 | 1.000 |
| P2 | baseline: mean Rate > benign p99 | 0.995 | 0.130 | 0.229 | 0.005 |
| P2 | baseline: packet size outside benign p1–p99 | 1.000 | 0.978 | 0.989 | 0.000 |

Per-class held-out detection with Wilson 95 % intervals (P2, tuned): DDoS-TCP 96.5 % [95.1, 97.5] (n = 913), DoS-SYN
100 % [99.2, 100] (493), port scan 96.5 % [91.2, 98.6] (113), MQTT malformed 88.9 % [56.5, 98.0] (9), ARP spoofing
55.6 % [26.7, 81.1] (9); benign false-positive rate 0 % [0, 2.0] (188). P1 per-class rates equal the E6 same-split
rates (Table in `benchmarks/README.md`) now with intervals: ARP 88.2 % [65.7, 96.7], MQTT 76.5 % [52.7, 90.4].

Interpretation for the paper: the rules keep F1 ≈ 0.98 and FPR ≤ 2.7 % on windows not used for threshold selection,
but the CICIoMT2024 test split is 89 % attack windows dominated by small-packet floods, so a packet-size band
baseline matches the rules' F1 (0.951 / 0.989) and the majority-class baseline reaches 0.942. The rules' contribution
is therefore the low false-positive rate and the attribution of a window to an attack type (the designated rule fires
on 84.5 % / 90.3 % of port-scan windows), not window-level F1. The two small classes remain uncertain. The CICIoMT2024
train split was not available; the capture-level protocol is implemented and awaits it. *Figures 7–8*
(`fig_e6_traffic_same_split`, `fig_e10_traffic_holdout`).

---

## 9. Attack simulation on the hospital ward (E11)

**Table 5.** 14 attacks × 9 devices × 3 seeds (AI attacks on the AI-enabled device only) = 282 runs; 249 with the
precondition present. "Detected" = new finding from the agent named in the catalogue for the attack; "restores" =
status after the catalogue mitigation ≤ baseline; "blocked" = the simulator refuses re-injection after mitigation.

| Attack | Exploitable / absent | Detected | Mean ΔS | Status worsened | Restores | Blocked |
|---|---|---|---|---|---|---|
| hndl_capture | 18 / 9 | 17 % (100 % already flagged at baseline) | +3.3 | 17 % | 100 % | 100 % |
| tls_downgrade | 27 / 0 | 100 % | +39.9 | 44 % | 100 % | 100 % |
| pq_strip | 9 / 18 | 100 % | +36.3 | 100 % | 100 % | 100 % |
| cert_spoof | 21 / 6 | 100 % | +15.0 | 29 % | 100 % | 100 % |
| syn_flood; ddos_volumetric | 27 / 0 each | 100 % | 0 | 44 % | 100 % | 100 % |
| port_scan; mqtt_malformed; arp_spoofing | 27 / 0 each | 100 % | 0 | 22 % | 100 % | 100 % |
| prompt_injection; pq_downgrade_prompt; phi_leak; unsafe_command | 3 / 0 each | 100 % | 0 | 100 % | 100 % | 100 % |
| secret_leak | 27 / 0 | 100 % | +10.0 | 44 % | 100 % | 100 % |

Findings: (i) passive harvest-now-decrypt-later capture leaves no telemetry trace; the framework reports the
*exposure*, which is already present at baseline on the five legacy devices — the only new finding appears on the
EHR gateway whose lifetime the capture extends from 8 to 25 years; (ii) ΔS = 0 for network, AI and identity attacks
because S is cryptography-only by design; they change pillar scores (minimum pillar −8 to −70 points), environment
status and the simulator's live risk; (iii) "blocked" is tautological in the simulator (a mitigation in `blocked_by`
refuses re-injection) and must not be read as adversary behaviour. Kill chain (ICU Q-Day drill, seed 7): fleet mean S
31.0 → 35.2 and UNSAFE devices 5 → 7 across capture, weaken (PACS 23 → 46), Q-Day (ECG 46 → 61), AI steps; after
the fleet-wide mitigations 0.0 and 0, a configuration-consistency result. *Figure 9* (`fig_e11_attack_simulation`).

---

## 10. Standards traceability (E12)

[standards_mapping.md](standards_mapping.md) lists all 42 finding types with agent, severity, TIPPSS pillars, pillar
deduction, score category and weight, rationale, public references (NIST FIPS 203/204, NIST IR 8547, NIST SP 800-52r2
and SP 800-131Ar2, RFC 8996, HIPAA 45 CFR 164.312 and 164.514(b)(2), OWASP Top 10 for LLM applications, FDA premarket
cybersecurity guidance, MITRE CWE/ATT&CK identifiers, the CICIoMT2024 dataset paper) and, where one exists, an attack
technique identifier. Every pillar is covered by at least five finding types. IEEE/UL 2933-2024 is cited by title and
date only; its clause numbers are not public, and the mapping must not be presented as conformance.

---

## 11. Definitions and formulas for the manuscript

[formulas.md](formulas.md) transcribes from the code: pillar scores; PQ risk score with the weights, severity points
and half-up rounding; the single SAFE rule; Mosca's test M and the lifetime override P; the benefit B_i with all
constants; the optimisation problem and the energy actually minimised (linear, inactive penalty — hence the
recommendation to drop "quantum-inspired"); the gap formula; projected and reassessed scores; the instance generators
and catalogue ranges; software versions. Manuscript corrections implied by this document: replace "0.053 % of the
optimum number of candidate actions" and "mean absolute error of only 0.053 %" by "mean optimality gap 0.053 %"; fix
the weight sentence ("… are weighted lower than classical public-key crypto (0.30) and TLS (0.20)"); state the seeds
once (assessments 2026, instance generator 0); use the SAFE rule of `formulas.md` §3; use one planner name.

---

## 12. Reproduction commands

See [docs/reproducibility.md](../reproducibility.md): one command per experiment, seeds, expected outputs and
`cd backend && ruff check src tests && pytest` (216 tests) / `cd frontend && npx playwright test` (12 browser tests).

---

## 13. Figures

Result figures 3–9 are drawn by `benchmarks/make_figures.py` at their printed width (single column 3.5 in, double
column 7.16 in) with 7–8 pt text and no text below 6.5 pt, without in-figure titles (the captions below carry them),
and exported as vector SVG and PDF with embedded TrueType fonts plus 300-dpi PNG. Figures 1–2 are schematic drafts
drawn at 14.6 in: at a 7.16-in two-column width their smallest text falls to about 4–5 pt, so they must be simplified
or set as full-page figures before submission.

| Figure | File | Printed width | Caption |
|---|---|---|---|
| 1 | `figures/fig1_evaluation_design` | full page (draft) | Evaluation design: inputs, five-stage pipeline, experiments E1–E12, data and claim boundary. |
| 2 | `figures/fig2_threat_model` | full page (draft) | Threat model: adversaries, simulated attacks, observable preconditions, detectors and mitigations; E11 measurement loop. |
| 3 | `figures/fig_e3_optimizer_small_n` | 2-column | E3: share of 500 small instances solved optimally and gap distribution for annealing alone and with local search. |
| 4 | `figures/fig_e8_scalability` | 2-column | E8: optimal share, mean and maximum gap to the HiGHS optimum, and runtime for n = 20–200. |
| 5 | `figures/fig_e7_sensitivity` | 2-column | E7: max |ΔS| and share of systems whose verdict / status changes per perturbation; PQ score vs lifetime threshold per scenario. |
| 6 | `figures/fig_e9_reassessment` | 2-column | E9: baseline, projected and reassessed PQ score per system for both planners; status after plan A. |
| 7 | `figures/fig_e6_traffic_same_split` | 1-column | E6: window flag rates on the CICIoMT2024 test split with Wilson intervals (same split as threshold selection). |
| 8 | `figures/fig_e10_traffic_holdout` | 2-column | E10: held-out precision / recall / F1 with bootstrap intervals for the rules and three baselines under three protocols. |
| 9 | `figures/fig_e11_attack_simulation` | 2-column | E11: outcome per attack (detected, flagged, restored, blocked) and the ICU Q-Day drill trajectory. |

---

## 14. Limitations that remain after Release 3

- No independently built or observed clinical configurations (R1 #2); no comparison with other tools or expert plans.
- Scoring constants are design choices; the sensitivity analysis bounds, but does not calibrate, their effect.
- The CICIoMT2024 train split was not available; held-out results rest on the test split under two weaker protocols.
- Reassessment and attack simulation are configuration-level; network mitigations are unmodelled; "blocked" reflects
  the simulator's own model.
- Standards mapping is at pillar level; no conformance claim.
- No device measurements; deployment figures are third-party.

Full list: [docs/limitations.md](../limitations.md).
