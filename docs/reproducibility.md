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
cd frontend && npm ci && npx playwright install chromium
```

## Dependencies

Declared in `backend/pyproject.toml` (ranges) and `frontend/package.json` + `package-lock.json` (exact versions).
Versions used for the recorded results: FastAPI 0.143.3, Pydantic 2.14.1, ReportLab 5.0.1, Uvicorn 0.54.0,
React 19.3.1, three 0.186.1, @react-three/fiber 9.8.2, @react-three/drei 10.7.9, Vite 8.3.4, TypeScript 7.0.2,
Playwright 1.64.1.

## Dataset preparation

Nothing is needed for tests, demos and the QIRO benchmark (synthetic). For the traffic-rule benchmark, download the
CICIoMT2024 CSV test split yourself (see [datasets/README.md](../datasets/README.md)) into a folder of your choice.

## Configuration

Defaults need no configuration. `.env.example` documents all options; the LLM must stay `none` to reproduce reports exactly.

## Random seeds

- QIRO: request field `seed`, default `QIRO_DEFAULT_SEED=2026`.
- Simulator: `seed` per simulation (default 7); telemetry and attack windows are generated from it.
- Benchmarks: `--seed` (QIRO instance generator); QIRO seed per instance = instance index.

## Reproduce core example

```bash
cd backend
safeguard-pq assess --scenario icu_gateway_critical --json result.json --pdf report.pdf
```
Expected: `environment UNSAFE | PQ score 61/100 (Not Post-Quantum Safe) | 8 finding(s) | QIRO 5 action(s)`.

## Reproduce experiments

```bash
python benchmarks/qiro_optimality.py --instances 500 --seed 0
python benchmarks/traffic_rules_eval.py --data-dir /path/to/CICIoMT2024/test --window 100
```

## Expected outputs

`benchmarks/results/qiro_optimality.json` and `benchmarks/results/traffic_rules_eval.json` — compare with the committed
versions (see [benchmarks/README.md](../benchmarks/README.md)). The QIRO numbers are deterministic for a given seed and
Python version.

## Evaluation commands

```bash
cd backend && ruff check src tests && pytest           # expected: 148 passed
cd frontend && npm run typecheck && npm run build && npx playwright test   # expected: 10 passed
```

## Troubleshooting

- **Port already in use:** E2E tests use ports 8765/5199 (override with `E2E_API_PORT`, `E2E_WEB_PORT`); the dev scripts
  accept `-ApiPort/-WebPort` (PowerShell) or positional ports (bash).
- **GUI shows "API offline":** start the backend and check the Vite proxy target (`SAFEGUARD_API`).
- **No WebGL in headless browsers:** Playwright is launched with SwiftShader flags in `playwright.config.ts`.

## Known sources of non-determinism

- Timestamps, assessment ids and per-agent timings.
- LLM narratives when an LLM provider is configured.
- Simulator state depends on the number of ticks elapsed (wall-clock stream); use `POST /simulations/{id}/step` for
  deterministic stepping.

## Reproducibility limitations

Results were produced on a single Windows machine; cross-platform floating-point differences in annealing acceptance are
possible but have not been observed. The traffic benchmark requires a third-party download that may change over time.
