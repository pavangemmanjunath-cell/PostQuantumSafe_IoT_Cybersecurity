"""Heuristic network-traffic anomaly rules over CICIoMT2024-style flow features.

Features use the CICIoMT2024 column names (e.g. ``syn_flag_number``, ``Rate``,
``Tot size``). Thresholds were set by inspecting window means of the public
CICIoMT2024 *test* split and are therefore optimistic on that data; see
``benchmarks/README.md``. This is a transparent rule baseline, not a validated
intrusion-detection model.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

FEATURE_COLUMNS = {
    "syn_ratio": "syn_flag_number",
    "ack_ratio": "ack_flag_number",
    "rst_ratio": "rst_flag_number",
    "fin_ratio": "fin_flag_number",
    "tcp_ratio": "TCP",
    "udp_ratio": "UDP",
    "rate_mean": "Rate",
    "tot_size_mean": "Tot size",
    "header_length_mean": "Header_Length",
}


@dataclass(frozen=True)
class TrafficRule:
    type: str
    severity: str
    pillars: tuple[str, ...]
    description: str
    conditions: tuple[tuple[str, str, float], ...]  # (feature, op, threshold)

    def evaluate(self, f: Mapping[str, float]) -> tuple[bool, list[str]]:
        reasons, ok = [], True
        for feat, op, thr in self.conditions:
            v = f.get(feat)
            hit = v is not None and (v >= thr if op == ">=" else v <= thr if op == "<=" else v < thr)
            ok &= hit
            reasons.append(f"{feat}={_fmt(v)} {op} {_fmt(thr)} → {'yes' if hit else 'no'}")
        return ok, reasons


def _fmt(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:.4g}"


TRAFFIC_RULES: list[TrafficRule] = [
    TrafficRule(
        "volumetric_flood_pattern", "critical", ("Safety", "Security"),
        "Header-only TCP packets with no ACKs (handshake-less flood, DDoS-like)",
        (("tcp_ratio", ">=", 0.99), ("ack_ratio", "<=", 0.01), ("tot_size_mean", "<=", 60.0),
         ("header_length_mean", "<=", 1000.0)),
    ),
    TrafficRule(
        "syn_flood_pattern", "critical", ("Safety", "Security"),
        "SYN-dominated tiny packets (SYN flood / DoS-like)",
        (("syn_ratio", ">=", 0.6), ("tot_size_mean", "<=", 80.0)),
    ),
    TrafficRule(
        "port_scan_pattern", "high", ("Security", "Trust"),
        "SYN probes answered by RST with small packets (reconnaissance-like)",
        (("syn_ratio", ">=", 0.15), ("syn_ratio", "<", 0.6), ("rst_ratio", ">=", 0.1), ("tot_size_mean", "<=", 250.0)),
    ),
    TrafficRule(
        "protocol_flag_anomaly", "medium", ("Security", "Protection"),
        "Elevated SYN/FIN/RST control-flag share on TCP sessions (malformed-protocol-like, e.g. MQTT)",
        (("control_flag_ratio", ">=", 0.03), ("tcp_ratio", ">=", 0.8), ("syn_ratio", "<", 0.15)),
    ),
    TrafficRule(
        "protocol_mix_anomaly", "high", ("Identity", "Trust", "Security"),
        "UDP-heavy, mid-size packets with low ACK share (possible MITM / ARP-spoofing relay); weak evidence",
        (("udp_ratio", ">=", 0.3), ("tot_size_mean", ">=", 200.0), ("tot_size_mean", "<=", 1000.0),
         ("ack_ratio", "<=", 0.6)),
    ),
]


def features_from_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    sums: dict[str, float] = {k: 0.0 for k in FEATURE_COLUMNS}
    n = 0
    for row in rows:
        n += 1
        for feat, col in FEATURE_COLUMNS.items():
            try:
                sums[feat] += float(row.get(col, 0) or 0)
            except (TypeError, ValueError):
                pass
    if n == 0:
        return {}
    f = {k: v / n for k, v in sums.items()}
    f["control_flag_ratio"] = f["syn_ratio"] + f["fin_ratio"] + f["rst_ratio"]
    f["rows"] = float(n)
    return f


def features_from_summary(summary: Mapping[str, Any]) -> dict[str, float]:
    """Accepts the per-column ``{"mean": …}`` summary produced by the CSV ingest adapter."""
    f: dict[str, float] = {}
    for feat, col in FEATURE_COLUMNS.items():
        entry = summary.get(col)
        if isinstance(entry, Mapping) and "mean" in entry:
            f[feat] = float(entry["mean"])
    if not f:
        return {}
    for k in ("syn_ratio", "fin_ratio", "rst_ratio"):
        f.setdefault(k, 0.0)
    f["control_flag_ratio"] = f["syn_ratio"] + f["fin_ratio"] + f["rst_ratio"]
    return f


def extract_features(iot_traffic: Mapping[str, Any] | None) -> dict[str, float]:
    if not iot_traffic:
        return {}
    if isinstance(iot_traffic.get("features"), Mapping):
        f = {k: float(v) for k, v in iot_traffic["features"].items() if isinstance(v, int | float)}
        if f:
            f.setdefault("control_flag_ratio", f.get("syn_ratio", 0) + f.get("fin_ratio", 0) + f.get("rst_ratio", 0))
        return f
    if isinstance(iot_traffic.get("window"), list):
        return features_from_rows(iot_traffic["window"])
    if isinstance(iot_traffic.get("feature_summary"), Mapping):
        return features_from_summary(iot_traffic["feature_summary"])
    return {}


def evaluate(features: Mapping[str, float]) -> list[dict[str, Any]]:
    out = []
    for rule in TRAFFIC_RULES:
        hit, reasons = rule.evaluate(features)
        out.append({"type": rule.type, "hit": hit, "severity": rule.severity, "pillars": list(rule.pillars),
                    "description": rule.description, "reasons": reasons})
    return out
