# Reproducibility Guide

## Supported environment

| Item | Tested |
|---|---|
| OS | Windows 11 (10.0.26200). Linux/macOS expected to work (CI runs Ubuntu) but not yet verified locally. |
| Python | 3.13.5 (requires ≥ 3.11) |
| Node.js / npm | 24.20.0 / 11.19.0 (requires Node ≥ 20) |
| Browser for E2E | Playwright Chromium (headless shell 156) with SwiftShader WebGL |
| Hardware | any laptop; no GPU needed |

## Installation

```bash
python -m venv backend/.venv
# activate it (Windows: backend\.venv\Scripts\activate, Linux/macOS: source backend/.venv/bin/activate)
pip install -e "backend[dev]"
pip install -e "backend[benchmark]"      # optional: ILP reference (highspy) and figure generation (matplotlib)
cd frontend && npm ci && npx playwright install chromium
```

Windows note: on very long repository paths `pip` can fail to install packages with deeply nested files (SciPy,
matplotlib's bundled fonts) unless Windows long-path support is enabled. The ILP reference uses `highspy`, which
installs on such paths; if matplotlib's fonts are missing, run `benchmarks/make_figures.py` with any other Python that
has matplotlib (the script needs only matplotlib and the JSON artifacts).

## Dependencies

Declared in `backend/pyproject.toml` (ranges) and `frontend/package.json` + `package-lock.json` (exact versions).
Versions used for the recorded results: FastAPI 0.143.3, Pydantic 2.14.1, ReportLab 5.0.1, Uvicorn 0.54.0,
highspy 1.16.0 (HiGHS 1.16.0), matplotlib 3.10/3.11, React 19.3.1, three 0.186.1, @react-three/fiber 9.8.2,
@react-three/drei 10.7.9, Vite 8.3.4, TypeScript 7.0.2, Playwright 1.64.1.

## Dataset preparation

Nothing is needed for tests, demos, the optimizer benchmarks (E3, E8), the sensitivity analysis (E7), the reassessment
benchmark (E9), the attack simulation (E11) or the synthetic held-out run of E10: all use bundled synthetic data.

For the CICIoMT2024 runs (E6, E10 protocols P1 and P2) download the `WiFi_and_MQTT/attacks/CSV/test` files yourself
from the Canadian Institute for Cybersecurity (registration form; see [datasets/README.md](../datasets/README.md))
into a folder of your choice. The train split enables the capture-level protocol (`--protocol capture_split`).

## Configuration

Defaults need no configuration. `.env.example` documents all options; the LLM must stay `none` to reproduce reports exactly.

## Random seeds

- QIRO: request field `seed`, default `QIRO_DEFAULT_SEED=2026`; assessments of the ten scenarios use 2026.
- Simulator: `seed` per simulation (default 7); E11 uses seeds 7, 11, 23.
- Benchmarks: `--seed` (instance generator; E3/E8 use 0, per-instance optimizer seed = instance index; E8 draws each
  size from `Random(f"{seed}-n{n}")`); bootstrap resampling seed 0 (E10); synthetic dataset seeds 101 (train) and 202
  (test).

## Reproduce core example

```bash
cd backend
safeguard-pq assess --scenario icu_gateway_critical --json result.json --pdf report.pdf
```
Expected: `environment UNSAFE | PQ score 61/100 (Not Post-Quantum Safe) | 8 finding(s) | QIRO 5 action(s)`.

## Reproduce experiments (one command each)

```bash
python benchmarks/qiro_optimality.py --instances 500 --seed 0                                   # E3
python benchmarks/traffic_rules_eval.py --data-dir <CIC test folder> --window 100              # E6 (same split)
python benchmarks/sensitivity_analysis.py --seed 2026                                            # E7
python benchmarks/qiro_scalability.py --sizes 20,50,100,200 --instances-per-size 50 --seed 0 --small-check 100   # E8 (~100 s)
python benchmarks/plan_reassessment.py --seed 2026 --exhaustive-max-n 10                         # E9
python benchmarks/make_synthetic_traffic_dataset.py --out datasets/synthetic_holdout --train-seed 101 --test-seed 202 --windows-per-class 20
python benchmarks/traffic_rules_holdout.py --train-dir datasets/synthetic_holdout/train --test-dir datasets/synthetic_holdout/test \
    --out benchmarks/results/traffic_rules_holdout.json                                           # E10 demonstration
python benchmarks/traffic_rules_holdout.py --protocol cross_source --train-dir datasets/synthetic_holdout/train \
    --test-dir <CIC test folder> --out benchmarks/results/traffic_rules_holdout_cic_p1.json        # E10 P1
python benchmarks/traffic_rules_holdout.py --protocol temporal_split --test-dir <CIC test folder> --dev-fraction 0.5 \
    --out benchmarks/results/traffic_rules_holdout_cic_p2.json                                    # E10 P2
python benchmarks/attack_simulation_eval.py --template hospital_ward --seeds 7,11,23              # E11
python scripts/gen_standards_map_doc.py                                                          # E12 table
python benchmarks/make_figures.py                                                                 # figures (SVG, PDF, PNG)
```

## Expected outputs

The committed artifacts in `benchmarks/results/` (see [benchmarks/README.md](../benchmarks/README.md) for the headline
numbers). Objective metrics, verdicts, scores, selections, detection counts and intervals are deterministic for the
stated seeds and Python version; the recorded `date`, runtimes and platform strings are machine-dependent. The
attack-simulation and synthetic-dataset outputs are byte-identical on re-run (no timestamps). The E10 CIC artifacts
depend on the downloaded files (window counts are listed in their manifests: 376 benign, 17 ARP, 17 MQTT, 226 port
scan, 1825 DDoS, 985 SYN).

## Evaluation commands

```bash
cd backend && ruff check src tests && pytest           # expected: 216 passed
cd frontend && npm run typecheck && npm run build && npx playwright test   # expected: 12 passed
```

## Troubleshooting

- **Port already in use:** E2E tests use ports 8765/5199 (override with `E2E_API_PORT`, `E2E_WEB_PORT`); the dev scripts
  accept `-ApiPort/-WebPort` (PowerShell) or positional ports (bash).
- **GUI shows "API offline":** start the backend and check the Vite proxy target (`SAFEGUARD_API`).
- **No WebGL in headless browsers:** Playwright is launched with SwiftShader flags in `playwright.config.ts`.
- **`highspy` missing:** `pip install -e "backend[benchmark]"`; the E8 script and its tests skip without it.

## Known sources of non-determinism

- Timestamps, assessment ids and per-agent timings.
- LLM narratives when an LLM provider is configured.
- Simulator state depends on the number of ticks elapsed (wall-clock stream); use `POST /simulations/{id}/step` for
  deterministic stepping (the benchmarks step explicitly).

## Reproducibility limitations

Results were produced on a single Windows machine; cross-platform floating-point differences in annealing acceptance are
possible but have not been observed. The traffic benchmarks require a third-party download that may change over time.
