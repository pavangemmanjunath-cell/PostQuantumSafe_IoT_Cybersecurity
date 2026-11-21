"""Held-out traffic-rule evaluation helpers and the synthetic dataset generator (benchmarks/)."""

from __future__ import annotations

import csv
import importlib
import json
import sys
from pathlib import Path

import pytest

from safeguard_pq.knowledge import traffic_rules

BENCH = Path(__file__).resolve().parents[3] / "benchmarks"


def _load(name: str):
    if str(BENCH) not in sys.path:
        sys.path.insert(0, str(BENCH))
    return importlib.import_module(name)


@pytest.fixture(scope="module")
def holdout():
    return _load("traffic_rules_holdout")


@pytest.fixture(scope="module")
def generator():
    return _load("make_synthetic_traffic_dataset")


def test_wilson_interval_known_values(holdout) -> None:
    lo, hi = holdout.wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-3) and hi == pytest.approx(0.7634, abs=1e-3)
    lo, hi = holdout.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = holdout.wilson(10, 10)
    assert lo == pytest.approx(0.7225, abs=1e-3) and hi == 1.0
    assert holdout.wilson(3, 3) == (pytest.approx(0.4385, abs=1e-3), 1.0)
    assert holdout.wilson(0, 0) is None


def test_bootstrap_is_deterministic_for_a_seed(holdout) -> None:
    codes = [holdout.TP] * 30 + [holdout.FP] * 5 + [holdout.TN] * 50 + [holdout.FN] * 15
    a = holdout.bootstrap_ci(codes, 200, seed=0)
    assert a == holdout.bootstrap_ci(codes, 200, seed=0)
    assert a["resamples"] == 200 and a["valid_resamples"]["recall"] == 200
    assert a["ci95"]["recall"][0] <= 30 / 45 <= a["ci95"]["recall"][1]
    assert a["ci95"]["fpr"][0] <= 5 / 55 <= a["ci95"]["fpr"][1]
    assert holdout.bootstrap_ci(codes, 200, seed=1)["ci95"] != a["ci95"]


def test_precision_recall_f1_on_toy_confusion(holdout) -> None:
    m = holdout.prf(tp=3, fp=1, tn=10, fn=2)
    assert m["precision"] == pytest.approx(0.75)
    assert m["recall"] == pytest.approx(0.6)
    assert m["f1"] == pytest.approx(2 / 3)
    assert m["fpr"] == pytest.approx(1 / 11)
    assert holdout.prf(0, 0, 5, 0) == {"precision": None, "recall": None, "f1": None, "fpr": 0.0}
    codes = holdout.outcome_codes([1, 1, 0, 0, 1], [1, 0, 1, 0, 1])
    assert holdout.confusion(codes) == {"tp": 2, "fp": 1, "tn": 1, "fn": 1}


def test_percentile_uses_linear_interpolation(holdout) -> None:
    assert holdout.percentile([4, 1, 3, 2], 50) == 2.5
    assert holdout.percentile([1, 2, 3, 4], 99) == pytest.approx(3.97)
    assert holdout.percentile([5], 1) == 5
    assert holdout.percentile([], 50) is None


def test_class_inference_from_file_names(holdout) -> None:
    assert holdout.infer_class("Benign_test.pcap.csv") == "benign"
    assert holdout.infer_class("TCP_IP-DoS-SYN_test.pcap.csv") == "syn_flood"
    assert holdout.infer_class("TCP_IP-DDoS-TCP1_train.pcap.csv") == "ddos_volumetric"
    assert holdout.infer_class("TCP_IP-DDoS-SYN_test.pcap.csv") == "TCP_IP-DDoS-SYN"  # distinct CIC class, not merged
    assert holdout.infer_class("Recon-Port_Scan_test.pcap.csv") == "port_scan"
    assert holdout.infer_class("MQTT-Malformed_Data_test.pcap.csv") == "mqtt_malformed"
    assert holdout.infer_class("ARP_Spoofing_train.pcap.csv") == "arp_spoofing"
    assert holdout.infer_class("mqtt_malformed.csv") == "mqtt_malformed"  # synthetic dataset naming


