"""Run every Release 3 experiment, rebuild the figures and the Word summary, and check the results against git.

    python benchmarks/run_all.py --cic-test-dir <CICIoMT2024 test CSV folder> \\
        --figures-python <python with matplotlib> --check

Steps, in this order and with the arguments documented in docs/reproducibility.md (each command is printed with its
wall time; the run stops with a non-zero exit status at the first failure):

  E3 qiro_optimality, E7 sensitivity_analysis, E8 qiro_scalability (about 100 s; skipped with --skip-slow),
  E9 plan_reassessment, the synthetic held-out dataset, E10 on the synthetic dataset; with --cic-test-dir also
  E6 traffic_rules_eval and E10 protocols P1 (cross_source) and P2 (temporal_split); E11 attack_simulation_eval;
  the E12 standards table (scripts/gen_standards_map_doc.py); the result figures (benchmarks/make_figures.py, run
  with --figures-python in isolated mode); the schematic figure PDFs (node scripts/svg_to_pdf.cjs) and the Word
  summary (scripts/build_release3_docx.py), both only when Node.js is available. --no-figures and --no-docx leave
  out the figure and Word steps.

--check compares every regenerated artifact in benchmarks/results/ and datasets/synthetic_holdout/ with the
committed version (``git show HEAD:<path>``): JSON files value by value without the volatile fields (dates,
interpreter, platform and software-version strings, runtimes), other files byte by byte with line endings
normalised. It prints a PASS / CHANGED table and exits with status 1 if any deterministic value changed. The CI
job ``reproduce`` (.github/workflows/ci.yml) runs ``--check --no-figures --no-docx`` for pushes and pull requests.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECKED_DIRS = ("benchmarks/results", "datasets/synthetic_holdout")
RESULTS = "benchmarks/results/"
SYNTHETIC = "datasets/synthetic_holdout"
# Label recorded as test_dir for the CICIoMT2024 runs, so the artifacts do not depend on the local folder name.
CIC_LABEL = "<CICIoMT2024 test CSV folder, user-supplied; not redistributed>"
VOLATILE_KEYS = frozenset({
    "date", "python", "platform", "machine", "software_version", "runtime_s", "total_runtime_s",
    "mean_optimize_ms_including_exact_solver", "runtime_ratio_heuristic_over_ilp",
})
FAILING = frozenset({"CHANGED", "MISSING"})
STATUS_ORDER = ("PASS", "CHANGED", "NEW", "MISSING", "NOT RUN")


def is_volatile(key: str) -> bool:
    """Run- or machine-dependent field: date, interpreter / platform / version string or a runtime (``*_ms``)."""
    return key in VOLATILE_KEYS or key.endswith("_ms")


# ----------------------------------------------------------------------------------------------------- comparison


@dataclass
class Comparison:
    path: str
    status: str  # one of STATUS_ORDER
    notes: list[str] = field(default_factory=list)


def _short(value: Any, limit: int = 70) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def json_differences(old: Any, new: Any, limit: int = 8) -> tuple[list[str], Counter[str]]:
    """Differences between two JSON values outside the volatile fields, and the volatile fields that differ.

    Returns ``(differences, ignored)``: up to ``limit`` lines ``$.path: old -> new`` (plus a count of the rest) and
    a counter of volatile keys whose values differ.
    """
    diffs: list[str] = []
    ignored: Counter[str] = Counter()
    total = 0

    def record(line: str) -> None:
        nonlocal total
        total += 1
        if len(diffs) < limit:
            diffs.append(line)

    def walk(a: Any, b: Any, where: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in [*a, *(k for k in b if k not in a)]:
                sub = f"{where}.{key}"
                if is_volatile(str(key)):
                    if a.get(key) != b.get(key):
                        ignored[str(key)] += 1
                elif key not in b:
                    record(f"{sub}: removed")
                elif key not in a:
                    record(f"{sub}: added {_short(b[key])}")
                else:
                    walk(a[key], b[key], sub)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                record(f"{where}: {len(a)} -> {len(b)} items")
            for i, (x, y) in enumerate(zip(a, b, strict=False)):
                walk(x, y, f"{where}[{i}]")
        elif not _same(a, b):
            record(f"{where}: {_short(a)} -> {_short(b)}")

    walk(old, new, "$")
    if total > len(diffs):
        diffs.append(f"... and {total - len(diffs)} more difference(s)")
    return diffs, ignored


def _first_text_difference(a: bytes, b: bytes) -> str:
    la, lb = a.decode("utf-8", "replace").split("\n"), b.decode("utf-8", "replace").split("\n")
    for i, (x, y) in enumerate(zip(la, lb, strict=False), 1):
        if x != y:
            return f"line {i}: {_short(x)} -> {_short(y)}"
    return f"{len(la)} -> {len(lb)} lines"


def compare_artifact(path: str, old: bytes | None, new: bytes | None) -> Comparison:
    """Compare the committed bytes (``old``, None if not in HEAD) with the regenerated bytes (``new``)."""
    if new is None:
        return Comparison(path, "MISSING", ["expected output was not written by this run"])
    if old is None:
        return Comparison(path, "NEW", ["not in HEAD; nothing to compare"])
    if path.endswith(".json"):
        try:
            a, b = json.loads(old), json.loads(new)
        except ValueError as exc:
            return Comparison(path, "CHANGED", [f"not valid JSON: {exc}"])
        diffs, ignored = json_differences(a, b)
        if diffs:
            return Comparison(path, "CHANGED", diffs)
        if ignored:
            return Comparison(path, "PASS", ["volatile fields differ (ignored): "
                                             + ", ".join(f"{k} x{n}" if n > 1 else k for k, n in sorted(ignored.items()))])
        return Comparison(path, "PASS", ["identical"])
    a, b = old.replace(b"\r\n", b"\n"), new.replace(b"\r\n", b"\n")
    if a == b:
        return Comparison(path, "PASS", ["identical"])
    return Comparison(path, "CHANGED", [_first_text_difference(a, b)])


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)


def git_show(path: str) -> bytes | None:
    proc = _git("show", f"HEAD:{path}")
    return proc.stdout if proc.returncode == 0 else None


def tracked(prefixes: Sequence[str]) -> list[str]:
    proc = _git("ls-tree", "-r", "--name-only", "HEAD", "--", *prefixes)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace").strip() or "git ls-tree failed")
    return [line for line in proc.stdout.decode("utf-8").splitlines() if line]


def _under(path: str, prefixes: Sequence[str]) -> bool:
    return any(path == p or path.startswith(p.rstrip("/") + "/") for p in prefixes)


def check(steps: Sequence[Step]) -> list[Comparison]:
    """Compare the outputs of the steps that ran with HEAD; tracked artifacts no step regenerated are NOT RUN."""
    head = tracked(CHECKED_DIRS)
    produced: dict[str, None] = {}
    for step in steps:
        for out in step.outputs:
            if not _under(out, CHECKED_DIRS):
                continue
            target = ROOT / out
            if target.is_dir() or out == SYNTHETIC:
                files = [p.relative_to(ROOT).as_posix() for p in sorted(target.rglob("*")) if p.is_file()]
                for path in [*files, *(h for h in head if _under(h, [out]))]:
                    produced.setdefault(path)
            else:
                produced.setdefault(out)
    results = []
    for path in sorted(produced):
        file = ROOT / path
        results.append(compare_artifact(path, git_show(path), file.read_bytes() if file.is_file() else None))
    results += [Comparison(path, "NOT RUN", ["its step did not run"]) for path in head if path not in produced]
    return results


def print_check(results: Sequence[Comparison]) -> None:
    print("\nCheck of regenerated artifacts against HEAD (git show HEAD:<path>)")
    print("volatile fields ignored: " + ", ".join(sorted(VOLATILE_KEYS)) + ", *_ms")
    width = max((len(r.path) for r in results), default=10)
    print(f"\n{'Status':8} {'Artifact':{width}}  Notes")
    print(f"{'-' * 8} {'-' * width}  {'-' * 40}")
    for r in results:
        notes = r.notes or [""]
        print(f"{r.status:8} {r.path:{width}}  {notes[0]}")
        for extra in notes[1:]:
            print(f"{'':8} {'':{width}}  {extra}")
    counts = Counter(r.status for r in results)
    summary = ", ".join(f"{counts[s]} {s}" for s in STATUS_ORDER if counts[s])
    print(f"\nsummary: {summary}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _github_report(results, summary)


def _gh_escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _github_report(results: Sequence[Comparison], summary: str) -> None:
    """GitHub Actions: one annotation per failing artifact (readable through the checks API) and a job summary."""
    for r in results:
        if r.status in FAILING:
            print(f"::error title=run_all --check {r.status}::" + _gh_escape(f"{r.path}: {'; '.join(r.notes)}"[:3000]))
    print(f"::notice title=run_all --check::{_gh_escape(summary)}")
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if not target:
        return
    lines = ["### Reproduction check: `benchmarks/run_all.py --check`", "", summary, "", "| Status | Artifact | Notes |", "|---|---|---|"]
    for r in results:
        notes = "<br>".join(n.replace("|", "\\|") for n in r.notes)
        lines.append(f"| {r.status} | `{r.path}` | {notes} |")
    with open(target, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------------------------------------- steps


@dataclass
class Step:
    name: str
    cmd: list[str]
    outputs: tuple[str, ...] = ()  # repository-relative files or folders the step writes


def build_steps(args: argparse.Namespace) -> tuple[list[Step], list[str]]:
    """The pipeline for these options and the steps left out (with the reason)."""
    py = sys.executable
    syn_train, syn_test = f"{SYNTHETIC}/train", f"{SYNTHETIC}/test"
    steps = [
        Step("E3 optimizer vs exhaustive optimum", [py, "benchmarks/qiro_optimality.py", "--instances", "500", "--seed", "0"],
             (RESULTS + "qiro_optimality.json",)),
        Step("E7 scoring sensitivity", [py, "benchmarks/sensitivity_analysis.py", "--seed", "2026"],
             (RESULTS + "sensitivity_analysis.json",)),
    ]
    skipped: list[str] = []
    e8 = Step("E8 optimizer scalability vs ILP",
              [py, "benchmarks/qiro_scalability.py", "--sizes", "20,50,100,200", "--instances-per-size", "50", "--seed", "0",
               "--small-check", "100"], (RESULTS + "qiro_scalability.json",))
    if args.skip_slow:
        skipped.append(f"{e8.name} (--skip-slow)")
    else:
        steps.append(e8)
    steps += [
        Step("E9 plan reassessment", [py, "benchmarks/plan_reassessment.py", "--seed", "2026", "--exhaustive-max-n", "10"],
             (RESULTS + "plan_reassessment.json",)),
        Step("synthetic held-out dataset",
             [py, "benchmarks/make_synthetic_traffic_dataset.py", "--out", SYNTHETIC, "--train-seed", "101", "--test-seed", "202",
              "--windows-per-class", "20"], (SYNTHETIC,)),
        Step("E10 held-out rules, synthetic demonstration",
             [py, "benchmarks/traffic_rules_holdout.py", "--train-dir", syn_train, "--test-dir", syn_test,
              "--out", RESULTS + "traffic_rules_holdout.json"], (RESULTS + "traffic_rules_holdout.json",)),
    ]
    if args.cic_test_dir:
        cic = str(args.cic_test_dir)
        steps += [
            Step("E6 traffic rules, same split", [py, "benchmarks/traffic_rules_eval.py", "--data-dir", cic, "--window", "100"],
                 (RESULTS + "traffic_rules_eval.json",)),
            Step("E10 P1 cross-source",
                 [py, "benchmarks/traffic_rules_holdout.py", "--protocol", "cross_source", "--train-dir", syn_train, "--test-dir", cic,
                  "--data-label", CIC_LABEL, "--out", RESULTS + "traffic_rules_holdout_cic_p1.json"],
                 (RESULTS + "traffic_rules_holdout_cic_p1.json",)),
            Step("E10 P2 temporal split",
                 [py, "benchmarks/traffic_rules_holdout.py", "--protocol", "temporal_split", "--test-dir", cic, "--dev-fraction", "0.5",
                  "--data-label", CIC_LABEL, "--out", RESULTS + "traffic_rules_holdout_cic_p2.json"],
                 (RESULTS + "traffic_rules_holdout_cic_p2.json",)),
        ]
    else:
        skipped.append("E6 and E10 P1/P2 on CICIoMT2024 (no --cic-test-dir)")
    steps += [
        Step("E11 attack simulation", [py, "benchmarks/attack_simulation_eval.py", "--template", "hospital_ward", "--seeds", "7,11,23"],
             (RESULTS + "attack_simulation.json",)),
        Step("E12 standards table", [py, "scripts/gen_standards_map_doc.py"], ("docs/release-3/standards_mapping.md",)),
    ]
    node = shutil.which("node")
    if args.no_figures:
        skipped.append("result figures and schematic figure PDFs (--no-figures)")
    else:
        steps.append(Step("result figures", [args.figures_python, "-I", "benchmarks/make_figures.py"], ("docs/release-3/figures",)))
        if node and (ROOT / "frontend" / "node_modules" / "playwright").is_dir():
            steps.append(Step("schematic figure PDFs", [node, "scripts/svg_to_pdf.cjs"], ("docs/release-3/figures",)))
        else:
            skipped.append("schematic figure PDFs (node or frontend/node_modules/playwright not found)")
    if args.no_docx:
        skipped.append("Word evidence summary (--no-docx)")
    elif node:
        steps.append(Step("Word evidence summary", [py, "scripts/build_release3_docx.py"],
                          ("docs/release-3/SafeGuard-PQ_Release3_Evidence_Summary.docx",)))
    else:
        skipped.append("Word evidence summary (node not found)")
    return steps, skipped


def _display(cmd: Sequence[str]) -> str:
    shown = ["python" if i == 0 and c == sys.executable else c for i, c in enumerate(cmd)]
    return shlex.join(shown)


def run_steps(steps: Sequence[Step]) -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    timings: list[tuple[str, float, int]] = []
    rc = 0
    for i, step in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps)}] {step.name}\n$ {_display(step.cmd)}", flush=True)
        t0 = time.perf_counter()
        try:
            rc = subprocess.run(step.cmd, cwd=ROOT, env=env, check=False).returncode
        except OSError as exc:  # interpreter or node not found
            print(f"cannot start: {exc}", file=sys.stderr)
            rc = 127
        elapsed = time.perf_counter() - t0
        timings.append((step.name, elapsed, rc))
        print(f"-> {'ok' if rc == 0 else f'FAILED with exit status {rc}'} ({elapsed:.1f} s)", flush=True)
        if rc != 0:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print(f"::error title=run_all step failed::{_gh_escape(f'{step.name} exited with status {rc}')}")
            break
    print("\nWall time per step")
    for name, elapsed, code in timings:
        print(f"  {name:46s} {elapsed:8.1f} s{'' if code == 0 else '  FAILED'}")
    print(f"  {'total':46s} {sum(t for _, t, _ in timings):8.1f} s")
    return rc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cic-test-dir", type=Path, default=None,
                    help="folder with the CICIoMT2024 *_test.pcap.csv files; enables E6 and E10 protocols P1 and P2")
    ap.add_argument("--figures-python", default=sys.executable,
                    help="Python interpreter with matplotlib for benchmarks/make_figures.py, run in isolated mode -I "
                         "(default: this interpreter)")
    ap.add_argument("--skip-slow", action="store_true", help="skip E8 (about 100 s)")
    ap.add_argument("--no-figures", action="store_true", help="do not redraw the figures (make_figures.py, svg_to_pdf.cjs)")
    ap.add_argument("--no-docx", action="store_true", help="do not rebuild the Word evidence summary")
    ap.add_argument("--check", action="store_true",
                    help="afterwards compare the regenerated artifacts with HEAD; exit 1 if a deterministic value changed")
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # never fail on characters the console cannot encode
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="backslashreplace")
    if args.cic_test_dir and not args.cic_test_dir.is_dir():
        print(f"--cic-test-dir is not a folder: {args.cic_test_dir}", file=sys.stderr)
        return 2
    steps, skipped = build_steps(args)
    print(f"python = {sys.executable}")
    for reason in skipped:
        print(f"skip: {reason}")
    rc = run_steps(steps)
    if rc != 0 or not args.check:
        return rc
    try:
        results = check(steps)
    except (OSError, RuntimeError) as exc:
        print(f"--check needs git and a commit to compare with: {exc}", file=sys.stderr)
        return 2
    print_check(results)
    return 1 if any(r.status in FAILING for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
