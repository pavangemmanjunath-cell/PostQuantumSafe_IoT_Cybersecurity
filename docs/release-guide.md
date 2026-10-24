# Release Guide

## Before release

- [ ] `cd backend && ruff check src tests && pytest` passes
- [ ] `cd frontend && npm run typecheck && npm run build && npx playwright test` passes
- [ ] CI green on the release commit
- [ ] `CHANGELOG.md` updated (move `[Unreleased]` items under the new version and date)
- [ ] Version bumped consistently: `backend/pyproject.toml`, `backend/src/safeguard_pq/__init__.py`,
      `frontend/package.json`, `CITATION.cff` (`version`, `date-released`)
- [ ] `CITATION.cff` validates (`pip install cffconvert && cffconvert --validate`)
- [ ] Secret scan clean (e.g. `gitleaks detect` or GitHub secret scanning); no `.env` committed
- [ ] License and third-party data statements correct
- [ ] Examples execute; documentation links work
- [ ] Release notes prepared in `docs/releases/vX.Y.Z.md`

## Versioning

Semantic Versioning `MAJOR.MINOR.PATCH`, tags with a lowercase `v`: `v0.1.0`, `v0.2.0`, `v0.2.1`, `v1.0.0`.

- MAJOR — backward-incompatible API/schema changes (0.x may still change APIs; note them in the changelog).
- MINOR — new backward-compatible functionality.
- PATCH — backward-compatible fixes and documentation corrections.

Avoid tags such as `V_1.1`, `Version_1`, `release_new`.

## GitHub release

```bash
git tag -a v0.1.0 -m "SafeGuard-PQ v0.1.0"
git push origin v0.1.0
```
Create the GitHub Release from the tag and paste `docs/releases/v0.1.0.md`.

## Zenodo

If the repository is enabled in Zenodo's GitHub integration: GitHub Release → Zenodo ingests the release → archived
software version → version DOI. Do not upload the same release manually as well.

## Post-release

After Zenodo assigns a DOI: verify the Zenodo metadata, add the DOI badge and "Software DOI" line to the README, add
`doi:` / `identifiers:` to `CITATION.cff` for the next release, and record the release in the changelog.
Never modify an archived release to make history look cleaner — publish a new version instead.
