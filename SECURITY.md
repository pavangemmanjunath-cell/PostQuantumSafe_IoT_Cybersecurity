# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ (latest release only) |
| < 0.1 (v0 prototype) | ❌ |

This is a research prototype intended for local, non-production use. It has not undergone an independent security audit.

## Reporting a vulnerability

**Do not open a public issue for exploitable vulnerabilities.**

Use GitHub **Private Vulnerability Reporting** on this repository (*Security → Report a vulnerability*). If that option is
not available, contact the maintainer privately through the GitHub profile
[@pavangemmanjunath-cell](https://github.com/pavangemmanjunath-cell) and request a private channel.

## What to include

- affected version / commit;
- a description of the vulnerability and its impact;
- reproduction steps or a proof of concept (please use synthetic data only);
- any suggested mitigation.

## Response expectations

This project is maintained on a best-effort basis by an individual researcher. Reports will be acknowledged and
assessed as time permits; no response-time guarantee is given. Coordinated disclosure is appreciated — please allow a
reasonable period for a fix before public disclosure.

## Scope notes

- The backend stores assessments **in memory only** and has **no authentication**; do not expose it to untrusted networks.
- Uploaded files are parsed in memory and not persisted; size is limited by `MAX_UPLOAD_MB`.
- Optional outbound calls (LLM provider, openFDA) are disabled by default and only send redacted, aggregated data.
