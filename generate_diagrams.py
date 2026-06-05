"""
TIPPSS SafeGuard-PQ — High-Quality Architecture Diagram Generator
=================================================================
Produces 3 professional PNG diagrams in 00_Documention/:
  1. data_flow_diagram.png       — end-to-end data flow (swimlane style)
  2. architecture_diagram.png    — component/entity architecture
  3. qiro_optimization_diagram.png — QIRO math + use case walkthrough
"""

import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Wedge
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import matplotlib.patheffects as pe
import numpy as np

OUT = pathlib.Path("00_Documention")
OUT.mkdir(exist_ok=True)

DPI = 220   # high quality

# ── Palette ───────────────────────────────────────────────────────────────────
P = dict(
    navy="#1F3864",   blue="#2563EB",   lblue="#60A5FA",
    teal="#0D9488",   lteal="#5EEAD4",  green="#16A34A",
    lgreen="#4ADE80", amber="#D97706",  gold="#F59E0B",
    orange="#EA580C", red="#DC2626",    pink="#EC4899",
    purple="#7C3AED", lpurple="#A78BFA",
    white="#FFFFFF",  lgray="#F1F5F9",  mgray="#CBD5E1",
    gray="#64748B",   dark="#0F172A",   darkb="#1E293B",
    card="#0F2040",
)

def box(ax, x, y, w, h, fc, ec, lw=1.5, radius=0.015, alpha=1.0, zorder=3):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad={radius}",
                       facecolor=fc, edgecolor=ec,
                       linewidth=lw, alpha=alpha, zorder=zorder)
    ax.add_patch(p)
    return p

def label(ax, x, y, text, size=9, color=P["white"], bold=False,
          ha="center", va="center", zorder=10, family="sans-serif",
          wrap=False, linespacing=1.4):
    kw = dict(ha=ha, va=va, fontsize=size, color=color,
              fontweight="bold" if bold else "normal",
              fontfamily=family, zorder=zorder, multialignment=ha,
              linespacing=linespacing)
    if wrap:
        text = "\n".join(text.split(" / "))
    ax.text(x, y, text, **kw)

def arrow(ax, x1, y1, x2, y2, col=P["blue"], lw=1.8,
          style="-|>", ms=14, zorder=5, conn="arc3,rad=0.0"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle=style, color=col, lw=lw,
                    mutation_scale=ms,
                    connectionstyle=conn),
                zorder=zorder)

def shadow_box(ax, x, y, w, h, fc, ec, lw=2.0, radius=0.02, zorder=3):
    # shadow
    p_sh = FancyBboxPatch((x+0.003, y-0.003), w, h,
                           boxstyle=f"round,pad={radius}",
                           facecolor="#000000", edgecolor="none",
                           linewidth=0, alpha=0.25, zorder=zorder-1)
    ax.add_patch(p_sh)
    box(ax, x, y, w, h, fc, ec, lw, radius, zorder=zorder)

def gradient_rect(ax, x, y, w, h, col_left, col_right, steps=60, zorder=2):
    for i in range(steps):
        t = i / steps
        r1,g1,b1 = matplotlib.colors.to_rgb(col_left)
        r2,g2,b2 = matplotlib.colors.to_rgb(col_right)
        r = r1 + t*(r2-r1); g = g1 + t*(g2-g1); b = b1 + t*(b2-b1)
        seg_x = x + t*w
        seg_w = w/steps + 0.001
        p = FancyBboxPatch((seg_x, y), seg_w, h,
                            boxstyle="square,pad=0",
                            facecolor=(r,g,b), edgecolor="none",
                            linewidth=0, zorder=zorder)
        ax.add_patch(p)


# ════════════════════════════════════════════════════════════════════════════
# DIAGRAM 1 — Data Flow (Swimlane)
# ════════════════════════════════════════════════════════════════════════════

