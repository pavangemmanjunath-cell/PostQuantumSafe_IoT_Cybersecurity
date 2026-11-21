# Unreleased

## Research results and simulation transparency

- Added a Research Results page to the web application. It reads the committed, machine-readable benchmark artifacts and presents optimizer and traffic-rule metrics alongside their limitations.
- Re-ran the seeded QIRO benchmark with 500 synthetic instances on 2026-11-22. Annealing plus local search reached the exhaustive optimum on 97.6% of instances, with a 0.0532% mean objective gap. The measured mean runtime was 8.62 ms per instance on the recorded machine and is not a portable performance guarantee.
- Kept the previously recorded CICIoMT2024 traffic-rule results visible with their dataset date and explicit same-split threshold-selection caveat. The external CSV dataset is not included in this repository and was not re-run in this update.
- Clarified in the simulation UI that defences are simulated configuration changes; a reassessment is not evidence of real-world protection.

## Validation

- `.\backend\.venv\Scripts\python.exe .\benchmarks\qiro_optimality.py --instances 500 --seed 0 --out .\benchmarks\results\qiro_optimality.json` — passed; 500 nonzero-optimum instances.
- `.\backend\.venv\Scripts\ruff.exe check .\backend\src .\backend\tests` — passed.
- `.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests` — passed; 148 tests.
- `npm --prefix .\frontend run build` — passed.
- `npm --prefix .\frontend run test:e2e` — passed; 11 tests.

### Independent re-check (2026-11-22)

All of the above were repeated on a clean checkout of `feat/research-results-dashboard` before pushing:

- Backend lint passed; 148 backend tests passed; frontend type-check and build passed; 11 browser end-to-end tests passed.
- A second QIRO run (`--instances 500 --seed 0`, written to a temporary file) matched the committed
  `benchmarks/results/qiro_optimality.json` exactly for instance count, optimal share, and mean / p95 / max gap for both
  methods. Mean runtime was 8.51 ms versus 8.62 ms in the committed artifact, consistent with runtime being
  machine- and load-dependent.
- README, `docs/novelty.md`, `benchmarks/README.md` and this note were cross-checked against both JSON artifacts.
  The "10 browser tests" counts in `CHANGELOG.md` [0.1.0] and `docs/releases/v0.1.0.md` are historical and were left
  unchanged.
