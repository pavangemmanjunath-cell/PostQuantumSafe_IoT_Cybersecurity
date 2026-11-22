"""Generate the Release 3 result figures from the committed benchmark artifacts.

    python benchmarks/make_figures.py            # writes docs/release-3/figures/fig_e*.svg, .pdf and .png

Journal style: each figure carries one message in at most two panels and is drawn at its printed width (single
column 3.5 in, double column 7.16 in). All text is 8 pt, so nothing falls below 7 pt even when a double-column
figure is reduced to a 16 cm text width. There are no in-figure titles (the captions in docs/release-3/README.md
carry them), no second y-axis, and one colour-blind-safe pair (blue, orange) plus grey for reference series.
Output: vector SVG and PDF (TrueType fonts embedded) and 300-dpi PNG. Every figure is drawn from a JSON file in
benchmarks/results/; figures whose artifact is missing are skipped. Requires matplotlib (optional ``benchmark``
extra).
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
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter
except ImportError as exc:  # pragma: no cover - documented optional dependency
    raise SystemExit("matplotlib is required: pip install -e 'backend[benchmark]'") from exc

BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#a3a19b"  # validated categorical pair + neutral reference grey
INK, INK2, RULE = "#1a1a1a", "#55534e", "#d9d7d2"  # text, secondary text / axes, hairline grid
SINGLE, DOUBLE = 3.5, 7.16  # printed widths in inches (journal single / double column)
FONT = 8  # pt, every text element


def _style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": FONT, "axes.titlesize": FONT, "axes.labelsize": FONT, "xtick.labelsize": FONT,
        "ytick.labelsize": FONT, "legend.fontsize": FONT, "figure.titlesize": FONT,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "xtick.labelcolor": INK, "ytick.labelcolor": INK, "axes.titlelocation": "left", "axes.titlepad": 4,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
        "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "grid.color": RULE, "grid.linewidth": 0.5, "grid.linestyle": "-",
        "lines.linewidth": 1.4, "lines.markersize": 4.5, "legend.frameon": False, "legend.handlelength": 1.5,
        "figure.constrained_layout.use": True, "savefig.pad_inches": 0.03,
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


def _hgrid(ax: plt.Axes, axis: str = "y") -> None:
    ax.grid(True, axis=axis)
    ax.set_axisbelow(True)


# --------------------------------------------------------------------------- E3: optimizer, small n


def fig_e3_optimizer() -> None:
    """Local search raises the optimal share and cuts the worst-case gap (two bars per panel)."""
    d = _load("qiro_optimality.json")
    if not d:
        return
    methods = [("annealing\nonly", d["annealing_only"], GREY), ("annealing +\nlocal search", d["annealing_plus_local_search"], BLUE)]
    fig, axes = plt.subplots(1, 2, figsize=(SINGLE, 2.1))
    panels = ((axes[0], "optimal_share", 100.0, "(a) Solved to the optimum", "Instances (%)", 112),
              (axes[1], "max_gap_pct", 1.0, "(b) Worst-case gap", "Maximum gap (%)", None))
    for ax, key, scale, title, ylabel, top in panels:
        vals = [scale * m[key] for _, m, _ in methods]
        top = top or 1.25 * max(vals)
        ax.bar(range(2), vals, width=0.55, color=[c for *_, c in methods])
        for x, v in enumerate(vals):
            ax.text(x, v + 0.02 * top, f"{v:.1f} %", ha="center", va="bottom")
        ax.set_xticks(range(2), [name for name, *_ in methods])
        ax.set_xlim(-0.6, 1.6)
        ax.set_ylim(0, top)
        if key == "optimal_share":
            ax.set_yticks(range(0, 101, 25))
        ax.set_ylabel(ylabel)
        ax.set_title(title)
    _save(fig, "fig_e3_optimizer_small_n")


# --------------------------------------------------------------------------- E6 / E10: traffic rules

SHORT_FILE = {
    "ARP_Spoofing": "ARP spoofing", "Benign": "Benign", "MQTT-Malformed_Data": "Malformed MQTT", "Recon-Port_Scan": "Port scan",
    "TCP_IP-DDoS-TCP": "DDoS (TCP)", "TCP_IP-DoS-SYN": "DoS (SYN)",
}


def fig_e6_traffic() -> None:
    """Flag rate per CICIoMT2024 test file on the threshold-selection split, benign first, attacks sorted."""
    d = _load("traffic_rules_eval.json")
    if not d:
        return
    rows = d["results"]
    attacks = sorted((r for r in rows if r["expected"] != "benign"), key=lambda r: r["flagged_windows"] / r["windows"])
    order = attacks + [r for r in rows if r["expected"] == "benign"]  # barh draws bottom-up: benign ends on top
    fig, ax = plt.subplots(figsize=(SINGLE, 2.0))
    for y, r in enumerate(order):
        rate = 100 * r["flagged_windows"] / r["windows"]
        lo, hi = wilson(r["flagged_windows"], r["windows"])
        color = ORANGE if r["expected"] == "benign" else BLUE
        err = [[max(0.0, rate - 100 * lo)], [max(0.0, 100 * hi - rate)]]
        ax.barh(y, rate, height=0.6, color=color, xerr=err, error_kw={"lw": 0.6, "capsize": 1.5, "ecolor": INK2})
        ax.text(rate + err[1][0] + 2, y, f"{rate:.1f} %", va="center")
    labels = [f"{SHORT_FILE.get(r['file'].replace('_test.pcap.csv', ''), r['file'])} ({r['windows']})" for r in order]
    ax.set_yticks(range(len(order)), labels)
    ax.set_xlim(0, 118)
    ax.set_xticks(range(0, 101, 25))
    ax.set_xlabel("Windows flagged (%)")
    _hgrid(ax, "x")
    ax.legend(handles=[Line2D([], [], color=BLUE, lw=5, label="attack: detection rate"),
                       Line2D([], [], color=ORANGE, lw=5, label="benign: false-positive rate")],
              loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=2, handlelength=1.0, borderaxespad=0.2)
    _save(fig, "fig_e6_traffic_same_split")


BASELINE_LABELS = {"majority_class": "majority class", "rate_p99_benign": "packet rate above benign p99",
                   "tot_size_p1_p99_band_benign": "packet size outside benign p1–p99"}


def _best_baseline(results: dict) -> tuple[str, dict]:
    candidates = [(k, v) for k, v in results.get("baselines", {}).items() if v.get("metrics", {}).get("f1") is not None]
    return max(candidates, key=lambda kv: kv[1]["metrics"]["f1"])


def fig_e10_traffic_holdout() -> None:
    """Held-out F1 (95 % bootstrap CI) of the dev-tuned rules vs the best single-feature baseline, per protocol."""
    runs = [(label, _load(name)) for label, name in (
        ("P1 cross-source", "traffic_rules_holdout_cic_p1.json"),
        ("P2 temporal split", "traffic_rules_holdout_cic_p2.json"),
    )]
    runs = [(lbl, d) for lbl, d in runs if d]
    if not runs:
        return
    best = [_best_baseline(d["results"]) for _, d in runs]
    keys = {k for k, _ in best}
    base_name = "best baseline: " + (BASELINE_LABELS.get(next(iter(keys)), next(iter(keys))) if len(keys) == 1 else "per protocol")
    fig, ax = plt.subplots(figsize=(SINGLE, 2.5))
    lows = []
    for i, ((_, d), (_, base)) in enumerate(zip(runs, best, strict=True)):
        for j, (block, color, marker) in enumerate(((d["results"]["tuned_thresholds"], BLUE, "o"), (base, GREY, "D"))):
            x = i + (j - 0.5) * 0.36
            f1 = block["metrics"]["f1"]
            lo, hi = (block.get("bootstrap") or {}).get("ci95", {}).get("f1") or (f1, f1)
            lows.append(lo)
            ax.errorbar([x], [f1], yerr=[[f1 - lo], [hi - f1]], fmt=marker, color=color, ecolor=color, elinewidth=0.9,
                        capsize=2.5, markersize=5, markeredgecolor="white", markeredgewidth=0.6, zorder=3)
            ax.text(x + 0.07, f1, f"{f1:.3f}", va="center", ha="left")
    ax.set_xticks(range(len(runs)), [lbl for lbl, _ in runs])
    ax.set_xlim(-0.6, len(runs) - 0.35)
    ax.set_ylim(math.floor(100 * min(lows) - 1) / 100, 1.0)
    ax.set_ylabel("Held-out F1 (window level)")
    _hgrid(ax)
    ax.legend(handles=[Line2D([], [], color=BLUE, marker="o", ls="none", label="rules, thresholds tuned on development windows"),
                       Line2D([], [], color=GREY, marker="D", ls="none", label=base_name)],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1)
    _save(fig, "fig_e10_traffic_holdout")


# --------------------------------------------------------------------------- E7: sensitivity


def fig_e7_sensitivity() -> None:
    """Largest score change per perturbation design, with the number of systems whose status changes."""
    d = _load("sensitivity_analysis.json")
    if not d:
        return
    designs = d["designs"]
    groups = [
        ("S1 category weights", designs.get("S1_category_weights", [])),
        ("S2 severity points", designs.get("S2_severity_points", [])),
        ("S3 principle deductions", designs.get("S3_pillar_deductions", [])),
        ("S4 lifetime L = 5–20 y", designs.get("S4_lifetime_threshold", {}).get("configs", [])),
        ("S5 planner weights", designs.get("S5_optimizer_pillar_weights", [])),
    ]
    groups = [(name, cfgs) for name, cfgs in groups if cfgs]
    n_sys = len(d.get("scenarios", [])) or 10
    fig, ax = plt.subplots(figsize=(SINGLE, 1.8))
    for y, (_, cfgs) in enumerate(reversed(groups)):
        delta = max(float(c["metrics"]["max_abs_delta_score"]) for c in cfgs)
        status = max(round(n_sys * float(c["metrics"]["status_change_share"])) for c in cfgs)
        ax.barh(y, delta, height=0.55, color=BLUE)
        ax.text(delta + 0.6, y, f"{delta:g}", va="center")
        ax.annotate(f"{status}/{n_sys}", (1, y), xycoords=("axes fraction", "data"), xytext=(14, 0),
                    textcoords="offset points", va="center", ha="center", annotation_clip=False)
    ax.annotate("status\nchanges", (1, len(groups) - 0.45), xycoords=("axes fraction", "data"), xytext=(14, 0),
                textcoords="offset points", va="bottom", ha="center", color=INK2, annotation_clip=False)
    ax.set_yticks(range(len(groups)), [name for name, _ in reversed(groups)])
    ax.set_ylim(-0.5, len(groups) - 0.5)
    ax.set_xlim(0, 25)
    ax.set_xticks(range(0, 26, 5))
    ax.set_xlabel("Largest |ΔS| over ten systems (points)")
    _hgrid(ax, "x")
    _save(fig, "fig_e7_sensitivity")


# --------------------------------------------------------------------------- E8: scalability


def fig_e8_scalability() -> None:
    """(a) mean gap of the greedy start and the shipped planner; (b) runtime of the shipped planner vs the ILP."""
    d = _load("qiro_scalability.json")
    if not d:
        return
    entries = sorted(((int(k), v["methods"]) for k, v in d["by_size"].items()), key=lambda kv: kv[0])
    ns = [n for n, _ in entries]
    fig, (a, b) = plt.subplots(1, 2, figsize=(DOUBLE, 2.4))
    for key, label, color, marker in (("greedy", "greedy start only", GREY, "o"),
                                      ("annealing_local_search", "shipped planner", BLUE, "o")):
        vals = [m[key]["mean_gap_pct"] for _, m in entries]
        a.plot(ns, vals, marker=marker, color=color, label=label)
        a.annotate(f"{vals[-1]:.3f} %", (ns[-1], vals[-1]), xytext=(4, 0), textcoords="offset points", va="center")
    a.set_ylim(0, 1.15 * max(m["greedy"]["mean_gap_pct"] for _, m in entries))
    a.set_ylabel("Mean gap to ILP optimum (%)")
    a.set_title("(a) Solution quality")
    for key, label, color, marker in (("annealing_local_search", "shipped planner", BLUE, "o"), ("ilp", "ILP solver (HiGHS)", ORANGE, "s")):
        vals = [m[key]["mean_runtime_ms"] for _, m in entries]
        b.plot(ns, vals, marker=marker, color=color, label=label)
        b.annotate(f"{vals[-1]:.0f} ms", (ns[-1], vals[-1]), xytext=(4, 0), textcoords="offset points", va="center")
    b.set_yscale("log")
    runtimes = [m[k]["mean_runtime_ms"] for _, m in entries for k in ("annealing_local_search", "ilp")]
    b.set_ylim(min(runtimes) / 1.6, max(runtimes) * 1.6)
    b.set_yticks([t for t in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000)
                  if min(runtimes) / 1.6 <= t <= max(runtimes) * 1.6])
    b.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    b.set_ylabel("Mean runtime per instance (ms)")
    b.set_title("(b) Runtime")
    for ax, where in ((a, "upper right"), (b, "upper left")):
        ax.set_xscale("log")
        ax.set_xticks(ns, [str(n) for n in ns])
        ax.minorticks_off()
        ax.set_xlim(ns[0] / 1.25, ns[-1] * 1.9)
        ax.set_xlabel("Candidate actions n")
        _hgrid(ax)
        ax.legend(loc=where)
    _save(fig, "fig_e8_scalability")


# --------------------------------------------------------------------------- E9: reassessment


def fig_e9_reassessment() -> None:
    """Baseline, projected and reassessed PQ risk score per system for the shipped planner, status after the plan."""
    d = _load("plan_reassessment.json")
    if not d:
        return
    systems = sorted(d["systems"], key=lambda s: (s["baseline"]["pq_risk_score"], s["scenario"]))
    fig, ax = plt.subplots(figsize=(SINGLE, 2.9))
    for y, s in enumerate(systems):
        base, a = s["baseline"]["pq_risk_score"], s["plan_a"]
        proj, reass = a["projected_pq_score"], a["reassessed_pq_score"]
        ax.plot([base, reass], [y, y], color=RULE, lw=1.6, zorder=1, solid_capstyle="round")
        ax.scatter([base], [y], s=22, color=GREY, zorder=2)
        ax.scatter([proj], [y], s=34, marker="D", facecolor="none", edgecolor=ORANGE, linewidth=1.0, zorder=3)
        ax.scatter([reass], [y], s=22, color=BLUE, edgecolor="white", linewidth=0.5, zorder=4)
        ax.text(104, y, a["reassessed_status"].replace("_", " "), va="center", ha="left", clip_on=False)
    ax.text(104, len(systems) - 0.35, "after plan", va="bottom", ha="left", color=INK2, clip_on=False)
    ax.set_yticks(range(len(systems)), [s["scenario"] for s in systems])
    ax.set_ylim(-0.6, len(systems) - 0.4)
    ax.set_xlim(-3, 100)
    ax.set_xticks(range(0, 101, 25))
    ax.set_xlabel("PQ risk score S")
    _hgrid(ax, "x")
    fig.legend(handles=[Line2D([], [], color=GREY, marker="o", ls="none", label="baseline"),
                        Line2D([], [], color=ORANGE, marker="D", ls="none", markerfacecolor="none", label="projected"),
                        Line2D([], [], color=BLUE, marker="o", ls="none", label="reassessed")],
               loc="outside lower center", ncol=3, handletextpad=0.3, columnspacing=1.2)
    _save(fig, "fig_e9_reassessment")


# --------------------------------------------------------------------------- E11: attack simulation

SHORT_ATTACK = {
    "hndl_capture": "Harvest-now-decrypt-later", "tls_downgrade": "TLS legacy fallback", "pq_strip": "Classical-only fallback",
    "cert_spoof": "Quantum cert. forgery", "syn_flood": "SYN flood", "ddos_volumetric": "Volumetric DDoS", "port_scan": "Port scan",
    "mqtt_malformed": "Malformed MQTT", "arp_spoofing": "ARP spoofing / MITM", "prompt_injection": "Prompt injection",
    "pq_downgrade_prompt": "PQ-downgrade prompt", "phi_leak": "PHI leak into prompts", "unsafe_command": "Unsafe clinical command",
    "secret_leak": "Credential leak in log",
}


def fig_e11_attacks() -> None:
    """Detection rate per simulated attack (sorted), with the number of exploitable runs in brackets."""
    d = _load("attack_simulation.json")
    if not d:
        return
    rows = sorted(d["attacks"].items(), key=lambda kv: (kv[1]["detection_rate"], kv[1]["exploitable_runs"], kv[0]), reverse=False)
    rows = [r for r in rows if r[1]["exploitable_runs"]]
    fig, ax = plt.subplots(figsize=(SINGLE, 3.0))
    for y, (_, a) in enumerate(rows):
        rate = 100 * a["detection_rate"]
        ax.barh(y, rate, height=0.6, color=BLUE)
        if rate < 100:
            hit = a["exploitable_runs"] - a["undetected_exploitable_runs"]
            ax.text(rate + 2, y, f"{rate:.0f} % ({hit} of {a['exploitable_runs']})", va="center")
    ax.set_yticks(range(len(rows)), [f"{SHORT_ATTACK.get(k, a['label'])} ({a['exploitable_runs']})" for k, a in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 25))
    ax.set_xlabel("Detected (% of exploitable runs)")
    _hgrid(ax, "x")
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
