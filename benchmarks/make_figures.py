"""Generate the Release 3 result figures from the committed benchmark artifacts.

    python benchmarks/make_figures.py            # writes docs/release-3/figures/fig_e*.svg, .pdf and .png

Figures are drawn at their final printed size (single column 3.5 in, double column 7.16 in) with 7-8 pt text and no
text below 6.5 pt, without in-figure titles (the captions in docs/release-3 carry them), as vector SVG and PDF
(TrueType fonts embedded) plus 300-dpi PNG. Every figure is drawn from a JSON file in benchmarks/results/; figures
whose artifact is missing are skipped. Requires matplotlib (optional ``benchmark`` extra).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks" / "results"
OUT = ROOT / "docs" / "release-3" / "figures"

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
except ImportError as exc:  # pragma: no cover - documented optional dependency
    raise SystemExit("matplotlib is required: pip install -e 'backend[benchmark]'") from exc

PALETTE = ["#1f3b73", "#7a9cc6", "#9e9e9e", "#d9833b", "#4c9a6a"]
SINGLE, DOUBLE = 3.5, 7.16  # printed widths in inches (typical journal single / double column)
SMALL = 6.5  # smallest text size used anywhere (pt)


def _style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "figure.titlesize": 8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
        "ytick.major.width": 0.6, "lines.linewidth": 1.0, "lines.markersize": 3.5, "legend.frameon": False,
        "figure.constrained_layout.use": True, "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    })


def _load(name: str) -> dict | None:
    p = RESULTS / name
    if not p.exists():
        print(f"skip: {p.name} not found")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(fig: plt.Figure, stem: str) -> None:
    """Journal export: vector SVG and PDF for typesetting, 300-dpi PNG for previews and Word."""
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.svg")
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.png", dpi=300)
    w, h = fig.get_size_inches()
    plt.close(fig)
    print(f"written: {stem}.svg / .pdf / .png ({w:.2f} x {h:.2f} in)")


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# --------------------------------------------------------------------------- E3: optimizer, small n


def fig_e3_optimizer() -> None:
    d = _load("qiro_optimality.json")
    if not d:
        return
    methods = [("Annealing only", d["annealing_only"]), ("Annealing + local search", d["annealing_plus_local_search"])]
    colors = [PALETTE[1], PALETTE[0]]
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE, 2.3))
    ax = axes[0]
    xs = list(range(len(methods)))
    vals = [100 * m["optimal_share"] for _, m in methods]
    ax.bar(xs, vals, color=colors, width=0.55)
    for x, v in zip(xs, vals, strict=True):
        ax.text(x, v + 1.5, f"{v:.1f} %", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(xs, ["Annealing only", "Annealing +\nlocal search"])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Instances solved optimally (%)")
    ax.set_title(f"(a) Optimal share (N = {d['instances_with_nonzero_optimum']}, n ≤ 14)", loc="left")
    ax = axes[1]
    keys = [("mean_gap_pct", "Mean"), ("p95_gap_pct", "95th percentile"), ("max_gap_pct", "Maximum")]
    w = 0.38
    for i, (name, m) in enumerate(methods):
        v = [m[k] for k, _ in keys]
        bars = ax.bar([j + (i - 0.5) * w for j in range(len(keys))], v, width=w, color=colors[i], label=name)
        for b, val in zip(bars, v, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.3, f"{val:.2f}", ha="center", va="bottom", fontsize=SMALL)
    ax.set_xticks(range(len(keys)), [lbl for _, lbl in keys])
    ax.set_ylim(0, 1.15 * max(m["max_gap_pct"] for _, m in methods))
    ax.set_ylabel("Gap to exhaustive optimum (%)")
    ax.set_title("(b) Gap distribution", loc="left")
    ax.legend(loc="upper left")
    _save(fig, "fig_e3_optimizer_small_n")


# --------------------------------------------------------------------------- E6 / E10: traffic rules

SHORT_FILE = {
    "ARP_Spoofing": "ARP spoof.", "Benign": "Benign", "MQTT-Malformed_Data": "MQTT malf.", "Recon-Port_Scan": "Port scan",
    "TCP_IP-DDoS-TCP": "DDoS-TCP", "TCP_IP-DoS-SYN": "DoS-SYN",
}


def fig_e6_traffic() -> None:
    d = _load("traffic_rules_eval.json")
    if not d:
        return
    rows = d["results"]
    labels = [SHORT_FILE.get(r["file"].replace("_test.pcap.csv", ""), r["file"]) for r in rows]
    rates = [100 * r["flagged_windows"] / r["windows"] for r in rows]
    lo, hi = [], []
    for r, rate in zip(rows, rates, strict=True):
        a, b = wilson(r["flagged_windows"], r["windows"])
        lo.append(max(0.0, rate - 100 * a))
        hi.append(max(0.0, 100 * b - rate))
    colors = [PALETTE[3] if r["expected"] == "benign" else PALETTE[0] for r in rows]
    fig, ax = plt.subplots(figsize=(SINGLE, 2.5))
    ax.bar(range(len(rows)), rates, color=colors, width=0.6, yerr=[lo, hi], capsize=2, error_kw={"lw": 0.6})
    for i, (r, v) in enumerate(zip(rows, rates, strict=True)):
        ax.text(i, min(v + hi[i] + 2, 104), f"{v:.1f}\nn={r['windows']}", ha="center", va="bottom", fontsize=SMALL)
    ax.set_xticks(range(len(rows)), labels, rotation=35, ha="right")
    ax.set_ylim(0, 125)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Flagged windows (%)")
    ax.legend(handles=[Patch(color=PALETTE[0], label="attack: detection rate"),
                       Patch(color=PALETTE[3], label="benign: false-positive rate")],
              loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=SMALL)
    _save(fig, "fig_e6_traffic_same_split")


def fig_e10_traffic_holdout() -> None:
    runs = [(label, _load(name)) for label, name in (
        ("(a) Synthetic → synthetic", "traffic_rules_holdout.json"),
        ("(b) P1 cross-source → CICIoMT2024", "traffic_rules_holdout_cic_p1.json"),
        ("(c) P2 temporal split, CICIoMT2024", "traffic_rules_holdout_cic_p2.json"),
    )]
    runs = [(lbl, d) for lbl, d in runs if d]
    if not runs:
        return
    base_labels = {"majority_class": "baseline: majority class", "rate_p99_benign": "baseline: Rate > benign p99",
                   "tot_size_p1_p99_band_benign": "baseline: size outside benign p1–p99"}
    metrics = ["precision", "recall", "f1"]
    fig, axes = plt.subplots(1, len(runs), figsize=(DOUBLE, 2.8), squeeze=False, sharey=True)
    for ax, (label, d) in zip(axes[0], runs, strict=True):
        res = d["results"]
        series = [("rules, shipped thresholds", res["shipped_thresholds"]),
                  ("rules, tuned on development split", res["tuned_thresholds"])]
        series += [(base_labels.get(k, k), v) for k, v in res.get("baselines", {}).items()]
        w = 0.8 / len(series)
        for i, (name, s) in enumerate(series):
            vals = [s["metrics"][m] for m in metrics]
            ci = s.get("bootstrap", {}).get("ci95", {})
            lo = [max(0.0, s["metrics"][m] - ci[m][0]) if m in ci else 0 for m in metrics]
            hi = [max(0.0, ci[m][1] - s["metrics"][m]) if m in ci else 0 for m in metrics]
            ax.bar([j + (i - (len(series) - 1) / 2) * w for j in range(3)], vals, width=w, label=name,
                   color=PALETTE[i % len(PALETTE)], yerr=[lo, hi], capsize=1.2, error_kw={"lw": 0.5})
        ax.set_xticks(range(3), ["Precision", "Recall", "F1"])
        ax.set_ylim(0, 1.1)
        ax.set_title(label, loc="left")
        ax.text(0.02, 0.985, f"held-out windows: {res['tuned_thresholds']['windows']}", transform=ax.transAxes,
                fontsize=SMALL, va="top")
    axes[0][0].set_ylabel("Window-level score")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3)
    _save(fig, "fig_e10_traffic_holdout")


# --------------------------------------------------------------------------- E7: sensitivity


def fig_e7_sensitivity() -> None:
    d = _load("sensitivity_analysis.json")
    if not d:
        return
    designs = d["designs"]
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE, 3.9), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    rows: list[tuple[str, float, float, float]] = []
    entries = [e for key in ("S1_category_weights", "S2_severity_points", "S3_pillar_deductions",
                             "S5_optimizer_pillar_weights") for e in designs.get(key, [])]
    entries += designs.get("S4_lifetime_threshold", {}).get("configs", [])
    for e in entries:
        m = e["metrics"]
        rows.append((e["config"].replace(" x", " ×"), float(m["max_abs_delta_score"]), 100 * float(m["verdict_change_share"]),
                     100 * float(m["status_change_share"])))
    rows.sort(key=lambda r: (r[1], r[2]))
    ys = list(range(len(rows)))
    ax.barh(ys, [r[1] for r in rows], color=PALETTE[1], height=0.65, label="max |ΔS| (points, bottom axis)")
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=SMALL)
    ax.set_xlabel("Max |ΔS| over the ten systems (points)")
    ax.set_title("(a) Perturbations of the scoring constants", loc="left")
    ax2 = ax.twiny()
    ax2.plot([r[2] for r in rows], ys, "o", color=PALETTE[0], label="verdict changes (%, top axis)")
    ax2.plot([r[3] for r in rows], ys, "x", color=PALETTE[3], label="status changes (%, top axis)")
    ax2.set_xlim(0, 105)
    ax2.set_xlabel("Systems whose verdict / status changes (%)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=SMALL)
    ax = axes[1]
    s4 = designs.get("S4_lifetime_threshold", {})
    ls = [int(x) for x in s4.get("thresholds_years", [5, 10, 15, 20])]
    for i, row in enumerate(s4.get("per_scenario", [])):
        scores = [row["by_threshold"][str(L)]["pq_risk_score"] for L in ls]
        ax.plot(ls, scores, marker="o", color=PALETTE[i % len(PALETTE)], ls=["-", "--"][i // 5], alpha=0.9,
                label=f"{row['scenario']} ({row['data_lifetime_years']:g} y)")
    ax.axvline(10, color="#999", lw=0.6, ls=":")
    ax.text(10.25, 93, "default L", fontsize=SMALL, color="#555")
    ax.set_xticks(ls)
    ax.set_ylim(-3, 100)
    ax.set_xlabel("Lifetime threshold L (years)")
    ax.set_ylabel("PQ risk score S")
    ax.set_title("(b) Lifetime-threshold sweep", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=SMALL, title="scenario (data lifetime)",
              title_fontsize=SMALL)
    _save(fig, "fig_e7_sensitivity")


# --------------------------------------------------------------------------- E8: scalability


def fig_e8_scalability() -> None:
    d = _load("qiro_scalability.json")
    if not d:
        return
    entries = sorted(((int(k), v) for k, v in d["by_size"].items()), key=lambda kv: kv[0])
    ns = [n for n, _ in entries]
    methods = [("greedy", "greedy only"), ("annealing", "greedy + annealing"),
               ("greedy_local_search", "greedy + local search"), ("annealing_local_search", "shipped (greedy + annealing + local search)")]
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE, 2.7))
    ax = axes[0]
    for i, (key, label) in enumerate(methods):
        ax.plot(ns, [100 * v["methods"][key]["optimal_share"] for _, v in entries], marker="o", color=PALETTE[i], label=label)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Solved to ILP optimum (%)")
    ax.set_title("(a) Optimal share", loc="left")
    ax = axes[1]
    for i, (key, _) in enumerate(methods):
        ax.plot(ns, [v["methods"][key]["mean_gap_pct"] for _, v in entries], marker="o", color=PALETTE[i])
        ax.plot(ns, [v["methods"][key]["max_gap_pct"] for _, v in entries], marker="x", ls="--", lw=0.7, color=PALETTE[i])
    ax.set_ylabel("Gap to ILP optimum (%)")
    ax.set_title("(b) Mean (—) and max (--) gap", loc="left")
    ax = axes[2]
    ax.plot(ns, [v["methods"]["annealing_local_search"]["mean_runtime_ms"] for _, v in entries], marker="o", color=PALETTE[3],
            label="shipped")
    ax.plot(ns, [v["methods"]["greedy_local_search"]["mean_runtime_ms"] for _, v in entries], marker="^", color=PALETTE[2],
            label="greedy + LS")
    ax.plot(ns, [v["methods"]["ilp"]["mean_runtime_ms"] for _, v in entries], marker="s", color=PALETTE[0], label="ILP (HiGHS)")
    ax.set_yscale("log")
    ax.set_ylabel("Mean runtime (ms)")
    ax.set_title("(c) Runtime", loc="left")
    ax.legend(loc="upper left", fontsize=SMALL)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks(ns, [str(n) for n in ns])
        ax.minorticks_off()
        ax.set_xlabel("Candidate actions n")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=2)
    _save(fig, "fig_e8_scalability")


# --------------------------------------------------------------------------- E9: reassessment


def fig_e9_reassessment() -> None:
    d = _load("plan_reassessment.json")
    if not d:
        return
    systems = d["systems"]
    names = [s["scenario"] for s in systems]
    series = (
        ([s["baseline"]["pq_risk_score"] for s in systems], "baseline S", PALETTE[2]),
        ([s["plan_a"]["projected_pq_score"] for s in systems], "plan A projected", "#c7d4e8"),
        ([s["plan_a"]["reassessed_pq_score"] for s in systems], "plan A reassessed", PALETTE[0]),
        ([s["plan_b"]["projected_pq_score"] for s in systems], "plan B projected", "#f3cfae"),
        ([s["plan_b"]["reassessed_pq_score"] for s in systems], "plan B reassessed", PALETTE[3]),
    )
    fig, ax = plt.subplots(figsize=(DOUBLE, 3.0))
    w = 0.16
    xs = range(len(systems))
    for i, (vals, label, col) in enumerate(series):
        ax.bar([x + (i - 2) * w for x in xs], vals, width=w, color=col, label=label, edgecolor="#333", linewidth=0.25)
    for x, s in zip(xs, systems, strict=True):
        st = s["plan_a"]["reassessed_status"]
        ax.text(x, max(series[0][0][x], 1) + 3, st.replace("_", " "), ha="center", fontsize=SMALL,
                color=PALETTE[4] if st == "SAFE" else PALETTE[3])
    ax.set_xticks(list(xs), names, rotation=30, ha="right", fontsize=SMALL)
    ax.set_ylabel("PQ risk score S")
    ax.set_ylim(0, 100)
    fig.legend(loc="outside lower center", ncol=5)
    _save(fig, "fig_e9_reassessment")


# --------------------------------------------------------------------------- E11: attack simulation


def fig_e11_attacks() -> None:
    d = _load("attack_simulation.json")
    if not d:
        return
    attacks = d["attacks"]
    names = list(attacks)
    bars = [("detection_rate", "detected (new finding from the expected agent)", PALETTE[0]),
            ("flagged_after_attack_rate", "any finding present after the attack", PALETTE[1]),
            ("mitigation_restored_status_rate", "mitigation restores status ≤ baseline", PALETTE[4]),
            ("reinjection_blocked_rate", "re-injection blocked after mitigation", PALETTE[3])]
    fig, (ax, axk) = plt.subplots(2, 1, figsize=(DOUBLE, 5.0), gridspec_kw={"height_ratios": [1.5, 1]})
    w = 0.2
    xs = range(len(names))
    for i, (key, label, col) in enumerate(bars):
        ax.bar([x + (i - 1.5) * w for x in xs], [100 * attacks[a][key] for a in names], width=w, color=col, label=label)
    for x, a in zip(xs, names, strict=True):
        ax.text(x, 103, str(attacks[a]["exploitable_runs"]), ha="center", fontsize=SMALL, color="#444")
    ax.set_xticks(list(xs), names, rotation=35, ha="right", fontsize=SMALL)
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Share of exploitable runs (%)")
    ax.set_title("(a) Outcome per attack (numbers above bars: exploitable runs over devices × seeds)", loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.42), ncol=2, fontsize=SMALL)
    traj = d["kill_chain"]["trajectory"]
    steps = [t["step"] for t in traj]
    axk.plot(range(len(steps)), [t["mean_pq_risk_score"] for t in traj], marker="o", color=PALETTE[0],
             label="fleet mean PQ risk score (left axis)")
    axk.set_ylabel("Fleet mean S")
    axk.set_ylim(0, max(45, 1.2 * max(t["mean_pq_risk_score"] for t in traj)))
    ax2 = axk.twinx()
    ax2.bar(range(len(steps)), [t["unsafe"] for t in traj], width=0.5, color=PALETTE[3], alpha=0.35,
            label="devices UNSAFE (right axis)")
    ax2.set_ylabel(f"UNSAFE devices (of {len(d['devices'])})")
    ax2.set_ylim(0, len(d["devices"]) + 1)
    ax2.spines["right"].set_visible(True)
    axk.set_xticks(range(len(steps)), steps)
    axk.set_title(f"(b) ICU Q-Day drill on {d['kill_chain']['drill_device']} (seed {d['kill_chain']['seed']})", loc="left")
    h1, l1 = axk.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axk.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=SMALL)
    _save(fig, "fig_e11_attack_simulation")


def main() -> int:
    _style()
    for f in (fig_e3_optimizer, fig_e6_traffic, fig_e7_sensitivity, fig_e8_scalability, fig_e9_reassessment,
              fig_e10_traffic_holdout, fig_e11_attacks):
        try:
            f()
        except (KeyError, TypeError, ValueError) as exc:  # schema mismatch: report, keep going
            print(f"warning: {f.__name__} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
