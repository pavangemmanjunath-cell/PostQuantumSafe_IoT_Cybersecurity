# Limitations

Updated for Release 3 (v0.3.0). Items marked *measured* are quantified in [docs/release-3/README.md](release-3/README.md).

## Scientific limitations
- The PQ risk score's weights, severity points and pillar deductions are design choices inherited from the prototype,
  not calibrated on incident data. *Measured (E7):* the SAFE / AT_RISK / UNSAFE status of the ten scenarios never
  changes under ±20 % perturbations of the weights, points or deductions, but the four-level verdict changes in up to
  4 of 10 scenarios when the severity points are scaled, because several scores sit close to the 25 / 50 / 75
  thresholds. Verdicts near a threshold should be read with that in mind.
- The ten-year lifetime rule is a policy choice. *Measured (E7):* lowering it to 5 years changes the status of one
  scenario; raising it to 20 years changes the verdict of two.
- Mosca's inequality depends on a single, highly uncertain CRQC-arrival assumption supplied by the user.
- No comparative evaluation against other tools or expert-produced plans exists. The only external reference is an
  integer-programming solver for the planning objective (E8).
- The planner's objective is a proxy. *Measured (E9):* the projected score assumes each action removes only its own
  finding and differs from the reassessed score by 9.3 points on average (max 26) with the shipped planner; the
  shared-root-cause planner reduces this to 2.7, and in 3 of 10 scenarios the shipped plan is not the best plan by
  reassessment or not the cheapest plan attaining it.
- "Quantum-inspired" describes the history of the optimiser, not its mathematics: the energy that is minimised is a
  linear objective under two knapsack constraints, and simulated annealing contributes almost nothing beyond the
  greedy start at n ≥ 50 (E8). An off-the-shelf MIP solver is exact and faster at n ≤ 200.

## Data limitations
- All bundled data is synthetic. The ten scenarios are hand-written; they are not observed clinical deployments and
  were not built independently from clinical devices.
- The traffic rules' shipped thresholds were set on the CICIoMT2024 test split. *Measured (E10):* on windows not used
  for threshold selection the rules keep F1 ≈ 0.98 (cross-source and temporal protocols), but the CICIoMT2024 test
  split is 89 % attack windows and dominated by small-packet floods, so a trivial packet-size baseline reaches
  F1 ≈ 0.95 and the majority-class baseline ≈ 0.94; ARP spoofing and malformed MQTT have only 17 windows each (wide
  Wilson intervals). The CICIoMT2024 *train* split was not available, so no capture-level train/test evaluation
  exists.
- The synthetic held-out dataset (`datasets/synthetic_holdout`) was generated around the shipped rules; figures on it
  demonstrate the protocol only.
- Bootstrap intervals resample windows independently although consecutive windows of one capture are correlated;
  they are narrower than capture-level resampling would give.

## Model limitations
- Regex detectors miss paraphrases, other languages and obfuscation, and can flag benign text.
- The "ARP spoofing" rule detects a protocol-mix signature of that capture, not ARP spoofing as such.
- No trained ML model is included.
- Reassessment is a configuration-consistency check: it verifies that the remediated configuration satisfies the
  framework's own rules. It is not evidence that a mitigation stops a real attacker. Network mitigations (rate
  limiting, segmentation) have no configuration-level effect and are reported as *unmodelled*, so systems with traffic
  findings stay UNSAFE after reassessment (E9, `infusion_syn_flood`).
- Attack simulation (E11) exercises the simulator's own attack and mitigation models; a "detected" result means a rule
  fired on the simulated configuration or telemetry, and "blocked" reflects the simulator's `blocked_by` table.

## Generalisation limitations
- Device profiles, crypto defaults and remediation templates are illustrative, not vendor- or hospital-specific; costs,
  downtimes and complexities are placeholders.
- Traffic features assume CICIoMT2024 column semantics.
- The standards mapping is at pillar level: clause numbers of IEEE/UL 2933-2024 are not public and are not cited.
  Pillar scores do not imply conformance with the standard.

## Computational limitations
- The exhaustive optimum is computed only for ≤ 14 actions inside the product; the benchmark uses HiGHS as the
  reference for n = 20 to 200. The pure-Python local search is O(n²) per move and takes about 0.8 s at n = 200.
- Single-process, in-memory server.

## Security / privacy considerations
- No authentication; run locally only.
- Inputs may contain sensitive data if users supply real logs — redaction is pattern-based and not guaranteed complete.
  Use synthetic or de-identified data.
- Optional LLM and openFDA calls send data off-host (redacted aggregates / search terms only) and are off by default.

## Deployment limitations
- Not designed or tested for production, clinical or regulated environments.
- Assessments do not scan live systems; they evaluate supplied configuration.
- No device measurements (CPU, memory, energy, latency, downtime) were made; the deployment-feasibility discussion in
  [docs/release-3/deployment_feasibility.md](release-3/deployment_feasibility.md) relies on published third-party
  figures.

## Areas requiring further validation
- Capture-level train/test evaluation on the CICIoMT2024 train split and on other IoMT datasets; evaluation against
  adaptive adversaries who shape traffic to evade window-level thresholds.
- Configurations built from public device documentation or real scanner output, replacing the hand-written scenarios.
- Usefulness of explanations and plans with practitioners.
- Cost / downtime estimates from real migration projects; calibration of the scoring constants.
- Behaviour of the replay data source with full CICIoMT2024 files.
