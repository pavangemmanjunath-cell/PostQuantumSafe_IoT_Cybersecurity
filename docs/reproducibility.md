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

Nothing is needed for tests, demos, the paper experiments E1–E5, the optimizer benchmarks (E4, E8), the sensitivity
analysis (E7), the reassessment benchmark (E9), the attack simulation (E11) or the synthetic held-out run of E10:
all use bundled synthetic data.

For the CICIoMT2024 runs (E6, E10 protocols P1 and P2) download the `WiFi_and_MQTT/attacks/CSV/test` files yourself
from the Canadian Institute for Cybersecurity (registration form; see [datasets/README.md](../datasets/README.md))
into a folder of your choice. The train split enables the capture-level protocol (`--protocol capture_split`).

## Configuration

Defaults need no configuration. `.env.example` documents all options; the LLM must stay `none` to reproduce reports exactly.

## Random seeds

- QIRO: request field `seed`, default `QIRO_DEFAULT_SEED=2026`; assessments of the ten scenarios and the paper
  experiments E1–E5 (`paper_experiments.py --seed`) use 2026.
- Simulator: `seed` per simulation (default 7); E11 uses seeds 7, 11, 23.
- Benchmarks: `--seed` (instance generator; E4/E8 use 0, per-instance optimizer seed = instance index; E8 draws each
  size from `Random(f"{seed}-n{n}")`); bootstrap resampling seed 0 (E10); synthetic dataset seeds 101 (train) and 202
  (test).

## Reproduce core example

```bash
cd backend
safeguard-pq assess --scenario icu_gateway_critical --json result.json --pdf report.pdf
```
Expected: `environment UNSAFE | PQ score 61/100 (Not Post-Quantum Safe) | 8 finding(s) | QIRO 5 action(s)`.

## Reproduce everything (one command)

```bash
python benchmarks/run_all.py --cic-test-dir <CIC test folder> --figures-python <python with matplotlib> --check
```

`benchmarks/run_all.py` runs the paper experiments E1–E5 first and then every other command of the sections below in
that order, prints each command with its wall time and stops at the first failure (about 4 min, of which E8 takes
about 100 s). Without `--cic-test-dir`, E6 and E10
P1/P2 are skipped. `--figures-python` is the interpreter for `make_figures.py` (run in isolated mode `-I`; default:
the interpreter running `run_all.py`). `--skip-slow` leaves out E8, `--no-figures` and `--no-docx` the figure and Word
steps. `--check` then compares every regenerated file in `benchmarks/results/` and `datasets/synthetic_holdout/` with
the committed version (`git show HEAD:<path>`): JSON values are compared without the volatile fields (`date`,
`python`, `platform`, `machine`, `software_version`, `*_ms`, `runtime_s`, `total_runtime_s`,
`runtime_ratio_heuristic_over_ilp`, `mean_optimize_ms_including_exact_solver`), other files byte by byte with line
endings normalised. It prints a PASS / CHANGED table and exits with status 1 if a deterministic value changed.

On GitHub, the CI job `reproduce` (`.github/workflows/ci.yml`) runs
`python benchmarks/run_all.py --check --no-figures --no-docx` on ubuntu-latest with Python 3.13 and highspy 1.16.0 for every
push to `main` or a `feat/**` branch and every pull request, and uploads the regenerated results as the workflow
artifact `reproduced-results`. The CICIoMT2024 files are not redistributed, so there E6 and E10 P1/P2 are reported as
NOT RUN.

### Windows launcher

`start_all.bat` in the repository root wraps these commands in a menu (double-click it) or takes the option as an
argument, for example `start_all.bat pipeline`:

