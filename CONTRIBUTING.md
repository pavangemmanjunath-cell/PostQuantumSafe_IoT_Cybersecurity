# Contributing

## Welcome

Thank you for considering a contribution. SafeGuard-PQ is a TIPPSS-based framework (IEEE 2933-2024: Trust, Identity, Privacy, Protection, Safety, Security)
for post-quantum safety testing of IoT and edge environments, implemented first for healthcare. It is an early-stage research prototype, so independent scrutiny is
especially valuable: bug reports, reproductions that *fail*, and critiques of the methodology are as welcome as code.

## Ways to contribute

- **Bug fixes** and robustness improvements
- **Features** (new agents, tools, simulator device profiles or attacks)
- **Research extensions** — better PQ identification, calibrated scoring, alternative optimisers
- **Benchmark additions** — independent datasets, train/test splits, comparisons with other tools
- **Dataset adapters** — only for data you are allowed to use and that users can obtain themselves
- **Documentation** and examples
- **Tests**
- **Reproducibility verification** — run the documented commands on your platform and report the outcome

## Development setup

```bash
git clone https://github.com/<your-fork>/PostQuantumSafe_IoT_Cybersecurity.git
cd PostQuantumSafe_IoT_Cybersecurity
python -m venv backend/.venv
# Windows: backend\.venv\Scripts\activate   Linux/macOS: source backend/.venv/bin/activate
pip install -e "backend[dev]"
cd frontend && npm ci && npx playwright install chromium && cd ..
```

Run everything locally: `scripts/dev.ps1` (Windows) or `scripts/dev.sh` (Linux/macOS).

## Forking

1. Click **Fork** on GitHub.
2. Clone your fork and add the upstream remote:
   `git remote add upstream https://github.com/pavangemmanjunath-cell/PostQuantumSafe_IoT_Cybersecurity.git`
3. Keep your fork current: `git fetch upstream && git rebase upstream/main`.

## Branch naming

```
feature/<description>     new capability
fix/<description>         bug fix
docs/<description>        documentation only
research/<description>    methodological / experimental change
benchmark/<description>   benchmark scripts or results
```

## Making changes

- Python: typed, small single-purpose functions; follow the existing module layout (agents call tools; tools are pure).
  Run `ruff check src tests` from `backend/`.
- TypeScript: `npm run typecheck` must pass; avoid new runtime dependencies unless justified.
- Keep agents deterministic. Randomness must flow from an explicit seed.
- Never log or echo raw PHI or secrets — use `knowledge.redaction`.
- Do not change recorded benchmark numbers by hand; re-run the script and commit its output.

## Testing

All of the following must pass before a pull request is reviewed:

```bash
cd backend && ruff check src tests && pytest
cd frontend && npm run typecheck && npm run build && npx playwright test
```

Add tests for every behaviour change. If you change scoring or detection rules, update the affected expectations and
explain the derivation in the test or PR.

## Documentation

New capabilities need: a README or docs entry, an updated `CHANGELOG.md` (`[Unreleased]`), and API schema docstrings.

## Research contributions

For methodological changes, describe in the PR:

- the research problem and why the current approach is insufficient;
- the proposed method and its assumptions;
- the evaluation methodology (data, metrics, baselines) and results, including negative results;
- supporting references where relevant.

## Pull request process

1. Fork → 2. branch → 3. change → 4. test → 5. document → 6. open a PR using the template.
Keep PRs focused; large changes are easier to review after an issue discussion.

## Data contributions

Do **not** contribute:

- proprietary or confidential company data;
- real patient data, personal data, or anything subject to HIPAA/GDPR without documented authorisation;
- datasets you do not have the right to redistribute (e.g. most third-party research datasets — contribute a
  download/adapter script instead);
- credentials of any kind (test credentials must be built at runtime, see `simulation/fakes.py`).

## Contributor attribution

Merged contributions are acknowledged in `AUTHORS.md` by contribution category and in release notes. Authorship of any
associated publication is decided separately according to scholarly norms and is not granted automatically.

By contributing you agree that your contribution is licensed under the Apache License 2.0 and you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
