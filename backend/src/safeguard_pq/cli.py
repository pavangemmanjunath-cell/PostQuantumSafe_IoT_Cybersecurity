"""Command-line interface.

    safeguard-pq serve [--host 127.0.0.1] [--port 8000]
    safeguard-pq scenarios
    safeguard-pq assess --scenario icu_gateway_critical [--pdf report.pdf] [--json result.json]
    safeguard-pq assess --file request.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import __version__


def _assess(args: argparse.Namespace) -> int:
    from .orchestrator import run_assessment
    from .reporting import build_assessment_pdf
    from .scenarios import get_scenario

    if args.scenario:
        s = get_scenario(args.scenario)
        if not s:
            print(f"unknown scenario: {args.scenario}", file=sys.stderr)
            return 2
        payload = s["request"]
    else:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if args.seed is not None:
        payload = {**payload, "seed": args.seed}
    result = asyncio.run(run_assessment(payload))
    print(f"{result.system_id}: environment {result.environment_status} | PQ score {result.pq_risk_score}/100 ({result.verdict}) | "
          f"{result.findings_count} finding(s) | QIRO {result.qiro_optimization.get('selection_count', 0)} action(s)")
    for reason in result.environment_reasons:
        print(f"  - {reason}")
    if args.json:
        Path(args.json).write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"JSON written: {args.json}")
    if args.pdf:
        Path(args.pdf).write_bytes(build_assessment_pdf(result))
        print(f"PDF written: {args.pdf}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="safeguard-pq", description="TIPPSS SafeGuard-PQ (research prototype)")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the API server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")

    sub.add_parser("scenarios", help="list built-in scenarios")

    a = sub.add_parser("assess", help="run an assessment")
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--scenario")
    g.add_argument("--file")
    a.add_argument("--seed", type=int)
    a.add_argument("--pdf")
    a.add_argument("--json")

    args = ap.parse_args(argv)
    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("safeguard_pq.api.app:app", host=args.host, port=args.port, reload=args.reload)
        return 0
    if args.cmd == "scenarios":
        from .scenarios import load_scenarios

        for sc in load_scenarios():
            print(f"{sc['id']:24s} {sc['title']}")
        return 0
    return _assess(args)


if __name__ == "__main__":
    raise SystemExit(main())
