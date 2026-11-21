"""Generate the Release 3 result figures from the committed benchmark artifacts.

    python benchmarks/make_figures.py            # writes docs/release-3/figures/fig_*.png and .svg

Every figure is drawn from a JSON file in benchmarks/results/; figures whose artifact is
missing are skipped with a message, so the script runs on a partial set of results.
Requires the optional ``benchmark`` extra (matplotlib).
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
except ImportError as exc:  # pragma: no cover - documented optional dependency
    raise SystemExit("matplotlib is required: pip install -e 'backend[benchmark]'") from exc

PALETTE = ["#1f3b73", "#7a9cc6", "#b6b6b6", "#d9833b", "#4c9a6a"]


def _style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.8, "xtick.major.width": 0.8,
        "ytick.major.width": 0.8, "legend.frameon": False, "legend.fontsize": 8, "figure.dpi": 200,
        "savefig.dpi": 200, "savefig.bbox": "tight", "figure.constrained_layout.use": True,
    })


def _load(name: str) -> dict | None:
    p = RESULTS / name
    if not p.exists():
        print(f"skip: {p.name} not found")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save(fig: plt.Figure, stem: str) -> None:
    """Journal export: vector SVG and PDF for typesetting, 300-dpi PNG for previews."""
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.svg")
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.png", dpi=300)
    plt.close(fig)
    print(f"written: {stem}.svg / .pdf / .png")


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
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.7))
    ax = axes[0]
    xs = range(len(methods))
    ax.bar(xs, [100 * m["optimal_share"] for _, m in methods], color=[PALETTE[1], PALETTE[0]], width=0.55)
    for x, (_, m) in zip(xs, methods, strict=True):
        ax.text(x, 100 * m["optimal_share"] + 1, f"{100 * m['optimal_share']:.1f} %", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(xs), [n for n, _ in methods])
    ax.set_ylim(0, 110)
    ax.set_ylabel("Instances solved optimally (%)")
    ax.set_title(f"(a) Optimal share, N = {d['instances_with_nonzero_optimum']}, n ∈ [3, 14]")
    ax = axes[1]
    keys = [("mean_gap_pct", "mean"), ("p95_gap_pct", "p95"), ("max_gap_pct", "max")]
    w = 0.38
    for i, (name, m) in enumerate(methods):
        vals = [m[k] for k, _ in keys]
        bars = ax.bar([j + (i - 0.5) * w for j in range(len(keys))], vals, width=w, color=[PALETTE[1], PALETTE[0]][i], label=name)
        for b, v in zip(bars, vals, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(keys)), [lbl for _, lbl in keys])
    ax.set_ylabel("Gap to exhaustive optimum (%)")
    ax.set_title("(b) Gap distribution")
    ax.legend(loc="upper left")
    fig.suptitle(f"E3 · QIRO vs exhaustive optimum (seed 0, {d['date']})", fontsize=9.5)
    _save(fig, "fig_e3_optimizer_small_n")


# --------------------------------------------------------------------------- E6 / E10: traffic rules


def fig_e6_traffic() -> None:
    d = _load("traffic_rules_eval.json")
    if not d:
        return
    rows = d["results"]
    labels = [r["file"].replace("_test.pcap.csv", "").replace("TCP_IP-", "") for r in rows]
    rates = [100 * r["flagged_windows"] / r["windows"] for r in rows]
    errs = []
    for r, rate in zip(rows, rates, strict=True):
        lo, hi = wilson(r["flagged_windows"], r["windows"])
        errs.append((max(0.0, rate - 100 * lo), max(0.0, 100 * hi - rate)))
    colors = [PALETTE[3] if r["expected"] == "benign" else PALETTE[0] for r in rows]
    fig, ax = plt.subplots(figsize=(6.8, 2.7))
    ax.bar(range(len(rows)), rates, color=colors, width=0.6,
           yerr=[[e[0] for e in errs], [e[1] for e in errs]], capsize=3, error_kw={"lw": 0.8})
    for i, (r, v) in enumerate(zip(rows, rates, strict=True)):
        ax.text(i, v + 4, f"{v:.1f} %\n(n = {r['windows']})", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(range(len(rows)), labels, rotation=15, ha="right")
    ax.set_ylim(0, 125)
    ax.set_ylabel("Flagged windows (%)")
    ax.set_title(f"E6 · Window-level flag rate on the CICIoMT2024 test split ({d['window_rows']}-row windows, "
                 f"recorded {d['date']}); orange = benign (false-positive rate)")
    ax.text(0.01, 0.97, "Error bars: Wilson 95 % intervals. Thresholds were tuned on this same split (optimistic).",
            transform=ax.transAxes, fontsize=7.5, va="top", color="#444")
    _save(fig, "fig_e6_traffic_same_split")


def fig_e10_traffic_holdout() -> None:
    runs = [(label, _load(name)) for label, name in (
        ("(a) Synthetic train → synthetic test", "traffic_rules_holdout.json"),
        ("(b) P1 cross-source: synthetic dev → CICIoMT2024 test", "traffic_rules_holdout_cic_p1.json"),
        ("(c) P2 temporal split within CICIoMT2024 test captures", "traffic_rules_holdout_cic_p2.json"),
    )]
    runs = [(lbl, d) for lbl, d in runs if d]
    if not runs:
        return
    base_labels = {"majority_class": "majority class", "rate_p99_benign": "Rate > benign p99",
                   "tot_size_p1_p99_band_benign": "size outside benign p1–p99"}
    fig, axes = plt.subplots(1, len(runs), figsize=(3.3 * len(runs), 3.1), squeeze=False, sharey=True)
    metrics = ["precision", "recall", "f1"]
    for ax, (label, d) in zip(axes[0], runs, strict=True):
        res = d["results"]
        series = [("shipped thresholds (not held-out)", res["shipped_thresholds"]),
                  ("tuned on dev split (held-out)", res["tuned_thresholds"])]
        series += [(f"baseline: {base_labels.get(k, k)}", v) for k, v in res.get("baselines", {}).items()]
        w = 0.8 / len(series)
        for i, (name, s) in enumerate(series):
            vals = [s["metrics"][m] for m in metrics]
            ci = s.get("bootstrap", {}).get("ci95", {})
            lo = [max(0.0, s["metrics"][m] - ci[m][0]) if m in ci else 0 for m in metrics]
            hi = [max(0.0, ci[m][1] - s["metrics"][m]) if m in ci else 0 for m in metrics]
            ax.bar([j + (i - (len(series) - 1) / 2) * w for j in range(3)], vals, width=w, label=name,
                   color=PALETTE[i % len(PALETTE)], yerr=[lo, hi], capsize=1.5, error_kw={"lw": 0.6})
        ax.set_xticks(range(3), ["precision", "recall", "F1"])
        ax.set_ylim(0, 1.12)
        ax.set_title(label, fontsize=7.8)
        ax.text(0.02, 0.97, f"test windows: {res['tuned_thresholds']['windows']}", transform=ax.transAxes, fontsize=6.5, va="top")
    axes[0][0].set_ylabel("Window-level score (attack vs benign)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=6.8, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle("E10 · Traffic rules evaluated on data not used for threshold selection (bootstrap 95 % CIs)", fontsize=9.5)
    _save(fig, "fig_e10_traffic_holdout")


# --------------------------------------------------------------------------- E7: sensitivity


def fig_e7_sensitivity() -> None:
    d = _load("sensitivity_analysis.json")
    if not d:
        return
    designs = d["designs"]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), gridspec_kw={"width_ratios": [1.25, 1]})
    # (a) per perturbation: max |ΔS| (bars) and share of systems whose verdict / status changes (markers)
    ax = axes[0]
    rows: list[tuple[str, float, float, float]] = []
    for key in ("S1_category_weights", "S2_severity_points", "S3_pillar_deductions", "S5_optimizer_pillar_weights"):
        for entry in designs.get(key, []):
            m = entry["metrics"]
            rows.append((entry["config"], float(m["max_abs_delta_score"]), 100 * float(m["verdict_change_share"]),
                         100 * float(m["status_change_share"])))
    for entry in designs.get("S4_lifetime_threshold", {}).get("configs", []):
        m = entry["metrics"]
        rows.append((entry["config"], float(m["max_abs_delta_score"]), 100 * float(m["verdict_change_share"]),
                     100 * float(m["status_change_share"])))
    rows.sort(key=lambda r: (r[1], r[2]))
    ys = list(range(len(rows)))
    ax.barh(ys, [r[1] for r in rows], color=PALETTE[1], height=0.65, label="max |ΔS| (points)")
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=6.3)
    ax.set_xlabel("(a) Max |ΔS| over the ten systems (points)", fontsize=8.5)
    ax2 = ax.twiny()
    ax2.plot([r[2] for r in rows], ys, "o", color=PALETTE[0], ms=3.2, label="verdict changes (% of systems)")
    ax2.plot([r[3] for r in rows], ys, "x", color=PALETTE[3], ms=4, label="status changes (% of systems)")
    ax2.set_xlim(0, 105)
    ax2.set_xlabel("Systems whose verdict / status changes (%)", fontsize=7.5)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.3, loc="lower right")
    # (b) lifetime threshold sweep per scenario
    ax = axes[1]
    s4 = designs.get("S4_lifetime_threshold", {})
    ls = [int(x) for x in s4.get("thresholds_years", [5, 10, 15, 20])]
    for i, row in enumerate(s4.get("per_scenario", [])):
        scores = [row["by_threshold"][str(L)]["pq_risk_score"] for L in ls]
        ax.plot(ls, scores, marker="o", ms=3, lw=1, color=PALETTE[i % len(PALETTE)], ls=["-", "--", ":", "-."][i // 5],
                alpha=0.9, label=f"{row['scenario']} ({row['data_lifetime_years']:g} y)")
    ax.axvline(10, color="#999", lw=0.8, ls="--")
    ax.text(10.2, 2, "default L = 10", fontsize=6.5, color="#666")
    ax.set_xticks(ls)
    ax.set_xlabel("(b) Lifetime threshold L (years)", fontsize=8.5)
    ax.set_ylabel("PQ risk score S")
    ax.set_ylim(-4, 100)
    ax.legend(fontsize=5.6, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    fig.suptitle("E7 · Sensitivity of verdicts and scores to the scoring constants (ten scenarios)", fontsize=9.5)
    _save(fig, "fig_e7_sensitivity")


# --------------------------------------------------------------------------- E8: scalability


def fig_e8_scalability() -> None:
    d = _load("qiro_scalability.json")
    if not d:
        return
    entries = sorted(((int(k), v) for k, v in d["by_size"].items()), key=lambda kv: kv[0])
    ns = [n for n, _ in entries]
    methods = [("greedy", "greedy only"), ("annealing", "greedy + annealing"),
               ("greedy_local_search", "greedy + local search"), ("annealing_local_search", "shipped: greedy + annealing + local search")]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 2.9))
    ax = axes[0]
    for i, (key, label) in enumerate(methods):
        ax.plot(ns, [100 * v["methods"][key]["optimal_share"] for _, v in entries], marker="o", ms=3.5, color=PALETTE[i], label=label)
    ax.set_xscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_ylim(0, 105)
    ax.set_xlabel("Candidate actions n")
    ax.set_ylabel("Instances solved to ILP optimum (%)")
    ax.set_title("(a) Optimal share")
    ax = axes[1]
    for i, (key, label) in enumerate(methods):
        ax.plot(ns, [v["methods"][key]["mean_gap_pct"] for _, v in entries], marker="o", ms=3.5, color=PALETTE[i], label=f"{label} — mean")
        ax.plot(ns, [v["methods"][key]["max_gap_pct"] for _, v in entries], marker="x", ms=3.5, ls="--", lw=0.8, color=PALETTE[i],
                label=f"{label} — max")
    ax.set_xscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("Candidate actions n")
    ax.set_ylabel("Gap to ILP optimum (%)")
    ax.set_title("(b) Mean (solid) and maximum (dashed) gap")
    ax = axes[2]
    ax.plot(ns, [v["methods"]["annealing_local_search"]["mean_runtime_ms"] for _, v in entries], marker="o", ms=3.5, color=PALETTE[3],
            label="shipped QIRO")
    ax.plot(ns, [v["methods"]["greedy_local_search"]["mean_runtime_ms"] for _, v in entries], marker="^", ms=3.5, color=PALETTE[2],
            label="greedy + local search")
    ax.plot(ns, [v["methods"]["ilp"]["mean_runtime_ms"] for _, v in entries], marker="s", ms=3.5, color=PALETTE[0], label="ILP (HiGHS)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("Candidate actions n")
    ax.set_ylabel("Mean runtime per instance (ms)")
    ax.set_title("(c) Runtime (single machine)")
    ax.legend(fontsize=6.5)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.08))
    per_size = ", ".join(f"n={n}: {v['instances']}" for n, v in entries)
    fig.suptitle(f"E8 · Scalability against an integer-programming reference ({d.get('solver', 'HiGHS')}; seed {d.get('seed', 0)}; "
                 f"instances {per_size}; τ ∈ {{0.25, 0.5, 0.75}})", fontsize=9)
    fig.suptitle(f"E8 · Scalability against an integer-programming reference ({d.get('solver', 'HiGHS')}; seed {d.get('seed', 0)})",
                 fontsize=9.5)
    _save(fig, "fig_e8_scalability")


# --------------------------------------------------------------------------- E9: reassessment


def fig_e9_reassessment() -> None:
    d = _load("plan_reassessment.json")
    if not d:
        return
    systems = d["systems"]
    names = [s["scenario"] for s in systems]
    before = [s["baseline"]["pq_risk_score"] for s in systems]
    proj_a = [s["plan_a"]["projected_pq_score"] for s in systems]
    reass_a = [s["plan_a"]["reassessed_pq_score"] for s in systems]
    proj_b = [s["plan_b"]["projected_pq_score"] for s in systems]
    reass_b = [s["plan_b"]["reassessed_pq_score"] for s in systems]
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    w = 0.16
    xs = range(len(systems))
    series = ((before, "baseline S", PALETTE[2]), (proj_a, "plan A projected S_proj", "#c7d4e8"),
              (reass_a, "plan A reassessed S_reass", PALETTE[0]), (proj_b, "plan B projected S_proj", "#f3cfae"),
              (reass_b, "plan B reassessed S_reass", PALETTE[3]))
    for i, (vals, label, col) in enumerate(series):
        ax.bar([x + (i - 2) * w for x in xs], vals, width=w, color=col, label=label, edgecolor="#333", linewidth=0.3)
    for x, s in zip(xs, systems, strict=True):
        st = s["plan_a"]["reassessed_status"]
        ax.text(x, max(before[x], 2) + 3, st.replace("_", " "), ha="center", fontsize=5.8,
                color=PALETTE[4] if st == "SAFE" else PALETTE[3])
    ax.set_xticks(list(xs), names, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("PQ risk score S")
    ax.set_ylim(0, 105)
    ax.set_title("E9 · Baseline, projected and reassessed PQ risk score per system (plan A: independent actions; "
                 "plan B: shared root causes); label = status after plan A", fontsize=8.5)
    ax.legend(fontsize=6.5, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.32))
    _save(fig, "fig_e9_reassessment")


# --------------------------------------------------------------------------- E11: attack simulation


def fig_e11_attacks() -> None:
    d = _load("attack_simulation.json")
    if not d:
        return
    attacks = d["attacks"]
    names = list(attacks)
    det = [100 * attacks[a]["detection_rate"] for a in names]
    flagged = [100 * attacks[a]["flagged_after_attack_rate"] for a in names]
    restored = [100 * attacks[a]["mitigation_restored_status_rate"] for a in names]
    blocked = [100 * attacks[a]["reinjection_blocked_rate"] for a in names]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 3.4), gridspec_kw={"width_ratios": [2, 1]})
    ax = axes[0]
    w = 0.2
    xs = range(len(names))
    ax.bar([x - 1.5 * w for x in xs], det, width=w, color=PALETTE[0], label="new finding from the expected agent (detected)")
    ax.bar([x - 0.5 * w for x in xs], flagged, width=w, color=PALETTE[1], label="any finding present after the attack")
    ax.bar([x + 0.5 * w for x in xs], restored, width=w, color=PALETTE[4], label="mitigation restores status ≤ baseline")
    ax.bar([x + 1.5 * w for x in xs], blocked, width=w, color=PALETTE[3], label="re-injection blocked after mitigation")
    for x, a in zip(xs, names, strict=True):
        ax.text(x, 103, f"{attacks[a]['exploitable_runs']}", ha="center", fontsize=6, color="#555")
    ax.set_xticks(list(xs), [a.replace("_", "\n") for a in names], fontsize=6)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Share of exploitable runs (%)")
    ax.set_title("(a) Outcome per attack (number above bars = exploitable runs over devices × seeds)", fontsize=8)
    ax.legend(fontsize=6.3, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.26))
    ax = axes[1]
    traj = d["kill_chain"]["trajectory"]
    steps = [t["step"] for t in traj]
    ax.plot(range(len(steps)), [t["mean_pq_risk_score"] for t in traj], marker="o", ms=3.5, color=PALETTE[0], label="fleet mean PQ risk score")
    ax.set_ylabel("Fleet mean PQ risk score", color=PALETTE[0])
    ax.set_ylim(0, max(45, 1.15 * max(t["mean_pq_risk_score"] for t in traj)))
    ax2 = ax.twinx()
    ax2.bar(range(len(steps)), [t["unsafe"] for t in traj], width=0.5, color=PALETTE[3], alpha=0.35, label="devices UNSAFE")
    ax2.set_ylabel("Devices UNSAFE (of 9)", color=PALETTE[3])
    ax2.set_ylim(0, 10)
    ax2.spines["right"].set_visible(True)
    ax.set_xticks(range(len(steps)), steps, rotation=30, ha="right", fontsize=7)
    ax.set_title(f"(b) ICU Q-Day drill on {d['kill_chain']['drill_device']} (seed {d['kill_chain']['seed']})", fontsize=8)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    fig.suptitle(f"E11 · Attack simulation on the {d.get('template_label', d.get('template'))} template "
                 f"(seeds {', '.join(map(str, d.get('seeds', [])))}; {d['summary']['runs']} runs)", fontsize=9.5)
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