| Option | Argument | Runs |
|---|---|---|
| 1 | `app` | `scripts\dev.ps1`: backend on :8000 and frontend on :5173 (creates `backend\.venv` and installs the frontend packages on first run); Research Results tab at http://127.0.0.1:5173/#results |
| 2 | `pipeline` | `benchmarks\run_all.py --check`, with `--cic-test-dir ..\Input` when that folder exists and `--figures-python %USERPROFILE%\anaconda3\python.exe` when that interpreter exists (else the venv Python) |
| 3 | `pipeline-quick` | the same with `--skip-slow` (no E8) |
| 4 | `tests` | ruff (CI form and benchmarks/scripts), pytest, frontend type check, build and Playwright tests |
| 5 | `docs` | the result figures (`make_figures.py`), the schematic figure PDFs and the Word summary only |
| 0 | | exit |

Options 2–5 create `backend\.venv` with `pip install -e "backend[dev,benchmark]"` if it is missing. Every step
prints an OK / FAIL line with its exit code, and the launcher exits with the first failing code; it pauses at the
end only when started without an argument.

## Paper experiment → command → artifact

Experiment numbers are those of the revised journal paper (Section VI). Artifacts are in `benchmarks/results/` unless
a path is given. `python benchmarks/paper_experiments.py` runs E1–E5 together (a few seconds); every `paper_e*.json`
carries a `paper_check` block that lists each number the paper states for the experiment with the expected value,
the reproduced value and whether they match (all 215 match with v0.3.0).

| Paper experiment | Command | Artifact |
|---|---|---|
| E1 Ten synthetic systems: Table II and the principle scores of Section VII-A | `python benchmarks/paper_experiments.py --only e1` | `paper_e1_systems.json` |
| E2 Legacy infusion-pump gateway under six attack conditions, before and after the countermeasures | `python benchmarks/paper_experiments.py --only e2` (inputs: `examples/paper/e2_infusion_pump_conditions.json`) | `paper_e2_attack_conditions.json` |
| E3 Q-Day sweep: seven data classes (5–30 y), y = 2, 5, 8, z = 4–30 y, classical and hybrid ML-KEM | `python benchmarks/paper_experiments.py --only e3` | `paper_e3_qday_sweep.json` |
| E4 Budget sweep 10 000–200 000 USD, ICU gateway and legacy system | `python benchmarks/paper_experiments.py --only e4` | `paper_e4_budget_sweep.json` |
| E4 Solver quality: 500 random instances of 3–14 actions against exhaustive search (Table III, first row) | `python benchmarks/qiro_optimality.py --instances 500 --seed 0` | `qiro_optimality.json` |
| E5 Worked example of Section III: plan applied and re-assessed | `python benchmarks/paper_experiments.py --only e5` (input: `examples/paper/worked_example_gateway.json`) | `paper_e5_worked_example.json` |
| E6 Traffic rules on the CICIoMT2024 test split (same split) | `python benchmarks/traffic_rules_eval.py --data-dir <CIC test folder> --window 100` | `traffic_rules_eval.json` |
| E7 Sensitivity to the scoring constants and to L | `python benchmarks/sensitivity_analysis.py --seed 2026` | `sensitivity_analysis.json` |
| E8 ILP scalability, n = 20–200 | `python benchmarks/qiro_scalability.py --sizes 20,50,100,200 --instances-per-size 50 --seed 0 --small-check 100` | `qiro_scalability.json` |
| E9 Reassessment of every E1 system | `python benchmarks/plan_reassessment.py --seed 2026 --exhaustive-max-n 10` | `plan_reassessment.json` |
| E10 Held-out traffic rules | `python benchmarks/traffic_rules_holdout.py …` (synthetic demonstration, protocols P1 and P2; commands below) | `traffic_rules_holdout.json`, `traffic_rules_holdout_cic_p1.json`, `traffic_rules_holdout_cic_p2.json` |
| E11 Attack simulation — supplementary (not reported in the paper) | `python benchmarks/attack_simulation_eval.py --template hospital_ward --seeds 7,11,23` | `attack_simulation.json` |
| E12 Standards map — supplementary (not reported in the paper; its Discussion cites the table) | `python scripts/gen_standards_map_doc.py` | `docs/release-3/standards_mapping.md` |

