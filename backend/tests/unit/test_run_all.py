"""The --check comparison of benchmarks/run_all.py; the pipeline itself is not run in tests."""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[3] / "benchmarks"


@pytest.fixture(scope="module")
def run_all():
    if str(BENCH) not in sys.path:
        sys.path.insert(0, str(BENCH))
    return importlib.import_module("run_all")


def _json(obj: object) -> bytes:
    return json.dumps(obj, indent=2).encode("utf-8")


def test_volatile_keys_are_dates_versions_and_timings_only(run_all) -> None:
    for key in ("date", "python", "platform", "machine", "software_version", "runtime_s", "total_runtime_s",
                "mean_optimize_ms_including_exact_solver", "runtime_ratio_heuristic_over_ilp", "mean_runtime_ms", "runtime_ms"):
        assert run_all.is_volatile(key), key
    for key in ("mean_gap_pct", "f1", "runtime", "test_dir", "seed", "solver", "qiro_version"):
        assert not run_all.is_volatile(key), key


def test_json_check_ignores_volatile_fields_and_reports_every_other_change(run_all) -> None:
    old = {"date": "2026-11-22", "python": "3.13.5", "total_runtime_s": 97.7,
           "by_size": {"20": {"mean_gap_pct": 0.3006, "mean_runtime_ms": 16.6}},
           "instances": [{"objective": {"ilp": 10.0}, "runtime_ms": {"ilp": 3.2}, "ilp_status": "Optimal"}]}
    new = copy.deepcopy(old)
    new.update(date="2027-01-01", total_runtime_s=120.4)
    new["by_size"]["20"]["mean_runtime_ms"] = 20.1
    new["instances"][0]["runtime_ms"]["ilp"] = 4.0
    res = run_all.compare_artifact("benchmarks/results/x.json", _json(old), _json(new))
    assert res.status == "PASS"
    assert "total_runtime_s" in res.notes[0] and "mean_runtime_ms" in res.notes[0]

    new["by_size"]["20"]["mean_gap_pct"] = 0.3007
    new["instances"].append({"objective": {"ilp": 1.0}})
    res = run_all.compare_artifact("benchmarks/results/x.json", _json(old), _json(new))
    assert res.status == "CHANGED"
    assert "$.by_size.20.mean_gap_pct: 0.3006 -> 0.3007" in res.notes
    assert "$.instances: 1 -> 2 items" in res.notes
    assert run_all.compare_artifact("a.json", _json({"passed": True}), _json({"passed": 1})).status == "CHANGED"
    assert run_all.compare_artifact("a.json", _json({"n": 1}), _json({"n": 1.0})).status == "PASS"


def test_text_check_normalises_line_endings(run_all) -> None:
    assert run_all.compare_artifact("datasets/synthetic_holdout/README.md", b"a\nb\n", b"a\r\nb\r\n").status == "PASS"
    res = run_all.compare_artifact("datasets/synthetic_holdout/train/benign.csv", b"x,y\n1,2\n", b"x,y\n1,3\n")
    assert res.status == "CHANGED" and res.notes[0].startswith("line 2:")


def test_new_and_missing_artifacts(run_all) -> None:
    assert run_all.compare_artifact("benchmarks/results/new.json", None, b"{}").status == "NEW"
    missing = run_all.compare_artifact("benchmarks/results/gone.json", b"{}", None)
    assert missing.status == "MISSING" and missing.status in run_all.FAILING
    assert "NEW" not in run_all.FAILING and "NOT RUN" not in run_all.FAILING


def test_pipeline_steps_follow_the_options(run_all, tmp_path) -> None:
    steps, skipped = run_all.build_steps(run_all.parse_args(["--skip-slow", "--no-figures", "--no-docx"]))
    names = [s.name for s in steps]
    assert names[:2] == ["E3 optimizer vs exhaustive optimum", "E7 scoring sensitivity"]
    assert not any(n.startswith(("E8", "E6", "E10 P")) for n in names)
    assert not any("figures" in n or "Word" in n for n in names)
    assert any("--skip-slow" in s for s in skipped) and any("--cic-test-dir" in s for s in skipped)

    steps, _ = run_all.build_steps(run_all.parse_args(["--cic-test-dir", str(tmp_path), "--no-docx"]))
    cmds = {s.name: s.cmd for s in steps}
    assert cmds["E8 optimizer scalability vs ILP"][2:] == ["--sizes", "20,50,100,200", "--instances-per-size", "50",
                                                           "--seed", "0", "--small-check", "100"]
    for name in ("E10 P1 cross-source", "E10 P2 temporal split"):
        assert cmds[name][cmds[name].index("--data-label") + 1] == run_all.CIC_LABEL
    assert cmds["result figures"][1:] == ["-I", "benchmarks/make_figures.py"]
