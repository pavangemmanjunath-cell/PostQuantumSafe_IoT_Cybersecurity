# Benchmarks

Machine-readable results live in [`results/`](results/). Every number reported in the README comes from these files.

## 1. QIRO optimality (`qiro_optimality.py`)

| Item | Value |
|---|---|
| Objective | How close the shipped heuristic gets to the exact optimum of the same objective |
| Baselines | simulated annealing alone; exhaustive search (exact) |
| Dataset | 500 random synthetic instances: n ∈ [3, 14] actions drawn from the remediation catalogue, budgets {20k, 50k, 100k} USD, downtime {4, 10, 40} h |
| Metrics | share of instances solved optimally; mean / p95 / max relative gap |
| Command | `python benchmarks/qiro_optimality.py --instances 500 --seed 0` |
| Environment | Python 3.13.5, Windows 11, v0.1.0, 2026-10-24 |

| Method | Optimal | Mean gap | p95 gap | Max gap |
|---|---|---|---|---|
| Annealing only | 94.8 % | 0.19 % | 0.16 % | 20.16 % |
| Annealing + local search | 97.6 % | 0.05 % | 0.00 % | 6.06 % |

Mean run time per instance including the exhaustive solver: 6.76 ms.
Limitation: synthetic instances; exact solver limited to n ≤ 14.

## 2. Traffic rules (`traffic_rules_eval.py`)

| Item | Value |
|---|---|
| Objective | Window-level behaviour of the five transparent traffic rules |
| Dataset | CICIoMT2024 `WiFi_and_MQTT/attacks/CSV/test` (download separately; not redistributed) |
| Method | consecutive 100-row windows, up to 2000 per file; a window is flagged if any rule fires |
| Metrics | detection rate (attack files), false-positive rate (benign file) |
| Command | `python benchmarks/traffic_rules_eval.py --data-dir <folder> --window 100` |

| File | Windows | Flagged | Rate |
|---|---|---|---|
| Benign_test | 376 | 10 | 2.7 % (FPR) |
| ARP_Spoofing_test | 17 | 15 | 88.2 % |
| MQTT-Malformed_Data_test | 17 | 13 | 76.5 % |
| Recon-Port_Scan_test | 226 | 223 | 98.7 % |
| TCP_IP-DDoS-TCP_test | 1825 | 1750 | 95.9 % |
| TCP_IP-DoS-SYN_test | 985 | 985 | 100 % |

**Caveats:** thresholds were chosen by inspecting window statistics of this same split, so these figures are optimistic
and not an estimate of generalisation. The per-class rule mapping is not evaluated (a port-scan window flagged by the
SYN-flood rule counts as detected). Held-out evaluation on the train split is on the roadmap.

No comparison with other tools has been made.
