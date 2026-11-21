"""Held-out evaluation of the heuristic traffic rules: tune on a development split, evaluate ONCE on held-out data.

Three partition protocols are supported (``--protocol``):

* ``capture_split`` (default when ``--train-dir`` and ``--test-dir`` are given): whole files/captures belong
  to one split. This is the intended protocol for the CICIoMT2024 train and test CSV folders::

      python benchmarks/traffic_rules_holdout.py --train-dir <CIC/train> --test-dir <CIC/test>
      python benchmarks/traffic_rules_holdout.py --train-dir datasets/synthetic_holdout/train \\
          --test-dir datasets/synthetic_holdout/test

* ``cross_source``: development on one source (e.g. the synthetic simulator split), a single evaluation on
  another (e.g. the real CICIoMT2024 test files). The evaluation data are never used for threshold selection::

      python benchmarks/traffic_rules_holdout.py --protocol cross_source \\
          --train-dir datasets/synthetic_holdout/train --test-dir <CIC/test>

* ``temporal_split``: only ``--test-dir``; inside every file the first ``--dev-fraction`` of its windows (in
  file order) form the development set and the remainder the held-out set. Development and held-out windows
  come from the same captures, so this is weaker than a capture-level split::

      python benchmarks/traffic_rules_holdout.py --protocol temporal_split --test-dir <CIC/test> --dev-fraction 0.5

Common procedure
* Windows are consecutive, non-overlapping blocks of ``--window`` rows (same windowing as
  ``traffic_rules_eval.py``), never span files, at most ``--max-windows`` per file.
* Labels come from file names: "benign" in the name -> benign, otherwise attack. The class is derived from the
  CICIoMT2024 file-name keywords (``catalog.REPLAY_FILES``) or, failing that, the cleaned file stem (which is
  how the synthetic dataset is named).
* Development: each rule's thresholds are tuned by a bounded grid search - every threshold is multiplied by a
  factor in ``FACTORS``; the rule structure and comparison operators are kept - choosing the setting with the
  highest F1 for the rule's target attack class vs. benign. Ties go to the setting closest to the shipped
  thresholds, so the shipped values are kept when they are already optimal.
* Evaluation (once, on the held-out windows): window-level precision / recall / F1 / FPR with 95 % bootstrap
  CIs over windows, per-class detection rates with Wilson 95 % intervals, per-file summaries and a confusion
  matrix, for the shipped thresholds, the tuned thresholds and three baselines fitted on the development set
  (majority class; mean ``Rate`` above the 99th percentile of benign development windows; mean ``Tot size``
  outside the 1st-99th percentile band of benign development windows).

The CICIoMT2024 files are not redistributed with this repository (see datasets/README.md).
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import platform
import random
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.knowledge import traffic_rules  # noqa: E402
from safeguard_pq.knowledge.traffic_rules import TrafficRule  # noqa: E402
from safeguard_pq.simulation import catalog as cat  # noqa: E402
from traffic_rules_eval import windows as iter_windows  # noqa: E402

FACTORS: tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5)
TARGETS: dict[str, tuple[str, ...]] = {
    "volumetric_flood_pattern": ("ddos_volumetric",),
    "syn_flood_pattern": ("syn_flood",),
    "port_scan_pattern": ("port_scan",),
    "protocol_flag_anomaly": ("mqtt_malformed",),
    "protocol_mix_anomaly": ("arp_spoofing",),
}
TARGET_RULE_OF_CLASS = {cls: rule for rule, classes in TARGETS.items() for cls in classes}
PROTOCOLS = ("capture_split", "cross_source", "temporal_split")
CIC_TEST_SOURCE = "CICIoMT2024 test split (user-downloaded, not redistributed)"
CIC_TRAIN_SOURCE = "CICIoMT2024 train split (user-downloaded, not redistributed)"
CIC_SOURCE = "CICIoMT2024 (user-downloaded, not redistributed)"
SYNTHETIC_SOURCE = "synthetic_simulator"
Z95 = 1.959964
TN, FP, FN, TP = 0, 1, 2, 3


@dataclass(frozen=True)
class Window:
    file: str
    cls: str
    label: int  # 1 = attack, 0 = benign
    index: int  # position of the window inside its file
    features: Mapping[str, float]


# ----------------------------------------------------------------------------- statistics (no scipy)


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion k/n; None when n == 0."""
    if n <= 0:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, centre - half)  # the bounds are exactly 0 / 1 at k = 0 / k = n
    hi = 1.0 if k == n else min(1.0, centre + half)
    return (lo, hi)


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolation percentile (numpy default), q in [0, 100]."""
    if not values:
        return None
    s = sorted(values)
    pos = (len(s) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def prf(tp: int, fp: int, tn: int, fn: int) -> dict[str, float | None]:
    """Precision, recall, F1 and false-positive rate; None where the denominator is zero."""
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    return {"precision": precision, "recall": recall, "f1": f1, "fpr": fpr}


def outcome_codes(y_true: Sequence[int], y_pred: Sequence[int]) -> list[int]:
    return [(TP if t else FP) if p else (FN if t else TN) for t, p in zip(y_true, y_pred, strict=True)]


def confusion(codes: Sequence[int]) -> dict[str, int]:
    c = Counter(codes)
    return {"tp": c[TP], "fp": c[FP], "tn": c[TN], "fn": c[FN]}


def bootstrap_ci(codes: Sequence[int], n_resamples: int = 1000, seed: int = 0) -> dict[str, Any]:
    """Percentile bootstrap (2.5 / 97.5) of precision, recall, F1 and FPR over windows resampled with replacement."""
    rng = random.Random(seed)
    n = len(codes)
    samples: dict[str, list[float]] = {"precision": [], "recall": [], "f1": [], "fpr": []}
    for _ in range(n_resamples):
        c = Counter(rng.choices(codes, k=n)) if n else Counter()
        for metric, value in prf(c[TP], c[FP], c[TN], c[FN]).items():
            if value is not None:
                samples[metric].append(value)
    ci = {m: ([round(percentile(v, 2.5), 4), round(percentile(v, 97.5), 4)] if v else None) for m, v in samples.items()}
    return {"ci95": ci, "resamples": n_resamples, "seed": seed, "valid_resamples": {m: len(v) for m, v in samples.items()}}


# ----------------------------------------------------------------------------- data loading


def clean_stem(name: str) -> str:
    return re.sub(r"(_train|_test)?(\.pcap)?\.csv$", "", name, flags=re.I)


def infer_class(name: str) -> str:
    """benign if the file name says so; otherwise a CICIoMT2024 keyword class (REPLAY_FILES) or the cleaned stem."""
    low = name.lower()
    if "benign" in low:
        return "benign"
    for cls, token in cat.REPLAY_FILES.items():
        if cls != "benign" and re.search(r"(?<![a-z0-9])" + re.escape(token.lower()), low):
            return cls
    return clean_stem(name)


def load_file_windows(path: Path, window: int, max_windows: int) -> list[Window]:
    cls = infer_class(path.name)
    label = 0 if cls == "benign" else 1
    out = []
    for i, rows in enumerate(iter_windows(path, window, max_windows)):
        out.append(Window(path.name, cls, label, i, traffic_rules.features_from_rows(rows)))
    return out


def load_dir(directory: Path, window: int, max_windows: int) -> dict[str, list[Window]]:
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"no CSV files in {directory}")
    return {f.name: load_file_windows(f, window, max_windows) for f in files}


def describe_source(directory: Path, override: str | None = None) -> str:
    if override:
        return override
    manifest = directory.parent / "manifest.json"
    if manifest.is_file():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            if "safeguard_pq" in str(m.get("generator", "")):
                return SYNTHETIC_SOURCE
        except (OSError, ValueError):
            pass
    names = [p.name.lower() for p in directory.glob("*.csv")]
    if any(n.endswith("_test.pcap.csv") for n in names):
        return CIC_TEST_SOURCE
    if any(n.endswith("_train.pcap.csv") for n in names):
        return CIC_TRAIN_SOURCE
    if any(".pcap" in n for n in names):
        return CIC_SOURCE
    return "csv_folder"


def manifest_of(per_file: Mapping[str, Sequence[Window]], max_windows: int) -> list[dict[str, Any]]:
    out = []
    for name, wins in per_file.items():
        entry: dict[str, Any] = {"file": name, "class": infer_class(name), "label": "benign" if infer_class(name) == "benign" else "attack",
                                 "windows": len(wins), "cap_reached": len(wins) >= max_windows}
        if wins:
            entry["window_range"] = [wins[0].index, wins[-1].index]
        out.append(entry)
    return out


# ----------------------------------------------------------------------------- rules with other thresholds


def shipped_thresholds() -> dict[str, list[float]]:
    return {r.type: [thr for _, _, thr in r.conditions] for r in traffic_rules.TRAFFIC_RULES}


def with_thresholds(rule: TrafficRule, thresholds: Sequence[float]) -> TrafficRule:
    conds = tuple((feat, op, thr) for (feat, op, _), thr in zip(rule.conditions, thresholds, strict=True))
    return replace(rule, conditions=conds)


def ruleset(thresholds: Mapping[str, Sequence[float]]) -> list[TrafficRule]:
    return [with_thresholds(r, thresholds[r.type]) for r in traffic_rules.TRAFFIC_RULES]


def fired(rules: Iterable[TrafficRule], f: Mapping[str, float]) -> list[str]:
    return [r.type for r in rules if r.evaluate(f)[0]]


def rule_predictions(rules: list[TrafficRule], wins: Sequence[Window]) -> tuple[list[int], list[list[str]]]:
    hits = [fired(rules, w.features) for w in wins]
    return [1 if h else 0 for h in hits], hits


# ----------------------------------------------------------------------------- evaluation


def evaluate(wins: Sequence[Window], preds: Sequence[int], hits: Sequence[Sequence[str]] | None = None,
             n_boot: int = 1000, seed: int = 0) -> dict[str, Any]:
    y = [w.label for w in wins]
    codes = outcome_codes(y, preds)
    conf = confusion(codes)
    metrics = prf(conf["tp"], conf["fp"], conf["tn"], conf["fn"])
    out: dict[str, Any] = {"windows": len(wins), "confusion": conf, "metrics": {k: _r(v) for k, v in metrics.items()}}
    if n_boot:
        out["bootstrap"] = bootstrap_ci(codes, n_boot, seed)

    per_class: dict[str, dict[str, Any]] = {}
    for cls in sorted({w.cls for w in wins}):
        idx = [i for i, w in enumerate(wins) if w.cls == cls]
        flagged = sum(preds[i] for i in idx)
        entry: dict[str, Any] = {
            "label": "benign" if cls == "benign" else "attack", "windows": len(idx), "flagged": flagged,
            "rate": _r(flagged / len(idx)), "rate_meaning": "false_positive_rate" if cls == "benign" else "detection_rate",
            "wilson95": _pair(wilson(flagged, len(idx))),
        }
        if hits is not None:
            counter: Counter[str] = Counter()
            for i in idx:
                counter.update(hits[i])
            entry["rule_hits"] = dict(counter.most_common())
            target = TARGET_RULE_OF_CLASS.get(cls)
            if target:
                k = sum(1 for i in idx if target in hits[i])
                entry.update(target_rule=target, target_rule_hits=k, target_rule_rate=_r(k / len(idx)),
                             target_rule_wilson95=_pair(wilson(k, len(idx))))
        per_class[cls] = entry
    out["per_class"] = per_class

    per_file = []
    for name in dict.fromkeys(w.file for w in wins):
        idx = [i for i, w in enumerate(wins) if w.file == name]
        flagged = sum(preds[i] for i in idx)
        entry = {"file": name, "class": wins[idx[0]].cls, "label": "benign" if wins[idx[0]].label == 0 else "attack",
                 "windows": len(idx), "flagged": flagged, "rate": _r(flagged / len(idx)), "wilson95": _pair(wilson(flagged, len(idx)))}
        if hits is not None:
            counter = Counter()
            for i in idx:
                counter.update(hits[i])
            entry["rule_hits"] = dict(counter.most_common())
        per_file.append(entry)
    out["per_file"] = per_file
    return out


def _r(v: float | None, nd: int = 4) -> float | None:
    return None if v is None else round(v, nd)


def _pair(p: tuple[float, float] | None) -> list[float] | None:
    return None if p is None else [round(p[0], 4), round(p[1], 4)]


# ----------------------------------------------------------------------------- tuning (development split only)


def tune(dev: Sequence[Window]) -> tuple[dict[str, list[float]], dict[str, Any]]:
    shipped = shipped_thresholds()
    tuned: dict[str, list[float]] = {}
    report: dict[str, Any] = {}
    benign = [w for w in dev if w.cls == "benign"]
    for rule in traffic_rules.TRAFFIC_RULES:
        targets = TARGETS[rule.type]
        pos = [w for w in dev if w.cls in targets]
        entry: dict[str, Any] = {"target_classes": list(targets), "conditions": [[feat, op] for feat, op, _ in rule.conditions],
                                 "shipped": shipped[rule.type], "dev_target_windows": len(pos), "dev_benign_windows": len(benign)}
        if not pos or not benign:
            tuned[rule.type] = shipped[rule.type]
            entry.update(status="skipped: target class or benign absent in development split; shipped thresholds kept",
                         tuned=shipped[rule.type], factors=[1.0] * len(rule.conditions))
            report[rule.type] = entry
            continue

        def f1_of(thresholds: Sequence[float], _rule: TrafficRule = rule, _pos: list[Window] = pos) -> tuple[float, int, int, int]:
            r = with_thresholds(_rule, thresholds)
            tp = sum(1 for w in _pos if r.evaluate(w.features)[0])
            fp = sum(1 for w in benign if r.evaluate(w.features)[0])
            fn = len(_pos) - tp
            return (2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0), tp, fp, fn

        best_key: tuple | None = None
        best: dict[str, Any] = {}
        scores: list[float] = []
        for factors in itertools.product(FACTORS, repeat=len(rule.conditions)):
            thresholds = [t * f for t, f in zip(shipped[rule.type], factors, strict=True)]
            f1, tp, fp, fn = f1_of(thresholds)
            scores.append(f1)
            key = (-f1, sum(abs(math.log(f)) for f in factors), factors)  # max F1, then closest to shipped, then deterministic
            if best_key is None or key < best_key:
                best_key = key
                best = {"tuned": [round(t, 6) for t in thresholds], "factors": list(factors), "dev_f1_tuned": round(f1, 4),
                        "dev_tp_fp_fn_tuned": [tp, fp, fn]}
        max_f1 = max(scores)
        f1_shipped, tp0, fp0, fn0 = f1_of(shipped[rule.type])
        tuned[rule.type] = best["tuned"]
        entry.update(best, status="tuned", dev_f1_shipped=round(f1_shipped, 4), dev_tp_fp_fn_shipped=[tp0, fp0, fn0],
                     grid_points=len(scores), tied_at_max_f1=sum(1 for s in scores if abs(s - max_f1) < 1e-12),
                     changed=best["tuned"] != shipped[rule.type])
        report[rule.type] = entry
    return tuned, report


# ----------------------------------------------------------------------------- baselines (fitted on development split)


def baselines(dev: Sequence[Window], test: Sequence[Window], n_boot: int, seed: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    n_attack = sum(w.label for w in dev)
    majority = 1 if n_attack * 2 >= len(dev) else 0
    out["majority_class"] = {
        "description": "predict the majority window label of the development split for every held-out window (tie -> attack)",
        "fitted": {"dev_attack_windows": n_attack, "dev_benign_windows": len(dev) - n_attack,
                   "predicts": "attack" if majority else "benign"},
        **evaluate(test, [majority] * len(test), None, n_boot, seed),
    }
    benign_dev = [w for w in dev if w.cls == "benign"]
    if not benign_dev:
        out["rate_p99_benign"] = {"status": "skipped: no benign windows in development split"}
        out["tot_size_p1_p99_band_benign"] = {"status": "skipped: no benign windows in development split"}
        return out
    thr_rate = percentile([w.features["rate_mean"] for w in benign_dev], 99)
    assert thr_rate is not None
    out["rate_p99_benign"] = {
        "description": "single-feature baseline: flag a window when its mean Rate exceeds the 99th percentile of benign "
                       "development windows (feature scales must match between development and held-out sources)",
        "fitted": {"rate_mean_threshold": round(thr_rate, 4), "dev_benign_windows": len(benign_dev)},
        **evaluate(test, [1 if w.features["rate_mean"] > thr_rate else 0 for w in test], None, n_boot, seed),
    }
    sizes = [w.features["tot_size_mean"] for w in benign_dev]
    lo, hi = percentile(sizes, 1), percentile(sizes, 99)
    assert lo is not None and hi is not None
    out["tot_size_p1_p99_band_benign"] = {
        "description": "single-feature baseline: flag a window when its mean Tot size lies outside the 1st-99th percentile "
                       "band of benign development windows",
        "fitted": {"tot_size_mean_band": [round(lo, 4), round(hi, 4)], "dev_benign_windows": len(benign_dev)},
        **evaluate(test, [0 if lo <= w.features["tot_size_mean"] <= hi else 1 for w in test], None, n_boot, seed),
    }
    return out


# ----------------------------------------------------------------------------- orchestration


def counts(wins: Sequence[Window]) -> dict[str, Any]:
    return {"total": len(wins), "attack": sum(w.label for w in wins), "benign": sum(1 for w in wins if not w.label),
            "files": len({w.file for w in wins}), "per_class": dict(sorted(Counter(w.cls for w in wins).items()))}


def temporal_partition(per_file: Mapping[str, Sequence[Window]], dev_fraction: float) -> tuple[dict, dict]:
    dev: dict[str, list[Window]] = {}
    held: dict[str, list[Window]] = {}
    for name, wins in per_file.items():
        k = int(len(wins) * dev_fraction)
        dev[name] = list(wins[:k])
        held[name] = list(wins[k:])
    return dev, held


def _flat(per_file: Mapping[str, Sequence[Window]]) -> list[Window]:
    return [w for wins in per_file.values() for w in wins]


def run(args: argparse.Namespace) -> dict[str, Any]:
    protocol = args.protocol
    if protocol is None:
        protocol = "capture_split" if args.train_dir else None
    if protocol is None or protocol not in PROTOCOLS:
        raise SystemExit("choose --protocol capture_split|cross_source (with --train-dir and --test-dir) or temporal_split (with --test-dir)")
    if protocol in ("capture_split", "cross_source") and not args.train_dir:
        raise SystemExit(f"--protocol {protocol} requires --train-dir and --test-dir")
    if not args.test_dir:
        raise SystemExit("--test-dir is required")

    test_per_file = load_dir(args.test_dir, args.window, args.max_windows)
    eval_source = describe_source(args.test_dir, args.data_source)
    if protocol == "temporal_split":
        if not 0 < args.dev_fraction < 1:
            raise SystemExit("--dev-fraction must be in (0, 1)")
        dev_per_file, held_per_file = temporal_partition(test_per_file, args.dev_fraction)
        dev_source = (f"first {args.dev_fraction:g} of the windows of each held-out-folder file (same captures): {eval_source}")
        partition = (f"temporal within-capture split: for every file the first int(n * {args.dev_fraction:g}) of its "
                     "consecutive windows form the development set and the remaining windows the held-out set; "
                     "whole files are never shared across a boundary inside a window, but development and held-out "
                     "windows come from the same captures (weaker than a capture-level split)")
    else:
        dev_per_file = load_dir(args.train_dir, args.window, args.max_windows)
        held_per_file = test_per_file
        dev_source = describe_source(args.train_dir, args.train_data_source)
        if protocol == "capture_split":
            partition = ("capture-level split: every file (capture) belongs to exactly one split; development = all "
                         "windows of the --train-dir files, held-out = all windows of the --test-dir files")
        else:
            partition = ("cross-source split: development = all windows of the --train-dir files (one data source), "
                         "held-out = all windows of the --test-dir files (a different data source); the held-out "
                         "source is never used for threshold selection")
    dev, held = _flat(dev_per_file), _flat(held_per_file)
    if not dev or not held:
        raise SystemExit("empty development or held-out set")

    # Self-check: the threshold-substitution path reproduces the shipped evaluation exactly.
    shipped = shipped_thresholds()
    shipped_rules = ruleset(shipped)
    for w in [*dev, *held]:
        assert fired(shipped_rules, w.features) == [r["type"] for r in traffic_rules.evaluate(w.features) if r["hit"]]

    tuned, tuning_report = tune(dev)
    tuned_rules = ruleset(tuned)

    results: dict[str, Any] = {}
    for name, rules, thresholds in (("shipped_thresholds", shipped_rules, shipped), ("tuned_thresholds", tuned_rules, tuned)):
        preds, hits = rule_predictions(rules, held)
        results[name] = {"thresholds": {k: list(v) for k, v in thresholds.items()}, **evaluate(held, preds, hits, args.n_boot, args.seed)}
    results["baselines"] = baselines(dev, held, args.n_boot, args.seed)

    train_fit = {}
    for name, rules in (("shipped_thresholds", shipped_rules), ("tuned_thresholds", tuned_rules)):
        preds, hits = rule_predictions(rules, dev)
        train_fit[name] = evaluate(dev, preds, hits, 0, args.seed)

    synthetic_eval = eval_source == SYNTHETIC_SOURCE
    synthetic_dev = dev_source == SYNTHETIC_SOURCE
    caveat_parts = []
    if synthetic_eval:
        caveat_parts.append(
            "The held-out data are generated by the project's own simulator (safeguard_pq.simulation) whose traffic "
            "parameters were designed around these rules; the numbers demonstrate that the held-out protocol runs "
            "end-to-end and are NOT evidence of detection performance on real traffic. Real held-out numbers require "
            "the CICIoMT2024 CSV folders (user-downloaded, not redistributed).")
    else:
        caveat_parts.append(
            "The shipped thresholds in knowledge/traffic_rules.py were originally set by inspecting window statistics of "
            "the CICIoMT2024 test split, so the shipped-threshold row is NOT held-out on CICIoMT2024 test data and is "
            "optimistic; only the tuned-threshold row (thresholds selected on the development set, evaluated once "
            "on the held-out set) is a held-out estimate, and the baselines are fitted on the development set only.")
    if protocol == "cross_source" and synthetic_dev:
        caveat_parts.append(
            "Development data are simulator-generated; their parameters imitate the shape of CICIoMT2024 class "
            "statistics but are not samples of it, and the synthetic Rate scale is not calibrated to CICIoMT2024, "
            "so the Rate baseline does not transfer across sources.")
    if protocol == "temporal_split":
        caveat_parts.append(
            "Development and held-out windows come from the same six captures (first/last part of each file), so "
            "this protocol controls for threshold selection but not for capture-level effects; a capture-level "
            "split on the official train/test folders is the stronger test.")
    caveat_parts.append(
        "Bootstrap intervals resample windows independently although consecutive windows of one capture are "
        "correlated, so the intervals are narrower than a capture-level resampling would give. Small classes "
        "(e.g. 17 ARP-spoofing or MQTT-malformed windows in the CICIoMT2024 test split) have wide Wilson intervals.")

    return {
        "benchmark": "traffic_rules_holdout",
        "software_version": __version__,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "protocol": protocol,
        "data_source": eval_source,
        "development_source": dev_source,
        "evaluation_source": eval_source,
        "train_dir": str(args.train_dir) if args.train_dir else None,
        "test_dir": str(args.test_dir),
        "dev_fraction": args.dev_fraction if protocol == "temporal_split" else None,
        "window_rows": args.window,
        "max_windows_per_file": args.max_windows,
        "train_manifest": manifest_of(dev_per_file, args.max_windows),
        "test_manifest": manifest_of(held_per_file, args.max_windows),
        "train_windows": counts(dev),
        "test_windows": counts(held),
        "tuning": {
            "objective": "per rule: maximise F1 of the rule for its target attack class(es) vs. benign on the development "
                         "windows; every threshold multiplied by a factor from FACTORS (rule structure and comparison "
                         "operators unchanged); ties -> smallest sum |ln factor| (closest to shipped), then lexicographic",
            "factors": list(FACTORS),
            "targets": {k: list(v) for k, v in TARGETS.items()},
            "rules": tuning_report,
            "train_fit": train_fit,
        },
        "results": results,
        "method": {
            "partition": partition,
            "windowing": f"consecutive non-overlapping windows of {args.window} rows per file (traffic_rules_eval.windows); "
                         f"a trailing partial window is dropped; windows never span files; at most {args.max_windows} windows "
                         "per file (cap_reached in the manifests)",
            "labels": "file name containing 'benign' -> benign, otherwise attack; class from CICIoMT2024 file-name keywords "
                      "(catalog.REPLAY_FILES tokens) or the cleaned file stem",
            "features": "per-window means of the CICIoMT2024 columns used by traffic_rules.features_from_rows",
            "prediction": "a window is predicted 'attack' when any of the five rules fires (same decision the TrafficAnomalyAgent uses)",
            "metrics": "window-level precision, recall, F1 and false-positive rate on the held-out set; per-class detection "
                       "rate (benign: false-positive rate) with Wilson 95 % intervals (z = 1.96); per-file summaries; "
                       "confusion matrix; target_rule_rate = share of a class's windows on which the rule designated for "
                       "that class fired",
            "confidence_intervals": f"percentile bootstrap over held-out windows, {args.n_boot} resamples with replacement, "
                                    f"seed {args.seed}, 2.5/97.5 percentiles (resamples with an undefined metric are dropped "
                                    "and counted in valid_resamples); Wilson score intervals for proportions; no scipy",
            "baselines": "majority class of the development split; mean Rate > 99th percentile of benign development windows; "
                         "mean Tot size outside the 1st-99th percentile band of benign development windows",
            "single_evaluation": "the held-out set is evaluated once, after all thresholds and baselines are fixed on the development set",
        },
        "caveat": " ".join(caveat_parts),
    }


def _fmt_metric(block: Mapping[str, Any], key: str) -> str:
    v = block["metrics"].get(key)
    ci = (block.get("bootstrap") or {}).get("ci95", {}).get(key)
    if v is None:
        return "n/a"
    return f"{v:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]" if ci else f"{v:.3f}"


def print_summary(result: Mapping[str, Any]) -> None:
    print(f"\nprotocol={result['protocol']}  development={result['development_source']}  held-out={result['evaluation_source']}")
    print(f"development windows: {result['train_windows']['total']}  held-out windows: {result['test_windows']['total']}")
    print(f"{'predictor':34s} {'precision':24s} {'recall':24s} {'F1':24s} {'FPR':24s}")
    rows = [("rules / shipped thresholds", result["results"]["shipped_thresholds"]),
            ("rules / tuned thresholds", result["results"]["tuned_thresholds"])]
    rows += [(f"baseline / {k}", v) for k, v in result["results"]["baselines"].items() if "metrics" in v]
    for name, block in rows:
        print(f"{name:34s} {_fmt_metric(block, 'precision'):24s} {_fmt_metric(block, 'recall'):24s} "
              f"{_fmt_metric(block, 'f1'):24s} {_fmt_metric(block, 'fpr'):24s}")
    print("\nper-class detection (tuned thresholds, held-out), Wilson 95 %:")
    for cls, e in result["results"]["tuned_thresholds"]["per_class"].items():
        w = e["wilson95"]
        print(f"  {cls:22s} {e['flagged']:5d}/{e['windows']:<5d} {e['rate']:.3f} [{w[0]:.3f}, {w[1]:.3f}]  {e.get('rule_hits', {})}")
    print("\ntuned vs shipped thresholds:")
    for rule, e in result["tuning"]["rules"].items():
        print(f"  {rule:26s} shipped={e['shipped']} tuned={e.get('tuned')} factors={e.get('factors')} ({e['status']})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train-dir", type=Path, default=None, help="development split folder (capture_split / cross_source)")
    ap.add_argument("--test-dir", type=Path, required=True, help="held-out folder (temporal_split: the folder to partition)")
    ap.add_argument("--protocol", choices=PROTOCOLS, default=None,
                    help="capture_split (default when --train-dir is given), cross_source or temporal_split")
    ap.add_argument("--dev-fraction", type=float, default=0.5, help="temporal_split: share of each file's windows used for development")
    ap.add_argument("--window", type=int, default=100)
    ap.add_argument("--max-windows", type=int, default=2000, help="cap on windows per file")
    ap.add_argument("--seed", type=int, default=0, help="bootstrap seed")
    ap.add_argument("--n-boot", type=int, default=1000, help="bootstrap resamples")
    ap.add_argument("--data-source", default=None, help="override the auto-detected held-out data source label")
    ap.add_argument("--train-data-source", default=None, help="override the auto-detected development data source label")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "traffic_rules_holdout.json")
    args = ap.parse_args(argv)

    result = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print_summary(result)
    print(f"\nWritten: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