def diagram_data_flow():
    fig = plt.figure(figsize=(22, 14), dpi=DPI)
    fig.patch.set_facecolor(P["dark"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 22); ax.set_ylim(0, 14)
    ax.axis("off")
    ax.set_facecolor(P["dark"])

    # ── Title ────────────────────────────────────────────────────────────────
    ax.text(11, 13.55, "TIPPSS SafeGuard-PQ — End-to-End Data Flow",
            ha="center", va="center", fontsize=20, fontweight="bold",
            color=P["white"], fontfamily="monospace")
    ax.text(11, 13.15, "Sequential Agentic Pipeline  ·  NIST FIPS 203/204/205  ·  IEEE 2933-2024 TIPPSS",
            ha="center", va="center", fontsize=11, color=P["mgray"])

    # ── Swimlane definitions ─────────────────────────────────────────────────
    LANES = [
        ("INPUT",           0.3,  12.7, P["teal"],    P["lteal"]),
        ("PRESENTATION",    0.3,  10.9, P["blue"],    P["lblue"]),
        ("DETECTION AGENTS",0.3,   7.8, P["purple"],  P["lpurple"]),
        ("SCORING & AI",    0.3,   5.1, P["navy"],    P["lblue"]),
        ("QIRO OPTIMIZER",  0.3,   3.2, P["amber"],   P["gold"]),
        ("OUTPUT",          0.3,   1.2, P["green"],   P["lgreen"]),
    ]
    lane_heights = [1.5, 2.5, 2.5, 1.8, 1.8, 1.8]
    lane_ys      = [12.0, 10.2, 7.3, 4.7, 2.8, 0.5]

    for (lname, _, _, lfc, lec), lh, ly in zip(LANES, lane_heights, lane_ys):
        # lane background
        gradient_rect(ax, 0.2, ly, 21.6, lh, lfc+"22", lfc+"08", zorder=1)
        # lane label tab
        box(ax, 0.2, ly, 2.0, lh, lfc+"55", lec, lw=1.5, radius=0.01, zorder=2)
        ax.text(1.2, ly + lh/2, lname, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=P["white"],
                rotation=0, zorder=3)
        # lane border
        ax.plot([0.2, 21.8], [ly+lh, ly+lh], color=lec+"66",
                linewidth=0.8, linestyle="--", zorder=2)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 0: INPUT SOURCES
    # ══════════════════════════════════════════════════════════════════════
    input_items = [
        (4.0, "Pre-built Scenarios\n7 Clinical Simulations",      P["teal"],   P["lteal"]),
        (8.5, "CICIoMT2024 Files\n.pcap.csv Network Traffic",    P["teal"],   P["lteal"]),
        (13.0,"Synthea Records\npatients.csv / conditions.csv",   P["teal"],   P["lteal"]),
        (17.5,"Real System Config\nTLS + Device + AI Logs",       P["teal"],   P["lteal"]),
    ]
    for ix, itxt, ifc, iec in input_items:
        shadow_box(ax, ix-1.5, 12.15, 3.0, 1.15, ifc+"33", iec, lw=2, radius=0.025)
        label(ax, ix, 12.73, itxt, size=9, bold=True, color=P["white"])
        arrow(ax, ix, 12.15, ix, 11.25, col=P["lteal"], lw=2.2)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 1: STREAMLIT DASHBOARD
    # ══════════════════════════════════════════════════════════════════════
    shadow_box(ax, 2.5, 10.35, 7.5, 1.55, P["blue"]+"44", P["lblue"], lw=2.5, radius=0.03)
    label(ax, 6.25, 11.35, "STREAMLIT DASHBOARD  (localhost:8501)", size=11, bold=True, color=P["lblue"])
    dash_items = [
        (3.3,  10.75, "Scenario\nSelector"),
        (5.1,  10.75, "File\nUploader"),
        (6.9,  10.75, "Feature\nExtractor"),
        (8.7,  10.75, "Constraint\nSliders"),
    ]
    for dx, dy, dtxt in dash_items:
        box(ax, dx-0.7, dy-0.25, 1.4, 0.72, P["blue"]+"77", P["lblue"],
            lw=1.5, radius=0.015)
        label(ax, dx, dy+0.11, dtxt, size=8, color=P["white"])

    # Payload construction
    shadow_box(ax, 11.0, 10.35, 5.0, 1.55, P["blue"]+"33", P["blue"], lw=2, radius=0.025)
    label(ax, 13.5, 11.35, "Payload Constructor", size=10, bold=True, color=P["lblue"])
    label(ax, 13.5, 10.78,
          "system_id · tls_config · device_logs\nai_prompt_logs · constraints · iot_traffic",
          size=8, color=P["mgray"])

    arrow(ax, 10.0, 11.12, 11.0, 11.12, col=P["lblue"], lw=2.0)
    arrow(ax, 13.5, 10.35, 13.5,  9.95, col=P["gold"], lw=2.5)
    ax.text(13.9, 10.12, "HTTP POST (JSON)", fontsize=8, color=P["gold"],
            fontweight="bold", zorder=10)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 2: DETECTION AGENTS
    # ══════════════════════════════════════════════════════════════════════
    agents = [
        (3.0,  "Agent 1\nInput Validator",            P["blue"],   P["lblue"]),
        (5.8,  "Agent 2\nCrypto Classifier",          P["blue"],   P["lblue"]),
        (8.6,  "Agent 3\nPQ Benchmark",               P["purple"], P["lpurple"]),
        (11.4, "Agent 4\nIoT Device Identity",        P["purple"], P["lpurple"]),
        (14.2, "Agent 5\nAI Prompt Privacy",          P["purple"], P["lpurple"]),
        (17.0, "Agent 6\nSecret Exposure",            P["orange"], P["gold"]),
        (19.8, "Agent 7\nSafety Risk",                P["red"],    P["gold"]),
    ]
    sub_labels = [
        "Schema\nvalidation",
        "PQ-safe / Classical\n/ Deprecated",
        "FIPS 203/204/205\nHNDL rule",
        "Certificate\nAuth · Login",
        "PHI · MRN\nInjection",
        "API keys\nCredentials",
        "Dosing\nAlarm override",
    ]
    for (ax_x, atxt, afc, aec), sub in zip(agents, sub_labels):
        shadow_box(ax, ax_x-1.3, 8.15, 2.6, 1.5, afc+"44", aec, lw=2.2, radius=0.025)
        label(ax, ax_x, 9.2, atxt, size=8.5, bold=True, color=P["white"])
        label(ax, ax_x, 8.55, sub, size=7.2, color=P["mgray"])

    # arrows between agents
    for i in range(len(agents)-1):
        x1 = agents[i][0] + 1.3
        x2 = agents[i+1][0] - 1.3
        arrow(ax, x1, 8.90, x2, 8.90, col=P["mgray"], lw=1.4, ms=10)

    # entry arrow
    arrow(ax, 13.5, 9.95, 13.5, 9.65, col=P["gold"], lw=2.2)
    arrow(ax, 13.5, 9.65, 3.0,  9.65, col=P["gold"], lw=2.2)
    arrow(ax, 3.0,  9.65, 3.0,  9.65, col=P["gold"], lw=2.2)
    arrow(ax, 3.0,  9.65, 3.0,  9.65, col=P["gold"], lw=2.2)
    arrow(ax, 3.0, 9.65, 3.0, 9.65, col=P["gold"], lw=2)
    # small down from 9.65 to agent 1 top
    arrow(ax, 3.0, 9.65, 3.0, 9.65, col=P["gold"], lw=1)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 3: SCORING & AI
    # ══════════════════════════════════════════════════════════════════════
    # Agent 8
    shadow_box(ax, 3.5, 5.0, 4.5, 1.55, P["navy"]+"66", P["lblue"], lw=2.5, radius=0.03)
    label(ax, 5.75, 5.85, "Agent 8 — TIPPSS Six-Pillar Scorer", size=10, bold=True, color=P["lblue"])
    pillars = ["Trust","Identity","Privacy","Protection","Safety","Security"]
    pcols   = [P["teal"],P["blue"],P["purple"],P["navy"],P["red"],P["orange"]]
    for pi, (pil, pcol) in enumerate(zip(pillars, pcols)):
        px = 3.8 + pi * 0.73
        box(ax, px-0.3, 5.07, 0.6, 0.4, pcol+"88", pcol, lw=1.2, radius=0.01)
        label(ax, px, 5.27, pil[:4], size=6.5, color=P["white"])

    # Agent 9
    shadow_box(ax, 9.0, 5.0, 4.5, 1.55, P["navy"]+"44", P["blue"], lw=2.2, radius=0.03)
    label(ax, 11.25, 5.85, "Agent 9 — Claude AI Report", size=10, bold=True, color=P["lblue"])
    label(ax, 11.25, 5.35,
          "Plain-English executive summary\nfor clinical leadership",
          size=8.5, color=P["mgray"])

    # Verdict card
    shadow_box(ax, 14.5, 5.0, 4.5, 1.55, P["green"]+"44", P["lgreen"], lw=2.5, radius=0.03)
    label(ax, 16.75, 5.85, "Risk Verdict", size=10, bold=True, color=P["lgreen"])
    for vi, (vtxt, vcol) in enumerate([
        ("Safe  0-25",                P["lgreen"]),
        ("Partially Safe  26-50",     P["gold"]),
        ("Not PQ Safe  51-75",        P["orange"]),
        ("Critical Risk  76-100",     P["red"]),
    ]):
        vx = 14.75; vy = 5.6 - vi * 0.3
        box(ax, vx, vy-0.1, 4.0, 0.26, vcol+"44", vcol, lw=1.0, radius=0.008)
        label(ax, vx+2.0, vy+0.03, vtxt, size=7.5, color=P["white"])

    arrow(ax, 20.1, 8.15, 16.75, 6.55, col=P["mgray"], lw=1.6)
    arrow(ax, 8.0,  8.15, 5.75,  6.55, col=P["mgray"], lw=1.6)
    arrow(ax, 8.0,  6.55, 8.5,   6.55, col=P["lblue"], lw=1.6)
    arrow(ax, 11.25,6.55,11.25,  6.55, col=P["lblue"], lw=1.0)
    arrow(ax, 13.5,  6.55, 14.5,  6.55, col=P["lblue"], lw=1.6)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 4: QIRO
    # ══════════════════════════════════════════════════════════════════════
    shadow_box(ax, 2.5, 3.05, 8.5, 1.6, P["amber"]+"33", P["gold"], lw=2.5, radius=0.03)
    label(ax, 6.75, 4.17, "Agent 10 — QIRO Optimizer  [Novel Contribution]",
          size=11, bold=True, color=P["gold"])
    qiro_steps = [
        (3.5,  "Generate\nActions"),
        (5.2,  "Score\nBi=Ri+Pi+Si+Ti"),
        (7.2,  "Energy\nFunction E(x)"),
        (9.2,  "Simulated\nAnnealing"),
        (10.5, "Select /\nDefer"),
    ]
    for qx, qtxt in qiro_steps:
        box(ax, qx-0.65, 3.15, 1.3, 0.68, P["amber"]+"55", P["gold"],
            lw=1.5, radius=0.015)
        label(ax, qx, 3.49, qtxt, size=7.8, color=P["white"])
    for i in range(len(qiro_steps)-1):
        arrow(ax, qiro_steps[i][0]+0.65, 3.49,
              qiro_steps[i+1][0]-0.65, 3.49, col=P["gold"], lw=1.6, ms=11)

    # Constraints box
    shadow_box(ax, 12.0, 3.05, 3.8, 1.6, P["red"]+"22", P["red"], lw=1.8, radius=0.025)
    label(ax, 13.9, 4.17, "Constraints", size=10, bold=True, color=P["red"])
    label(ax, 13.9, 3.67, "Budget <= Cmax\nDowntime <= Dmax", size=8.5, color=P["white"])
    arrow(ax, 12.0, 3.85, 11.15, 3.49, col=P["red"], lw=1.8, ms=11)

    arrow(ax, 16.75, 5.0, 16.75, 4.68, col=P["mgray"], lw=1.6)
    arrow(ax, 16.75, 4.68, 6.75, 4.68, col=P["mgray"], lw=1.6)
    arrow(ax, 6.75, 4.68, 6.75, 4.65, col=P["amber"], lw=2.0)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 5: OUTPUT
    # ══════════════════════════════════════════════════════════════════════
    outputs = [
        (4.0,  "Verdict Card\nPQ Risk Score",         P["green"],  P["lgreen"]),
        (7.5,  "TIPPSS Spider\nSix-Pillar Chart",     P["blue"],   P["lblue"]),
        (11.0, "QIRO Roadmap\nSelected + Deferred",   P["amber"],  P["gold"]),
        (14.5, "Claude Report\nExecutive Summary",    P["navy"],   P["lblue"]),
        (18.0, "JSON + CSV\nTimestamped Results",     P["teal"],   P["lteal"]),
    ]
    for ox, otxt, ofc, oec in outputs:
        shadow_box(ax, ox-1.5, 0.6, 3.0, 1.2, ofc+"44", oec, lw=2.0, radius=0.025)
        label(ax, ox, 1.2, otxt, size=9, bold=True, color=P["white"])

    # Arrow from QIRO to outputs
    arrow(ax, 10.6, 3.05, 10.6, 1.85, col=P["gold"], lw=2.5)
    arrow(ax, 10.6, 1.85, 4.0,  1.85, col=P["gold"], lw=2.0)
    arrow(ax, 4.0,  1.85, 4.0,  1.8,  col=P["lgreen"], lw=2.0)
    for ox, *_ in outputs[1:]:
        arrow(ax, ox, 1.85, ox, 1.8, col=P["gold"], lw=1.8, ms=10)

    # ── Legend ───────────────────────────────────────────────────────────────
    legend_items = [
        (P["blue"],   "Detection / Classification"),
        (P["purple"], "Privacy / Security Agents"),
        (P["red"],    "Safety / Risk Agents"),
        (P["navy"],   "Scoring & AI Layer"),
        (P["amber"],  "QIRO Optimization (Novel)"),
        (P["green"],  "Output / Results"),
    ]
    for li, (lcol, ltxt) in enumerate(legend_items):
        lx = 0.5 + (li % 3) * 7.2
        ly = 0.3 - (li // 3) * 0.25
        box(ax, lx, ly-0.07, 0.35, 0.22, lcol, lcol, lw=1.0, radius=0.005)
        ax.text(lx+0.45, ly+0.04, ltxt, fontsize=7.5, color=P["mgray"],
                va="center", zorder=10)

    plt.savefig(OUT / "data_flow_diagram.png", dpi=DPI, bbox_inches="tight",
                facecolor=P["dark"], edgecolor="none")
    plt.close(fig)
    kb = (OUT / "data_flow_diagram.png").stat().st_size // 1024
    print(f"  data_flow_diagram.png  ({kb} KB)")


# ════════════════════════════════════════════════════════════════════════════
# DIAGRAM 2 — Component / Entity Architecture
# ════════════════════════════════════════════════════════════════════════════

def diagram_architecture():
    fig = plt.figure(figsize=(24, 16), dpi=DPI)
    fig.patch.set_facecolor(P["dark"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 24); ax.set_ylim(0, 16)
    ax.axis("off"); ax.set_facecolor(P["dark"])

    # Title
    ax.text(12, 15.6, "TIPPSS SafeGuard-PQ — Component & Entity Architecture",
            ha="center", fontsize=22, fontweight="bold", color=P["white"],
            fontfamily="monospace")
    ax.text(12, 15.1, "Three-Tier Local Deployment  ·  Standards: NIST FIPS 203/204/205 · IEEE 2933-2024 · HIPAA · OWASP LLM Top-10",
            ha="center", fontsize=10.5, color=P["mgray"])

    # ── TIER 1: Presentation ──────────────────────────────────────────────
    box(ax, 0.4, 11.8, 10.0, 2.95, P["blue"]+"18", P["blue"], lw=2.5, radius=0.03)
    ax.text(0.7, 14.55, "TIER 1 — PRESENTATION LAYER", fontsize=11,
            fontweight="bold", color=P["lblue"], zorder=10)
    ax.text(0.7, 14.2, "Streamlit Dashboard  (localhost:8501)", fontsize=9.5,
            color=P["mgray"], zorder=10)

    pres_comps = [
        (1.6,  12.7, "Scenario\nSelector\n7 Pre-built",        P["blue"]),
        (3.5,  12.7, "File\nUploader\n.pcap.csv / .csv",       P["blue"]),
        (5.4,  12.7, "Feature\nExtractor\n100 rows / 40 cols", P["teal"]),
        (7.3,  12.7, "Constraint\nSliders\nBudget / DT",       P["purple"]),
        (9.2,  12.7, "Result\nRenderer\nCharts + Cards",       P["green"]),
    ]
    for cx, cy, ctxt, ccol in pres_comps:
        shadow_box(ax, cx-0.75, cy-0.6, 1.5, 1.6, ccol+"44", ccol, lw=2, radius=0.02)
        label(ax, cx, cy+0.2, ctxt, size=8.5, color=P["white"])

    # ── TIER 2: Orchestration ─────────────────────────────────────────────
    box(ax, 0.4, 4.4, 23.2, 7.15, P["purple"]+"12", P["purple"], lw=2.5, radius=0.03)
    ax.text(0.7, 11.37, "TIER 2 — ORCHESTRATION LAYER", fontsize=11,
            fontweight="bold", color=P["lpurple"], zorder=10)
    ax.text(0.7, 11.0, "Sequential Agentic Framework  (localhost:5678)  ·  10-Agent Pipeline",
            fontsize=9.5, color=P["mgray"], zorder=10)

    # Agent boxes
    agents_arch = [
        (1.8,  9.0, "Agent 1",  "Input\nValidator",     "Schema · Fields\n· Normalise",                P["blue"],   P["lblue"]),
        (4.2,  9.0, "Agent 2",  "Crypto\nClassifier",   "PQ-safe / Classical\n/ Deprecated",           P["blue"],   P["lblue"]),
        (6.6,  9.0, "Agent 3",  "PQ\nBenchmark",        "NIST FIPS 203/204\n/205 · HNDL rule",         P["purple"], P["lpurple"]),
        (9.0,  9.0, "Agent 4",  "IoT Device\nIdentity", "Cert · Auth\n· Login count",                  P["purple"], P["lpurple"]),
        (11.4, 9.0, "Agent 5",  "AI Prompt\nPrivacy",   "PHI · MRN\n· Injection",                      P["pink"],   P["gold"]),
        (13.8, 9.0, "Agent 6",  "Secret\nExposure",     "API keys\n· Credentials",                     P["orange"], P["gold"]),
        (16.2, 9.0, "Agent 7",  "Safety\nRisk",         "Dosing · Alarms\n· Autonomous AI",            P["red"],    P["gold"]),
        (18.6, 9.0, "Agent 8",  "TIPPSS\nScorer",       "6-pillar score\n· Risk verdict",              P["navy"],   P["lblue"]),
        (21.0, 9.0, "Agent 9",  "Claude AI\nReport",    "Executive\nsummary NL",                       P["navy"],   P["lblue"]),
        (22.5, 6.8, "Agent 10", "QIRO\nOptimizer",      "QUBO · SA\n· Roadmap",                        P["amber"],  P["gold"]),
    ]

    for i, (ax_x, ax_y, atag, aname, adesc, afc, aec) in enumerate(agents_arch[:-1]):
        shadow_box(ax, ax_x-1.0, ax_y-1.5, 2.0, 3.0, afc+"44", aec, lw=2.2, radius=0.025)
        # Agent tag header
        box(ax, ax_x-1.0, ax_y+1.05, 2.0, 0.47, afc+"88", aec, lw=1.5, radius=0.01)
        label(ax, ax_x, ax_y+1.28, atag, size=8, bold=True, color=P["white"])
        label(ax, ax_x, ax_y+0.4, aname, size=9, bold=True, color=P["white"])
        label(ax, ax_x, ax_y-0.35, adesc, size=7.5, color=P["mgray"])
        if i < len(agents_arch) - 2:
            arrow(ax, ax_x+1.0, ax_y,
                  agents_arch[i+1][0]-1.0, agents_arch[i+1][1],
                  col=P["mgray"], lw=1.4, ms=10)

    # Agent 10 special position
    ax10_x, ax10_y = agents_arch[-1][0], agents_arch[-1][1]
    afc10, aec10 = agents_arch[-1][-2], agents_arch[-1][-1]
    shadow_box(ax, ax10_x-1.1, ax10_y-1.5, 2.2, 3.2, afc10+"44", aec10, lw=2.8, radius=0.03)
    box(ax, ax10_x-1.1, ax10_y+1.25, 2.2, 0.47, afc10+"88", aec10, lw=2, radius=0.01)
    label(ax, ax10_x, ax10_y+1.48, "Agent 10", size=8, bold=True, color=P["white"])
    label(ax, ax10_x, ax10_y+0.5, "QIRO\nOptimizer", size=9, bold=True, color=P["gold"])
    label(ax, ax10_x, ax10_y-0.35, "QUBO · SA\n· Roadmap", size=7.5, color=P["mgray"])
    # novel badge
    box(ax, ax10_x-0.9, ax10_y-1.42, 1.8, 0.32, P["gold"]+"55", P["gold"], lw=1.5, radius=0.01)
    label(ax, ax10_x, ax10_y-1.27, "NOVEL", size=8, bold=True, color=P["gold"])

    arrow(ax, 21.0+1.0, 9.0, ax10_x-0.5, ax10_y+1.25+0.23,
          col=P["amber"], lw=2.0, ms=12, conn="arc3,rad=-0.2")

    # Standards reference boxes
    std_items = [
        (2.5,  5.5, "NIST FIPS 203\nML-KEM (Kyber)",   P["blue"]),
        (5.5,  5.5, "NIST FIPS 204\nML-DSA (Dilithium)",P["blue"]),
        (8.5,  5.5, "NIST FIPS 205\nSLH-DSA (SPHINCS+)",P["blue"]),
        (11.8, 5.5, "IEEE 2933-2024\nTIPPSS Framework", P["purple"]),
        (15.1, 5.5, "HIPAA\nPHI Protection",            P["green"]),
        (18.0, 5.5, "OWASP LLM Top-10\nInjection Ref.", P["orange"]),
        (21.0, 5.5, "Kirkpatrick 1983\nSimul. Annealing",P["amber"]),
    ]
    ax.text(0.7, 6.15, "Standards & References:", fontsize=9, color=P["gray"], zorder=10)
    for sx, sy, stxt, scol in std_items:
        shadow_box(ax, sx-1.3, sy-0.55, 2.6, 1.1, scol+"22", scol, lw=1.5, radius=0.02)
        label(ax, sx, sy, stxt, size=8, color=P["white"])

    # ── TIER 3: Data / Output ─────────────────────────────────────────────
    box(ax, 0.4, 0.3, 23.2, 3.85, P["green"]+"12", P["green"], lw=2.5, radius=0.03)
    ax.text(0.7, 3.97, "TIER 3 — DATA & OUTPUT LAYER",
            fontsize=11, fontweight="bold", color=P["lgreen"], zorder=10)

    output_comps = [
        (2.0,  2.4, "fileuploadoutput/",  "payload.json\nresult.json\nsummary.csv",  P["teal"]),
        (5.5,  2.4, "test_outputs/\nunit_tests/",    "TC01-TC08\nTimestamped JSON\n8 test cases",  P["blue"]),
        (9.0,  2.4, "test_outputs/\nintegration/",  "CICIoMT + Synthea\nFile results",  P["blue"]),
        (12.5, 2.4, "Verdict Card",       "Safe / Partial /\nNot PQ Safe /\nCritical",  P["green"]),
        (16.0, 2.4, "TIPPSS\nSpider Chart", "6-pillar\nradar plot",  P["purple"]),
        (19.5, 2.4, "QIRO Roadmap",       "Selected\nDeferred\nPhased Plan",  P["amber"]),
        (22.5, 2.4, "Claude AI\nReport",  "Executive\nSummary",  P["navy"]),
    ]
    for ox, oy, otitle, odesc, ocol in output_comps:
        shadow_box(ax, ox-1.3, oy-1.0, 2.6, 1.9, ocol+"33", ocol, lw=2, radius=0.025)
        box(ax, ox-1.3, oy+0.6, 2.6, 0.32, ocol+"66", ocol, lw=1.3, radius=0.01)
        label(ax, ox, oy+0.76, otitle, size=8.5, bold=True, color=P["white"])
        label(ax, ox, oy-0.08, odesc, size=7.5, color=P["mgray"])

    # ── Connection arrows tier1→tier2 ─────────────────────────────────────
    arrow(ax, 5.0, 11.8, 5.0, 11.6, col=P["lblue"], lw=2.2)
    ax.text(5.4, 11.7, "HTTP POST (JSON payload)", fontsize=8.5,
            color=P["gold"], fontweight="bold", zorder=10)

    # tier2 → tier3
    arrow(ax, 20.0, 4.4, 20.0, 4.25, col=P["lgreen"], lw=2.2)
    ax.text(20.4, 4.32, "JSON Response", fontsize=8.5,
            color=P["lgreen"], fontweight="bold", zorder=10)

    plt.savefig(OUT / "architecture_diagram.png", dpi=DPI, bbox_inches="tight",
                facecolor=P["dark"], edgecolor="none")
    plt.close(fig)
    kb = (OUT / "architecture_diagram.png").stat().st_size // 1024
    print(f"  architecture_diagram.png  ({kb} KB)")


# ════════════════════════════════════════════════════════════════════════════
# DIAGRAM 3 — QIRO Optimization (Math + Use Case)
# ════════════════════════════════════════════════════════════════════════════

def diagram_qiro():
    fig = plt.figure(figsize=(26, 18), dpi=DPI)
    fig.patch.set_facecolor(P["dark"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 26); ax.set_ylim(0, 18)
    ax.axis("off"); ax.set_facecolor(P["dark"])

    # Title
    ax.text(13, 17.6, "QIRO — Quantum-Inspired Remediation Optimizer",
            ha="center", fontsize=22, fontweight="bold", color=P["gold"],
            fontfamily="monospace")
    ax.text(13, 17.15, "Novel Contribution: QUBO-Style Constrained Binary Optimisation via Simulated Annealing  "
            "|  Use Case: ICU Gateway Assessment",
            ha="center", fontsize=10.5, color=P["mgray"])

    # ════════════════════════════════════════════════════════
    # LEFT COLUMN — Mathematical Formulation
    # ════════════════════════════════════════════════════════
    box(ax, 0.3, 0.3, 11.0, 16.6, P["navy"]+"22", P["navy"], lw=2.5, radius=0.03)
    ax.text(5.8, 16.7, "MATHEMATICAL FORMULATION", ha="center", fontsize=14,
            fontweight="bold", color=P["lblue"], zorder=10)

    # 1. Decision Variable
    shadow_box(ax, 0.6, 14.95, 10.4, 1.6, P["blue"]+"33", P["blue"], lw=2, radius=0.02)
    ax.text(0.9, 16.3, "1.  Decision Variable", fontsize=12, fontweight="bold",
            color=P["lblue"], zorder=10)
    ax.text(5.8, 15.72,
            r"$x_i \in \{0, 1\}$      for each remediation action $i = 1,\ldots,n$",
            ha="center", fontsize=13, color=P["white"], zorder=10)
    ax.text(5.8, 15.25,
            r"$x_i = 1$  →  SELECT action     |     $x_i = 0$  →  DEFER action",
            ha="center", fontsize=10, color=P["mgray"], zorder=10)

    # 2. Benefit Score
    shadow_box(ax, 0.6, 12.95, 10.4, 1.85, P["purple"]+"33", P["purple"], lw=2, radius=0.02)
    ax.text(0.9, 14.57, "2.  Benefit Score per Action", fontsize=12,
            fontweight="bold", color=P["lpurple"], zorder=10)
    ax.text(5.8, 14.07,
            r"$B_i = R_i + P_i + S_i + T_i$",
            ha="center", fontsize=15, color=P["gold"], zorder=10,
            fontweight="bold")

    score_items = [
        (1.8,  13.37, r"$R_i$", "Risk\nreduction",   P["red"]),
        (4.3,  13.37, r"$P_i$", "PQ\nurgency",       P["blue"]),
        (6.8,  13.37, r"$S_i$", "Safety\ncriticality",P["orange"]),
        (9.3,  13.37, r"$T_i$", "TIPPSS\nimpact",    P["purple"]),
    ]
    for sx, sy, sym, sdesc, scol in score_items:
        box(ax, sx-0.9, sy-0.35, 1.8, 0.98, scol+"44", scol, lw=1.8, radius=0.018)
        ax.text(sx, sy+0.32, sym, ha="center", fontsize=13,
                color=P["white"], fontweight="bold", zorder=10)
        label(ax, sx, sy-0.12, sdesc, size=8, color=P["mgray"])

    # 3. Objective Function
    shadow_box(ax, 0.6, 10.7, 10.4, 2.05, P["green"]+"22", P["green"], lw=2, radius=0.02)
    ax.text(0.9, 12.52, "3.  Optimisation Objective", fontsize=12,
            fontweight="bold", color=P["lgreen"], zorder=10)
    ax.text(5.8, 11.97,
            r"$\max_x \sum_{i=1}^{n} B_i \, x_i$",
            ha="center", fontsize=16, color=P["lgreen"], fontweight="bold", zorder=10)
    ax.text(5.8, 11.37,
            r"Subject to:  $\sum C_i x_i \leq C_{\max}$    and    $\sum D_i x_i \leq D_{\max}$",
            ha="center", fontsize=11, color=P["white"], zorder=10)
    ax.text(5.8, 10.98,
            r"$C_i$ = remediation cost  ·  $D_i$ = service downtime  ·  $x_i \in \{0,1\}$",
            ha="center", fontsize=9.5, color=P["mgray"], zorder=10)

    # 4. Energy Function
    shadow_box(ax, 0.6, 7.9, 10.4, 2.65, P["amber"]+"22", P["amber"], lw=2, radius=0.02)
    ax.text(0.9, 10.32, "4.  Penalty-Based Energy Function  E(x)", fontsize=12,
            fontweight="bold", color=P["gold"], zorder=10)
    ax.text(5.8, 9.82,
            r"$E(x) = -\sum B_i x_i$",
            ha="center", fontsize=14, color=P["gold"], fontweight="bold", zorder=10)
    ax.text(5.8, 9.35,
            r"$+ \;\lambda_C \left[\max(0,\,\sum C_i x_i - C_{\max})\right]^2$",
            ha="center", fontsize=12, color=P["red"], zorder=10)
    ax.text(5.8, 8.88,
            r"$+ \;\lambda_D \left[\max(0,\,\sum D_i x_i - D_{\max})\right]^2$",
            ha="center", fontsize=12, color=P["orange"], zorder=10)
    ax.text(5.8, 8.42,
            r"$+ \;\lambda_K \sum K_i x_i$",
            ha="center", fontsize=12, color=P["purple"], zorder=10)
    ax.text(5.8, 8.08,
            r"$x^* = \arg\min_x \; E(x)$",
            ha="center", fontsize=13, color=P["white"], fontweight="bold", zorder=10)

    # 5. SA Algorithm
    shadow_box(ax, 0.6, 5.2, 10.4, 2.55, P["teal"]+"22", P["teal"], lw=2, radius=0.02)
    ax.text(0.9, 7.52, "5.  Simulated Annealing (Kirkpatrick et al., 1983)", fontsize=12,
            fontweight="bold", color=P["lteal"], zorder=10)
    sa_lines = [
        r"$T_{start} = 100.0$   $\alpha = 0.995$ (geometric cooling)   Iterations: 1,000",
        r"Flip random $x_j$  $\rightarrow$  Compute $\Delta E$",
        r"Accept if $\Delta E < 0$  OR  with probability $e^{-\Delta E / T}$",
        r"(Metropolis-Hastings)  Cool:  $T \leftarrow T \cdot \alpha$",
    ]
    for li, line in enumerate(sa_lines):
        ax.text(5.8, 7.0 - li * 0.43, line, ha="center", fontsize=10,
                color=P["white"] if li < 2 else P["mgray"], zorder=10)

    # 6. Output
    shadow_box(ax, 0.6, 2.8, 10.4, 2.2, P["lgreen"]+"18", P["lgreen"], lw=2, radius=0.02)
    ax.text(0.9, 4.77, "6.  QIRO Output", fontsize=12, fontweight="bold",
            color=P["lgreen"], zorder=10)
    out_items = [
        (r"$\mathcal{A}_{selected} = \{i \mid x_i^* = 1\}$",  "Actions to fix now",        P["lgreen"]),
        (r"$\mathcal{A}_{deferred} = \{i \mid x_i^* = 0\}$",  "Actions deferred",          P["amber"]),
        (r"$C_{rem} = C_{\max} - \sum C_i x_i^*$",             "Budget remaining",          P["blue"]),
        (r"$D_{rem} = D_{\max} - \sum D_i x_i^*$",             "Downtime remaining",        P["teal"]),
    ]
    for oi, (omath, odesc, ocol) in enumerate(out_items):
        oy = 4.3 - oi * 0.42
        ax.text(1.5, oy, omath, fontsize=10, color=ocol, zorder=10, va="center")
        ax.text(7.5, oy, f"->  {odesc}", fontsize=9, color=P["mgray"],
                zorder=10, va="center")

    # ════════════════════════════════════════════════════════
    # RIGHT COLUMN — Use Case: ICU Gateway
    # ════════════════════════════════════════════════════════
    box(ax, 12.0, 0.3, 13.7, 16.6, P["red"]+"0F", P["red"], lw=2.5, radius=0.03)
    ax.text(18.85, 16.7, "USE CASE:  ICU GATEWAY ASSESSMENT", ha="center",
            fontsize=14, fontweight="bold", color=P["red"], zorder=10)

    # System config
    shadow_box(ax, 12.3, 14.95, 13.1, 1.6, P["red"]+"33", P["orange"], lw=2, radius=0.02)
    ax.text(12.6, 16.32, "Input — System Configuration", fontsize=11,
            fontweight="bold", color=P["orange"], zorder=10)
    config_items = [
        ("TLS Version:",      "TLS 1.2",     P["orange"]),
        ("Key Exchange:",     "ECDHE-P256",  P["red"]),
        ("Cert Signature:",   "ECDSA-P256",  P["red"]),
        ("Cert Key:",         "RSA-2048",    P["red"]),
        ("Hash:",             "SHA-256",     P["amber"]),
        ("Data Lifetime:",    "15 years",    P["red"]),
    ]
    for ci, (ck, cv, ccol) in enumerate(config_items):
        cx_off = 12.6 + (ci % 3) * 4.2
        cy_off = 15.62 - (ci // 3) * 0.38
        ax.text(cx_off, cy_off, f"{ck} ", fontsize=8.5, color=P["gray"],
                va="center", zorder=10)
        ax.text(cx_off + 2.1, cy_off, cv, fontsize=8.5, color=ccol,
                fontweight="bold", va="center", zorder=10)

    # Detected findings → candidate actions table
    shadow_box(ax, 12.3, 9.8, 13.1, 4.85, P["darkb"], P["mgray"], lw=1.5, radius=0.02)
    ax.text(12.6, 14.42, "Candidate Remediation Actions  (n = 7)", fontsize=11,
            fontweight="bold", color=P["white"], zorder=10)

    # Table header
    col_xs = [12.7, 15.8, 17.6, 19.3, 21.0, 22.7, 24.5]
    for hx, htxt, hcol in zip(col_xs,
        ["Action", "Ri", "Pi", "Si", "Ti", "Cost ($K)", "DT (h)"],
        [P["white"], P["red"], P["blue"], P["orange"], P["purple"], P["gray"], P["gray"]]):
        ax.text(hx, 14.0, htxt, fontsize=9, fontweight="bold",
                color=hcol, zorder=10)
    ax.plot([12.5, 25.2], [13.75, 13.75], color=P["mgray"],
            linewidth=0.9, zorder=5)

    actions_uc = [
        ("Prompt Inject Firewall",  25, 0,  20, 30,  8,  1,  True,  "CRITICAL"),
        ("Device Re-Authentication",35, 0,  20, 20, 10,  2,  True,  "CRITICAL"),
        ("PQ Cert Migration",       30, 25,  0, 30, 20,  4,  True,  "HIGH"),
        ("TLS 1.3 Upgrade",         35, 30,  0, 25, 35,  8,  False, "HIGH"),
        ("PHI Redaction Middleware",20,  0, 10, 40,  8,  2,  True,  "HIGH"),
        ("Full ML-KEM Migration",   40, 35,  0, 25, 45, 10,  False, "CRITICAL"),
        ("Firmware Update",         15,  0,  5, 20, 12,  6,  False, "MEDIUM"),
    ]

    BUDGET   = 100_000
    DOWNTIME = 40
    sel_cost = sum(a[5]*1000 for a in actions_uc if a[7])
    sel_dt   = sum(a[6] for a in actions_uc if a[7])

    for ai, (aname, ri, pi, si, ti, cost, dt, selected, sev) in enumerate(actions_uc):
        row_y = 13.3 - ai * 0.48
        bi = ri + pi + si + ti
        row_bg = P["green"]+"22" if selected else P["darkb"]
        row_ec = P["lgreen"] if selected else P["darkb"]
        box(ax, 12.5, row_y-0.19, 12.7, 0.38, row_bg, row_ec, lw=1.2, radius=0.01)

        sel_marker = "SEL" if selected else "DEF"
        sel_col    = P["lgreen"] if selected else P["amber"]
        ax.text(12.68, row_y, sel_marker, fontsize=7.5, color=sel_col,
                fontweight="bold", va="center", zorder=10)
        ax.text(12.85, row_y, aname[:24], fontsize=8.5,
                color=P["white"] if selected else P["gray"],
                va="center", zorder=10)

        sev_col = P["red"] if sev=="CRITICAL" else (P["orange"] if sev=="HIGH" else P["amber"])
        for vx, val in zip([15.8, 17.6, 19.3, 21.0],
                           [str(ri), str(pi), str(si), str(ti)]):
            ax.text(vx, row_y, val, fontsize=8.5, color=P["white"] if selected else P["gray"],
                    ha="center", va="center", zorder=10)
        ax.text(22.7, row_y, f"${cost}K", fontsize=8.5,
                color=P["gold"] if selected else P["gray"],
                ha="center", va="center", fontweight="bold" if selected else "normal",
                zorder=10)
        ax.text(24.5, row_y, f"{dt}h", fontsize=8.5,
                color=P["teal"] if selected else P["gray"],
                ha="center", va="center", zorder=10)

        # Benefit bar
        bar_w = bi / 130 * 2.8
        if selected:
            box(ax, 15.9, row_y-0.14, bar_w, 0.27, P["gold"]+"88", P["gold"],
                lw=0.8, radius=0.005)

    ax.plot([12.5, 25.2], [9.98, 9.98], color=P["mgray"], linewidth=0.9, zorder=5)
    ax.text(12.68, 9.78, f"SELECTED: 4 actions  |  Budget: ${sel_cost//1000}K / $100K  |  Downtime: {sel_dt}h / 40h",
            fontsize=9, color=P["lgreen"], fontweight="bold", zorder=10)

    # QIRO Process flow diagram
    shadow_box(ax, 12.3, 5.4, 13.1, 4.15, P["amber"]+"18", P["amber"], lw=2, radius=0.02)
    ax.text(12.6, 9.33, "QIRO Optimisation Flow", fontsize=11,
            fontweight="bold", color=P["gold"], zorder=10)

    steps_qiro = [
        (14.2, 8.85, "Initialise", r"$x \leftarrow$ random $\{0,1\}^n$", P["blue"]),
        (14.2, 7.85, "Compute E(x)", r"$E = -\sum B_i x_i + \text{penalties}$", P["amber"]),
        (14.2, 6.85, "Flip random $x_j$", r"Accept if $\Delta E<0$ or $e^{-\Delta E/T}$", P["purple"]),
        (14.2, 5.85, "Cool temperature", r"$T \leftarrow T \cdot 0.995$,  1000 iters", P["teal"]),
    ]
    for sx, sy, stitle, sdesc, scol in steps_qiro:
        shadow_box(ax, sx-1.6, sy-0.35, 3.2, 0.95, scol+"44", scol, lw=1.8, radius=0.018)
        ax.text(sx, sy+0.24, stitle, ha="center", fontsize=9.5, fontweight="bold",
                color=P["white"], zorder=10)
        ax.text(sx, sy-0.13, sdesc, ha="center", fontsize=8.5,
                color=P["mgray"], zorder=10)

    for i in range(len(steps_qiro)-1):
        arrow(ax, steps_qiro[i][0], steps_qiro[i][1]-0.35,
              steps_qiro[i+1][0], steps_qiro[i+1][1]+0.60,
              col=P["gold"], lw=2.0, ms=13)

    # Branch to "selected" vs "deferred"
    arrow(ax, 14.2, 5.5, 14.2, 5.4, col=P["gold"], lw=2.0, ms=13)
    arrow(ax, 14.2, 5.4, 12.6, 5.4, col=P["lgreen"], lw=1.6, ms=10)
    arrow(ax, 14.2, 5.4, 19.0, 5.4, col=P["amber"], lw=1.6, ms=10)

    # Result columns
    shadow_box(ax, 16.0, 6.4, 4.5, 2.7, P["lgreen"]+"22", P["lgreen"], lw=2, radius=0.02)
    ax.text(18.25, 8.87, "SELECTED ACTIONS", ha="center", fontsize=10,
            fontweight="bold", color=P["lgreen"], zorder=10)
    for ii, aname in enumerate(["Prompt Inject Firewall",
                                  "Device Re-Auth",
                                  "PQ Cert Migration",
                                  "PHI Redaction"]):
        ax.text(16.3, 8.4 - ii * 0.42,
                f"  {ii+1}. {aname}", fontsize=8.5, color=P["lgreen"],
                va="center", zorder=10)

    shadow_box(ax, 20.7, 6.4, 4.2, 2.7, P["amber"]+"22", P["amber"], lw=2, radius=0.02)
    ax.text(22.8, 8.87, "DEFERRED ACTIONS", ha="center", fontsize=10,
            fontweight="bold", color=P["amber"], zorder=10)
    defer_reasons = [
        ("TLS 1.3 Upgrade", "Cost > budget remaining"),
        ("Full ML-KEM",     "Cost > budget remaining"),
        ("Firmware Update", "Lower priority score"),
    ]
    for ii, (aname, reason) in enumerate(defer_reasons):
        ay = 8.4 - ii * 0.55
        ax.text(20.9, ay,    f"  {ii+1}. {aname}", fontsize=8.5,
                color=P["amber"], va="center", zorder=10)
        ax.text(20.9, ay-0.2, f"      -> {reason}", fontsize=7.5,
                color=P["gray"], va="center", zorder=10)

    # Phased roadmap
    shadow_box(ax, 12.3, 0.5, 13.1, 4.7, P["navy"]+"44", P["blue"], lw=2, radius=0.02)
    ax.text(18.85, 5.0, "Phased Migration Roadmap", ha="center", fontsize=11,
            fontweight="bold", color=P["blue"], zorder=10)

    phases_uc = [
        ("Phase 1\n0–6 months",   P["red"],    ["Prompt Injection Firewall", "Device Re-Authentication"],
         "CRITICAL controls — immediate action required"),
        ("Phase 2\n6–18 months",  P["amber"],  ["PQ Certificate Migration", "PHI Redaction Middleware"],
         "PQ migration + privacy controls"),
        ("Phase 3\n18–36 months", P["lgreen"], ["TLS 1.3 Upgrade (when budget permits)", "Full ML-KEM Migration"],
         "Complete post-quantum deployment"),
    ]
    for pi, (ptitle, pcol, pitems, pdesc) in enumerate(phases_uc):
        px = 13.3 + pi * 4.3
        shadow_box(ax, px, 0.7, 3.8, 4.1, pcol+"22", pcol, lw=2.2, radius=0.025)
        box(ax, px, 4.4, 3.8, 0.45, pcol+"66", pcol, lw=1.5, radius=0.01)
        label(ax, px+1.9, 4.62, ptitle, size=9, bold=True, color=P["white"])
        ax.text(px+0.15, 4.25, pdesc, fontsize=7.5, color=P["mgray"], va="center", zorder=10)
        for ii, item in enumerate(pitems):
            iy = 3.7 - ii * 0.5
            box(ax, px+0.1, iy-0.18, 3.5, 0.36, pcol+"33", pcol, lw=1.0, radius=0.01)
            ax.text(px+0.25, iy, f"• {item}", fontsize=8, color=P["white"],
                    va="center", zorder=10)
        cost_str = ["$18K · 3h", "$28K · 6h", "Deferred (budget exceeded)"][pi]
        ax.text(px+1.9, 0.9, cost_str, ha="center", fontsize=8.5,
                color=pcol, fontweight="bold", zorder=10)

    # QUBO connection note
    ax.text(6.0, 2.2,
            "QUBO / Ising connection:\n"
            r"Map $x_i \in \{0,1\}$ to spin $s_i = 2x_i - 1 \in \{-1,+1\}$" "\n"
            "Energy E(x) equivalent to Ising Hamiltonian\n"
            "-> same problem class solved by quantum annealers",
            ha="center", fontsize=9, color=P["lpurple"], zorder=10,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=P["purple"]+"22",
                      edgecolor=P["purple"], linewidth=1.5))

    plt.savefig(OUT / "qiro_optimization_diagram.png", dpi=DPI, bbox_inches="tight",
                facecolor=P["dark"], edgecolor="none")
    plt.close(fig)
    kb = (OUT / "qiro_optimization_diagram.png").stat().st_size // 1024
    print(f"  qiro_optimization_diagram.png  ({kb} KB)")


# ── Run all ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nGenerating high-quality architecture diagrams ...\n")
    diagram_data_flow()
    diagram_architecture()
    diagram_qiro()
    print("\nAll diagrams saved to 00_Documention/")