def test_threshold_substitution_matches_shipped_evaluation(holdout) -> None:
    feats = {"syn_ratio": 0.9, "ack_ratio": 0.3, "rst_ratio": 0.1, "fin_ratio": 0.0, "tcp_ratio": 1.0, "udp_ratio": 0.0,
             "rate_mean": 5000.0, "tot_size_mean": 55.0, "header_length_mean": 90.0, "control_flag_ratio": 1.0}
    shipped = holdout.ruleset(holdout.shipped_thresholds())
    assert holdout.fired(shipped, feats) == [r["type"] for r in traffic_rules.evaluate(feats) if r["hit"]] == ["syn_flood_pattern"]
    loosened = holdout.with_thresholds(traffic_rules.TRAFFIC_RULES[1], [0.95, 80.0])  # syn_ratio >= 0.95 no longer fires
    assert loosened.evaluate(feats)[0] is False
    assert traffic_rules.TRAFFIC_RULES[1].conditions[0][2] == 0.6  # shipped rules untouched


def test_generator_writes_expected_files(generator, tmp_path) -> None:
    out = tmp_path / "ds"
    assert generator.main(["--out", str(out), "--windows-per-class", "2", "--window", "50"]) == 0
    for split in ("train", "test"):
        for cls in generator.CLASSES:
            with (out / split / f"{cls}.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            assert len(rows) == 100 and list(rows[0]) == generator.COLUMNS
            assert {r["window_id"] for r in rows} == {"0", "1"}
            assert all(r["TCP"] in ("0.0", "1.0") and r["UDP"] in ("0.0", "1.0") for r in rows)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True and "safeguard_pq" in manifest["generator"]
    assert manifest["splits"]["train"]["seed"] != manifest["splits"]["test"]["seed"]
    assert manifest["splits"]["test"]["jitter"] == 0.1 and manifest["splits"]["train"]["jitter"] == 0.0
    assert (out / "README.md").read_text(encoding="utf-8").startswith("# Synthetic held-out traffic dataset")
    out2 = tmp_path / "ds2"
    generator.main(["--out", str(out2), "--windows-per-class", "2", "--window", "50"])
    assert (out / "test" / "syn_flood.csv").read_bytes() == (out2 / "test" / "syn_flood.csv").read_bytes()


def test_holdout_main_runs_on_tiny_synthetic_dataset(generator, holdout, tmp_path) -> None:
    ds = tmp_path / "ds"
    generator.main(["--out", str(ds), "--windows-per-class", "2", "--window", "50"])
    out = tmp_path / "holdout.json"
    argv = ["--train-dir", str(ds / "train"), "--test-dir", str(ds / "test"), "--window", "50", "--n-boot", "50", "--out", str(out)]
    assert holdout.main(argv) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["benchmark"] == "traffic_rules_holdout" and r["protocol"] == "capture_split"
    assert r["data_source"] == "synthetic_simulator" and r["development_source"] == "synthetic_simulator"
    assert r["test_windows"]["total"] == 12 and r["train_windows"]["total"] == 12 and len(r["test_manifest"]) == 6
    assert {m["label"] for m in r["train_manifest"]} == {"benign", "attack"}
    for key in ("shipped_thresholds", "tuned_thresholds"):
        block = r["results"][key]
        assert set(block["confusion"]) == {"tp", "fp", "tn", "fn"} and block["bootstrap"]["resamples"] == 50
        assert block["metrics"]["recall"] is not None and set(block["per_class"]) == set(generator.CLASSES)
        assert len(block["per_class"]["benign"]["wilson95"]) == 2
    assert set(r["results"]["baselines"]) == {"majority_class", "rate_p99_benign", "tot_size_p1_p99_band_benign"}
    assert set(r["tuning"]["rules"]) == {rule.type for rule in traffic_rules.TRAFFIC_RULES}
    assert all(e["status"] == "tuned" for e in r["tuning"]["rules"].values())
    assert "simulator" in r["caveat"]

    out2 = tmp_path / "temporal.json"
    argv2 = ["--protocol", "temporal_split", "--test-dir", str(ds / "test"), "--dev-fraction", "0.5", "--window", "50",
             "--n-boot", "20", "--out", str(out2)]
    assert holdout.main(argv2) == 0
    r2 = json.loads(out2.read_text(encoding="utf-8"))
    assert r2["protocol"] == "temporal_split" and r2["dev_fraction"] == 0.5
    assert r2["train_windows"]["total"] == 6 and r2["test_windows"]["total"] == 6
    assert all(m["window_range"] == [0, 0] for m in r2["train_manifest"])
    assert all(m["window_range"] == [1, 1] for m in r2["test_manifest"])