The E2 and E3 inputs are not spelled out in the original draft; they are taken from the v0.1.0 experiment script
that produced its numbers, every E2 condition equals the effect of the simulator's attack injection
(`Simulation.inject`, re-checked on each run), and each artifact's `method` lists the assumptions. The worked example
of the paper is the Section III gateway (`examples/paper/worked_example_gateway.json`, Listing 1 of the original
draft), not the built-in ICU gateway scenario `icu_gateway_critical`.

## Reproduce experiments (one command each)

```bash
python benchmarks/paper_experiments.py                                                          # E1-E5 (--only e1,...)
python benchmarks/qiro_optimality.py --instances 500 --seed 0                                   # E4 solver quality
python benchmarks/traffic_rules_eval.py --data-dir <CIC test folder> --window 100              # E6 (same split)
python benchmarks/sensitivity_analysis.py --seed 2026                                            # E7
python benchmarks/qiro_scalability.py --sizes 20,50,100,200 --instances-per-size 50 --seed 0 --small-check 100   # E8 (~100 s)
python benchmarks/plan_reassessment.py --seed 2026 --exhaustive-max-n 10                         # E9
python benchmarks/make_synthetic_traffic_dataset.py --out datasets/synthetic_holdout --train-seed 101 --test-seed 202 --windows-per-class 20
python benchmarks/traffic_rules_holdout.py --train-dir datasets/synthetic_holdout/train --test-dir datasets/synthetic_holdout/test \
    --out benchmarks/results/traffic_rules_holdout.json                                           # E10 demonstration
python benchmarks/traffic_rules_holdout.py --protocol cross_source --train-dir datasets/synthetic_holdout/train \
    --test-dir <CIC test folder> --data-label "<CICIoMT2024 test CSV folder, user-supplied; not redistributed>" \
    --out benchmarks/results/traffic_rules_holdout_cic_p1.json                                    # E10 P1
python benchmarks/traffic_rules_holdout.py --protocol temporal_split --test-dir <CIC test folder> --dev-fraction 0.5 \
    --data-label "<CICIoMT2024 test CSV folder, user-supplied; not redistributed>" \
    --out benchmarks/results/traffic_rules_holdout_cic_p2.json                                    # E10 P2
python benchmarks/attack_simulation_eval.py --template hospital_ward --seeds 7,11,23              # E11 (supplementary)
python scripts/gen_standards_map_doc.py                                                          # E12 table (supplementary)
python benchmarks/make_figures.py                                                                 # figures (SVG, PDF, PNG)
node scripts/svg_to_pdf.cjs                                                                       # schematic drafts (PDF, PNG)
python scripts/build_release3_docx.py                                                            # Word evidence summary
```

`traffic_rules_holdout.py` never records local paths: `train_dir` / `test_dir` hold the repository-relative path of an
in-repository folder, the folder name of any other folder, or the `--train-data-label` / `--data-label` text. The two
CICIoMT2024 runs pass a fixed label so the artifacts do not depend on where the files were downloaded.
`scripts/build_release3_docx.py` writes `docs/release-3/SafeGuard-PQ_Release3_Evidence_Summary.docx` with docx-js
(npm package `docx` 9.15.3), which it installs on first use into a scratch folder outside the repository; it is not
a dependency of the repository.

## Expected outputs

The committed artifacts in `benchmarks/results/` (see [benchmarks/README.md](../benchmarks/README.md) for the headline
numbers); `run_all.py --check` verifies them. Objective metrics, verdicts, scores, selections, detection counts and
intervals are deterministic for the stated seeds and Python version; the recorded `date`, runtimes and platform strings
are machine-dependent. The
attack-simulation and synthetic-dataset outputs are byte-identical on re-run (no timestamps). The E10 CIC artifacts
depend on the downloaded files (window counts are listed in their manifests: 376 benign, 17 ARP, 17 MQTT, 226 port
scan, 1825 DDoS, 985 SYN).

## Evaluation commands

```bash
cd backend && ruff check src tests && pytest           # expected: 236 passed
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
