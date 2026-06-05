"""
TIPPSS SafeGuard-PQ — Consolidated Technical PDF Report
========================================================
Generates: 00_Documention/TIPPSS_SafeGuard_PQ_Technical_Report.pdf

Sections:
  Cover Page
  1. Problem Statement & Threat Model
  2. Solution Overview
  3. System Architecture Diagram
  4. End-to-End Data Flow Diagram
  5. Network Topology & Attack Surface
  6. QIRO Optimisation Diagram
  7. Test Results & Validation
  8. Standards Compliance Matrix
"""

import io
import pathlib
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
import matplotlib.colors as mcolors
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas

OUT = pathlib.Path("00_Documention")
OUT.mkdir(exist_ok=True)
PDF_PATH = OUT / "TIPPSS_SafeGuard_PQ_Technical_Report.pdf"

DPI = 180

# ── Colour constants ──────────────────────────────────────────────────────────
NAVY   = "#1F3864"; BLUE   = "#2563EB"; LBLUE  = "#60A5FA"
TEAL   = "#0D9488"; GREEN  = "#16A34A"; LGREEN = "#4ADE80"
AMBER  = "#D97706"; GOLD   = "#F59E0B"; ORANGE = "#EA580C"
RED    = "#DC2626"; PURPLE = "#7C3AED"; PINK   = "#EC4899"
WHITE  = "#FFFFFF"; LGRAY  = "#F1F5F9"; MGRAY  = "#CBD5E1"
DARK   = "#0F172A"; DARKB  = "#1E293B"

RL_NAVY   = HexColor(NAVY);   RL_BLUE   = HexColor(BLUE)
RL_TEAL   = HexColor(TEAL);   RL_GREEN  = HexColor(GREEN)
RL_AMBER  = HexColor(AMBER);  RL_RED    = HexColor(RED)
RL_PURPLE = HexColor(PURPLE); RL_DARK   = HexColor(DARK)
RL_LGRAY  = HexColor(LGRAY);  RL_MGRAY  = HexColor(MGRAY)
RL_GOLD   = HexColor(GOLD);   RL_WHITE  = HexColor(WHITE)
RL_ORANGE = HexColor(ORANGE)

PW, PH = A4  # 595 × 842 pt

# ── Matplotlib diagram helpers ────────────────────────────────────────────────
P = dict(navy=NAVY, blue=BLUE, lblue=LBLUE, teal=TEAL, green=GREEN, lgreen=LGREEN,
         amber=AMBER, gold=GOLD, orange=ORANGE, red=RED, purple=PURPLE,
         white=WHITE, mgray=MGRAY, dark=DARK, darkb=DARKB)

def bbox(ax, x, y, w, h, fc, ec, lw=1.5, r=0.02, alpha=1.0, z=3):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={r}",
                       facecolor=fc, edgecolor=ec, linewidth=lw,
                       alpha=alpha, zorder=z)
    ax.add_patch(p); return p

def lbl(ax, x, y, t, sz=9, c=WHITE, bold=False, ha="center", va="center",
        z=10, wrap=None, ls=1.4):
    ax.text(x, y, t, ha=ha, va=va, fontsize=sz,
            color=c, fontweight="bold" if bold else "normal",
            zorder=z, multialignment=ha, linespacing=ls)

def arr(ax, x1, y1, x2, y2, col=BLUE, lw=1.8, ms=13, conn="arc3,rad=0.0"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=lw,
                                mutation_scale=ms, connectionstyle=conn), zorder=5)

_tmp_files = []

def fig_png(fig, dpi=DPI, tag="diag"):
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=f"_{tag}.png")
    os.close(fd)
    fig.savefig(path, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    fw, fh = fig.get_size_inches()
    plt.close(fig)
    _tmp_files.append(path)
    return path, fw, fh   # also return figure size in inches

def rl_img(path_tuple, target_w_pt):
    """Create Image flowable with explicit height derived from figure aspect ratio."""
    path, fw, fh = path_tuple
    aspect = fh / fw
    h_pt = target_w_pt * aspect
    return Image(path, width=target_w_pt, height=h_pt)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM A — System Architecture
# ══════════════════════════════════════════════════════════════════════════════
def make_architecture():
    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor(DARK); ax.set_facecolor(DARK)
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.axis("off")

    ax.text(8, 9.72, "System Architecture — Three-Tier Pipeline",
            ha="center", fontsize=15, fontweight="bold",
            color=WHITE, fontfamily="monospace")

    # Tier bands
    tiers = [
        (0.2, 7.8, 15.6, 1.75, BLUE+"18",   BLUE,   "TIER 1 — PRESENTATION",   "Streamlit Dashboard  localhost:8501"),
        (0.2, 4.5, 15.6, 3.05, PURPLE+"18", PURPLE, "TIER 2 — ORCHESTRATION",  "Sequential Agentic Framework  localhost:5678"),
        (0.2, 0.3, 15.6, 3.95, GREEN+"18",  GREEN,  "TIER 3 — DATA & OUTPUT",  "Timestamped JSON + CSV Results"),
    ]
    for tx, ty, tw, th, tfc, tec, tlabel, tsub in tiers:
        bbox(ax, tx, ty, tw, th, tfc, tec, lw=2.2, r=0.02, z=1)
        ax.text(tx+0.15, ty+th-0.18, tlabel, fontsize=9, fontweight="bold",
                color=tec, zorder=5)
        ax.text(tx+0.15, ty+th-0.42, tsub, fontsize=7.5, color=MGRAY, zorder=5)

    # Tier 1 components
    t1_comps = [
        (1.6,  8.3, "Scenario\nSelector\n7 pre-built",  BLUE),
        (3.8,  8.3, "File\nUploader\n.pcap.csv",         BLUE),
        (6.0,  8.3, "Feature\nExtractor\n100 rows",      TEAL),
        (8.2,  8.3, "Constraint\nSliders\nBudget/DT",    PURPLE),
        (10.4, 8.3, "Result\nRenderer\nCharts/Cards",    GREEN),
        (13.0, 8.3, "Payload\nConstructor\nJSON build",  NAVY),
    ]
    for cx, cy, ctxt, ccol in t1_comps:
        bbox(ax, cx-0.85, cy-0.45, 1.7, 1.22, ccol+"44", ccol, lw=1.8, r=0.02)
        lbl(ax, cx, cy+0.22, ctxt, sz=7.5)

    # HTTP arrow
    arr(ax, 13.0, 7.85, 13.0, 7.57, col=GOLD, lw=2.2)
    ax.text(13.5, 7.7, "HTTP POST", fontsize=7.5, color=GOLD, fontweight="bold", zorder=10)

    # Tier 2 — agents
    agents = [
        (1.2,  "A1\nInput\nValidator",    BLUE,   LBLUE),
        (3.0,  "A2\nCrypto\nClassifier",  BLUE,   LBLUE),
        (4.8,  "A3\nPQ\nBenchmark",       PURPLE, "#A78BFA"),
        (6.6,  "A4\nIoT\nIdentity",       PURPLE, "#A78BFA"),
        (8.4,  "A5\nPrivacy\nPHI",        PINK,   GOLD),
        (10.2, "A6\nSecret\nExposure",    ORANGE, GOLD),
        (12.0, "A7\nSafety\nRisk",        RED,    GOLD),
        (13.8, "A8\nTIPPSS\nScorer",      NAVY,   LBLUE),
        (15.0, "A9\nQIRO\nOptimizer",     AMBER,  GOLD),
    ]
    for i, (ax_x, atxt, afc, aec) in enumerate(agents):
        bbox(ax, ax_x-0.7, 4.75, 1.4, 2.5, afc+"44", aec, lw=1.8, r=0.02)
        bbox(ax, ax_x-0.7, 6.92, 1.4, 0.38, afc+"88", aec, lw=1.3, r=0.01)
        lbl(ax, ax_x, 7.11, atxt.split("\n")[0], sz=7.5, bold=True)
        lbl(ax, ax_x, 5.98, "\n".join(atxt.split("\n")[1:]), sz=7, c=MGRAY)
        if i < len(agents)-1:
            arr(ax, ax_x+0.7, 6.0, agents[i+1][0]-0.7, 6.0, col=MGRAY, lw=1.3, ms=10)

    # NOVEL badge on A9
    bbox(ax, 14.3, 4.78, 1.36, 0.28, GOLD+"55", GOLD, lw=1.3, r=0.01)
    lbl(ax, 15.0, 4.93, "NOVEL", sz=7, bold=True, c=GOLD)

    # Standards row
    stds = [
        (2.0,  "NIST FIPS 203\nML-KEM",   BLUE),
        (4.4,  "NIST FIPS 204\nML-DSA",   BLUE),
        (6.8,  "NIST FIPS 205\nSLH-DSA",  BLUE),
        (9.2,  "IEEE 2933-2024\nTIPPSS",  PURPLE),
        (11.6, "HIPAA\nPHI Protection",   GREEN),
        (14.0, "OWASP LLM\nTop-10",       ORANGE),
    ]
    for sx, stxt, scol in stds:
        bbox(ax, sx-1.0, 4.52, 2.0, 0.78, scol+"1A", scol, lw=1.2, r=0.015)
        lbl(ax, sx, 4.91, stxt, sz=6.5, c=WHITE)

    # Tier 3 outputs
    outs = [
        (1.8,  "Verdict Card\nPQ Risk Score",       GREEN,  LGREEN),
        (4.6,  "TIPPSS Spider\n6-Pillar Chart",     BLUE,   LBLUE),
        (7.4,  "QIRO Roadmap\nSelected + Deferred", AMBER,  GOLD),
        (10.2, "fileuploadoutput/\nJSON + CSV",     TEAL,   "#5EEAD4"),
        (13.0, "test_outputs/\nUnit + Integration", NAVY,   LBLUE),
    ]
    for ox, otxt, ofc, oec in outs:
        bbox(ax, ox-1.2, 0.55, 2.4, 1.65, ofc+"33", oec, lw=1.8, r=0.02)
        bbox(ax, ox-1.2, 1.9,  2.4, 0.32, ofc+"66", oec, lw=1.2, r=0.01)
        lbl(ax, ox, 2.06, otxt.split("\n")[0], sz=8, bold=True)
        lbl(ax, ox, 0.98, "\n".join(otxt.split("\n")[1:]), sz=7.5, c=MGRAY)

    arr(ax, 14.6, 4.52, 14.0, 2.22, col=GOLD, lw=2.0)
    return fig_png(fig)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM B — Data Flow
# ══════════════════════════════════════════════════════════════════════════════
def make_dataflow():
    fig, ax = plt.subplots(figsize=(16, 11))
    fig.patch.set_facecolor(DARK); ax.set_facecolor(DARK)
    ax.set_xlim(0, 16); ax.set_ylim(0, 11); ax.axis("off")

    ax.text(8, 10.72, "End-to-End Data Flow — Sequential Agentic Pipeline",
            ha="center", fontsize=14, fontweight="bold",
            color=WHITE, fontfamily="monospace")

    lane_defs = [
        (9.8, 1.3,  TEAL,   "INPUT"),
        (8.0, 1.5,  BLUE,   "PRESENTATION"),
        (5.8, 1.9,  PURPLE, "DETECTION AGENTS"),
        (3.5, 1.5,  NAVY,   "SCORING"),
        (1.8, 1.5,  AMBER,  "QIRO OPTIMIZER"),
        (0.2, 1.3,  GREEN,  "OUTPUT"),
    ]
    lane_ys = [9.3, 7.6, 5.5, 3.7, 2.0, 0.3]
    lane_hs = [1.25, 1.7, 2.3, 1.4, 1.4, 1.4]

    for (lx, _, lcol, lname), ly, lh in zip(lane_defs, lane_ys, lane_hs):
        bbox(ax, 0.1, ly, 15.8, lh, lcol+"12", lcol, lw=1.8, r=0.015, z=1)
        ax.plot([0.1, 15.9], [ly+lh, ly+lh], color=lcol+"66", lw=0.7, ls="--", zorder=2)
        bbox(ax, 0.1, ly, 1.6, lh, lcol+"44", lcol, lw=1.2, r=0.01, z=2)
        lbl(ax, 0.9, ly+lh/2, lname, sz=7.5, bold=True, c=WHITE)

    # INPUT row
    for ix, itxt, icol in [
        (4.0,  "Pre-built Scenarios\n7 Clinical Simulations", TEAL),
        (7.2,  "CICIoMT2024 Files\n.pcap.csv Network",        TEAL),
        (10.4, "Synthea Records\npatients.csv",                TEAL),
        (13.6, "Real System Config\nTLS + Device + AI Logs",  TEAL),
    ]:
        bbox(ax, ix-1.5, 9.42, 3.0, 1.0, icol+"33", icol, lw=1.8, r=0.02)
        lbl(ax, ix, 9.92, itxt, sz=8, bold=True)
        arr(ax, ix, 9.42, ix, 9.3, col=icol, lw=1.5, ms=10)

    # PRESENTATION row
    for px, ptxt in [(3.5,"Scenario\nSelector"),(5.5,"File\nUploader"),
                     (7.5,"Feature\nExtractor"),(9.5,"Constraint\nSliders")]:
        bbox(ax, px-0.85, 7.72, 1.7, 1.08, BLUE+"44", LBLUE, lw=1.5, r=0.015)
        lbl(ax, px, 8.26, ptxt, sz=7.5)

    bbox(ax, 11.5, 7.72, 3.8, 1.08, BLUE+"22", BLUE, lw=1.5, r=0.015)
    lbl(ax, 13.4, 8.26, "Payload Constructor\nsystem_id · tls_config · device_logs\nai_prompt_logs · constraints", sz=7.2)
    arr(ax, 10.5, 8.26, 11.5, 8.26, col=LBLUE, lw=1.8)
    arr(ax, 13.4, 7.72, 13.4, 7.45, col=GOLD, lw=2.2)
    ax.text(13.75, 7.57, "HTTP POST (JSON)", fontsize=7.5, color=GOLD, fontweight="bold", zorder=10)

    # DETECTION AGENTS row
    det_agents = [
        (2.4,  "A1 Input\nValidator",    BLUE),
        (4.3,  "A2 Crypto\nClassifier",  BLUE),
        (6.2,  "A3 PQ\nBenchmark",       PURPLE),
        (8.1,  "A4 IoT\nIdentity",       PURPLE),
        (10.0, "A5 Privacy\nPHI",        PINK),
        (11.9, "A6 Secret\nExposure",    ORANGE),
        (13.8, "A7 Safety\nRisk",        RED),
    ]
    for i, (dx, dtxt, dcol) in enumerate(det_agents):
        bbox(ax, dx-0.8, 5.65, 1.6, 1.65, dcol+"44", dcol, lw=1.8, r=0.018)
        lbl(ax, dx, 6.47, dtxt, sz=7.5)
        if i < len(det_agents)-1:
            arr(ax, dx+0.8, 6.47, det_agents[i+1][0]-0.8, 6.47, col=MGRAY, lw=1.2, ms=9)

    arr(ax, 13.4, 7.45, 13.4, 7.3, col=GOLD, lw=2.0)
    arr(ax, 13.4, 7.3,  2.4,  7.3, col=GOLD, lw=1.8)
    arr(ax, 2.4,  7.3,  2.4, 7.30, col=GOLD, lw=1.5)

    # SCORING row
    bbox(ax, 2.0, 3.82, 5.5, 1.12, NAVY+"44", LBLUE, lw=2.0, r=0.02)
    lbl(ax, 4.75, 4.38, "Agent 8 — TIPPSS Six-Pillar Scorer", sz=9, bold=True, c=LBLUE)
    for pi, (pil, pc) in enumerate(zip(
        ["Trust","Identity","Privacy","Protection","Safety","Security"],
        [TEAL,BLUE,PURPLE,NAVY,RED,ORANGE])):
        bbox(ax, 2.2+pi*0.88, 3.88, 0.82, 0.36, pc+"88", pc, lw=1.0, r=0.01)
        lbl(ax, 2.61+pi*0.88, 4.06, pil[:5], sz=6.5)

    bbox(ax, 8.5, 3.82, 4.0, 1.12, GREEN+"33", LGREEN, lw=2.0, r=0.02)
    lbl(ax, 10.5, 4.38, "Risk Verdict", sz=9, bold=True, c=LGREEN)
    for vi, (vtxt, vc) in enumerate([("Safe 0-25",GREEN),("Partially Safe 26-50",GOLD),
                                      ("Not PQ Safe 51-75",ORANGE),("Critical 76-100",RED)]):
        bbox(ax, 8.65, 4.55-vi*0.22, 3.7, 0.2, vc+"44", vc, lw=0.8, r=0.006)
        lbl(ax, 10.5, 4.65-vi*0.22, vtxt, sz=6.8)

    arr(ax, 13.8, 5.65, 13.8, 4.95, col=MGRAY, lw=1.6)
    arr(ax, 2.4,  5.65, 4.75, 4.95, col=MGRAY, lw=1.6)
    arr(ax, 7.5,  4.38, 8.5,  4.38, col=LBLUE, lw=1.8)

    # QIRO row
    bbox(ax, 2.0, 2.12, 11.5, 1.1, AMBER+"22", GOLD, lw=2.2, r=0.02)
    lbl(ax, 7.75, 2.67, "Agent 9 — QIRO Optimizer  [Novel Contribution]", sz=9.5, bold=True, c=GOLD)
    for qi, (qx, qtxt) in enumerate([
        (3.2, "Generate\nActions"), (5.1, "Score\nBi=Ri+Pi+Si+Ti"),
        (7.1, "Energy\nFunction E(x)"), (9.1, "Simulated\nAnnealing"),
        (11.1,"Select /\nDefer")]):
        bbox(ax, qx-0.75, 2.18, 1.5, 0.65, AMBER+"55", GOLD, lw=1.3, r=0.012)
        lbl(ax, qx, 2.50, qtxt, sz=7)
        if qi < 4:
            arr(ax, qx+0.75, 2.50, [5.1,7.1,9.1,11.1][qi]-0.75, 2.50, col=GOLD, lw=1.4, ms=10)

    bbox(ax, 13.7, 2.12, 2.0, 1.1, RED+"1A", RED, lw=1.5, r=0.015)
    lbl(ax, 14.7, 2.67, "Constraints\nBudget/DT", sz=7.5, c=WHITE)
    arr(ax, 13.7, 2.67, 11.85, 2.50, col=RED, lw=1.6, ms=10)

    arr(ax, 10.5, 3.82, 10.5, 3.22, col=MGRAY, lw=1.6)
    arr(ax, 10.5, 3.22, 7.75, 3.22, col=MGRAY, lw=1.6)
    arr(ax, 7.75, 3.22, 7.75, 3.22, col=AMBER, lw=2.0)

    # OUTPUT row
    for ox, otxt, ofc in [
        (3.0,  "Verdict Card\nPQ Risk Score",       GREEN),
        (6.0,  "TIPPSS Spider\n6-Pillar Chart",     BLUE),
        (9.0,  "QIRO Roadmap\nSelected+Deferred",   AMBER),
        (12.5, "JSON + CSV\nTimestamped Results",   TEAL),
    ]:
        bbox(ax, ox-1.35, 0.42, 2.7, 1.12, ofc+"33", ofc, lw=1.8, r=0.02)
        lbl(ax, ox, 0.98, otxt, sz=8, bold=True)

    arr(ax, 7.75, 2.12, 7.75, 1.55, col=GOLD, lw=2.5)
    arr(ax, 7.75, 1.55, 3.0,  1.55, col=GOLD, lw=1.8)
    for ox in [3.0, 6.0, 9.0, 12.5]:
        arr(ax, ox, 1.55, ox, 1.54, col=GOLD, lw=1.6, ms=10)

    return fig_png(fig)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM C — Network Topology & Threat Model
# ══════════════════════════════════════════════════════════════════════════════
def make_network_topology():
    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor(DARK); ax.set_facecolor(DARK)
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.axis("off")

    ax.text(8, 9.72, "Network Topology & Threat Model — Clinical IoT Attack Surface",
            ha="center", fontsize=14, fontweight="bold",
            color=WHITE, fontfamily="monospace")

    # Hospital network zone
    bbox(ax, 0.4, 0.5, 9.2, 8.8, BLUE+"0F", BLUE, lw=2.5, r=0.03, z=1)
    ax.text(0.75, 9.12, "Hospital Clinical Network (Protected Zone)", fontsize=9,
            fontweight="bold", color=BLUE, zorder=5)

    # Internet zone
    bbox(ax, 10.2, 0.5, 5.5, 8.8, RED+"0A", RED, lw=2.0, r=0.03, z=1)
    ax.text(10.5, 9.12, "External Threat Zone", fontsize=9,
            fontweight="bold", color=RED, zorder=5)

    # Medical devices
    devices = [
        (1.5, 7.5, "ECG Monitor\nICU-007",         TEAL),
        (1.5, 5.8, "Infusion Pump\nA12",            TEAL),
        (1.5, 4.1, "Patient\nWearable W42",         TEAL),
        (1.5, 2.4, "SpO2 Sensor\nR03",              TEAL),
        (3.8, 6.8, "Clinical Edge\nGateway",        BLUE),
        (3.8, 4.0, "EHR API\nGateway",             BLUE),
        (3.8, 2.2, "AI Clinical\nAssistant",        PURPLE),
        (6.5, 5.2, "TIPPSS\nSafeGuard-PQ\nAssessment", AMBER),
    ]
    for dx, dy, dtxt, dcol in devices:
        is_assessment = "TIPPSS" in dtxt
        lw_d = 3.0 if is_assessment else 1.8
        bbox(ax, dx-0.9, dy-0.52, 1.8, 1.05,
             dcol+"44" if not is_assessment else dcol+"66",
             dcol, lw=lw_d, r=0.022)
        lbl(ax, dx, dy, dtxt, sz=7.5 if not is_assessment else 8, bold=is_assessment)

    # Arrows: devices to gateway
    for src_x, src_y in [(1.5,7.5),(1.5,5.8),(1.5,4.1),(1.5,2.4)]:
        arr(ax, src_x+0.9, src_y, 2.9, 6.8 if src_y > 4.5 else 4.0, col=MGRAY, lw=1.2, ms=8)

    # TIPPSS assesses everything
    for tgt_x, tgt_y in [(3.8,6.8),(3.8,4.0),(3.8,2.2)]:
        arr(ax, 5.6, 5.2, tgt_x+0.9, tgt_y, col=AMBER, lw=1.8, ms=10,
            conn="arc3,rad=0.2")

    # Internet connection
    arr(ax, 4.7, 6.8, 10.0, 6.8, col=MGRAY, lw=2.0)
    ax.text(7.3, 7.0, "TLS / Clinical Data Flow", fontsize=8,
            color=MGRAY, ha="center", zorder=10)

    # Threats
    threats = [
        (11.8, 7.8, "Harvest-Now\nDecrypt-Later\nAdversary",        RED,    "Captures encrypted PHI today\nDecrypts when quantum arrives"),
        (13.8, 7.8, "Quantum\nComputer\n(2030–2035)",              "#9B59B6","Breaks RSA-2048\nECDSA-P256 via\nShor's algorithm"),
        (11.8, 5.2, "Prompt\nInjection\nAttacker",                  ORANGE, "Targets clinical AI\nassistants via crafted\nprompts"),
        (13.8, 5.2, "ARP Spoof /\nMQTT Attack\nAgent",            RED,    "Medical IoT device\nimpersonation &\nprotocol abuse"),
        (11.8, 2.6, "Secret\nExposure\nThreat",                    ORANGE, "API keys in\ndevice logs\ncredentials"),
        (13.8, 2.6, "DoS / DDoS\nGateway\nDisruption",            RED,    "SYN flood\nTCP DDoS\nService denial"),
    ]
    for tx, ty, ttxt, tcol, tdesc in threats:
        bbox(ax, tx-0.9, ty-0.6, 1.8, 1.2, tcol+"33", tcol, lw=2.0, r=0.022)
        lbl(ax, tx, ty, ttxt, sz=7.5, bold=True, c=WHITE)
        ax.text(tx, ty-0.78, tdesc, ha="center", fontsize=6.5, color=MGRAY,
                va="top", zorder=10, multialignment="center", linespacing=1.4)
        # Attack arrow toward hospital
        arr(ax, tx-0.9, ty, 10.2, ty,
            col=tcol, lw=1.8, ms=11, conn="arc3,rad=0.0")

    # TIPPSS detection coverage bubble
    cov = plt.Circle((6.5, 5.2), 3.8, fill=False, edgecolor=GOLD,
                     linewidth=2.5, linestyle="--", alpha=0.7, zorder=4)
    ax.add_patch(cov)
    ax.text(6.5, 1.22, "TIPPSS SafeGuard-PQ Assessment Coverage", ha="center",
            fontsize=8, color=GOLD, fontweight="bold", zorder=10)

    # TIPPSS pillars legend
    for pi, (pil, pc) in enumerate(zip(
        ["Trust","Identity","Privacy","Protection","Safety","Security"],
        [TEAL, BLUE, PURPLE, NAVY, RED, ORANGE])):
        px2 = 0.7 + pi * 1.5
        bbox(ax, px2, 0.55, 1.3, 0.38, pc+"44", pc, lw=1.0, r=0.01)
        lbl(ax, px2+0.65, 0.74, pil, sz=7)

    return fig_png(fig)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM D — QIRO Optimisation
# ══════════════════════════════════════════════════════════════════════════════
def make_qiro():
    fig, axes = plt.subplots(1, 2, figsize=(18, 11),
                             gridspec_kw={"width_ratios": [1, 1.05]})
    fig.patch.set_facecolor(DARK)
    fig.suptitle("QIRO — Quantum-Inspired Remediation Optimizer  [Novel Contribution]",
                 fontsize=15, fontweight="bold", color=GOLD, y=0.98,
                 fontfamily="monospace")

    # ── Left: Math ────────────────────────────────────────────────────────────
    ax = axes[0]; ax.set_facecolor(DARK)
    ax.set_xlim(0, 10); ax.set_ylim(0, 11); ax.axis("off")
    ax.text(5, 10.7, "Mathematical Formulation", ha="center", fontsize=13,
            fontweight="bold", color=LBLUE)

    sections = [
        ("1.  Decision Variable", BLUE,
         ["$x_i \\in \\{0,1\\}$   for each action $i = 1,\\ldots,n$",
          "$x_i = 1$  → SELECT     $x_i = 0$  → DEFER"],
         10.25, 1.05),
        ("2.  Benefit Score", PURPLE,
         ["$B_i = R_i + P_i + S_i + T_i$",
          "$R_i$ risk · $P_i$ PQ urgency · $S_i$ safety · $T_i$ TIPPSS"],
         8.9, 1.05),
        ("3.  Objective Function", GREEN,
         ["$\\max_x \\sum_{i=1}^{n} B_i\\,x_i$",
          "Subject to: $\\sum C_i x_i \\leq C_{\\max}$ (budget)",
          "and:   $\\sum D_i x_i \\leq D_{\\max}$ (downtime)"],
         7.55, 1.42),
        ("4.  Energy Function  E(x)", AMBER,
         ["$E(x) = -\\sum B_i x_i$",
          "$+\\;\\lambda_C[\\max(0,\\sum C_i x_i - C_{\\max})]^2$",
          "$+\\;\\lambda_D[\\max(0,\\sum D_i x_i - D_{\\max})]^2$",
          "$+\\;\\lambda_K \\sum K_i x_i$   (complexity penalty)",
          "$x^* = \\arg\\min_x\\;E(x)$"],
         5.85, 1.82),
        ("5.  Simulated Annealing", TEAL,
         ["$T_{start}=100$   $\\alpha=0.995$   Iters=1000",
          "Flip $x_j$ → accept if $\\Delta E<0$ or $e^{-\\Delta E/T}$",
          "Cool: $T \\leftarrow T \\cdot \\alpha$ each step"],
         3.75, 1.2),
        ("6.  Output", GREEN,
         ["$\\mathcal{A}_{sel} = \\{i\\mid x_i^*=1\\}$  → Actions now",
          "$\\mathcal{A}_{def} = \\{i\\mid x_i^*=0\\}$  → Deferred",
          "$C_{rem} = C_{\\max} - \\sum C_i x_i^*$",
          "$D_{rem} = D_{\\max} - \\sum D_i x_i^*$"],
         2.2, 1.7),
    ]
    for title, col, lines, top_y, height in sections:
        bbox(ax, 0.2, top_y-height, 9.6, height, col+"1A", col, lw=2.0, r=0.02)
        ax.text(0.45, top_y-0.18, title, fontsize=10, fontweight="bold",
                color=col, zorder=10)
        for li, line in enumerate(lines):
            fc = [GOLD, WHITE, MGRAY, MGRAY, WHITE][min(li, 4)]
            ax.text(5.0, top_y-0.42-li*0.32, line, ha="center", fontsize=10,
                    color=fc, zorder=10, va="center")

    # QUBO note
    bbox(ax, 0.2, 0.08, 9.6, 1.9, PURPLE+"1A", PURPLE, lw=1.8, r=0.02)
    ax.text(5.0, 1.77, "QUBO / Ising Connection", ha="center", fontsize=9.5,
            fontweight="bold", color="#A78BFA", zorder=10)
    ax.text(5.0, 1.3, "Map $x_i\\in\\{0,1\\}$ to spin $s_i=2x_i-1\\in\\{-1,+1\\}$",
            ha="center", fontsize=9, color=WHITE, zorder=10)
    ax.text(5.0, 0.92, "Energy $E(x)$ is equivalent to an Ising Hamiltonian",
            ha="center", fontsize=9, color=MGRAY, zorder=10)
    ax.text(5.0, 0.54, "Same problem class solved by quantum annealers (D-Wave)",
            ha="center", fontsize=9, color=MGRAY, zorder=10)
    ax.text(5.0, 0.2, "QIRO solves on classical CPU — deployable today without quantum hardware",
            ha="center", fontsize=8.5, color="#A78BFA", fontweight="bold", zorder=10)

    # ── Right: Use Case ───────────────────────────────────────────────────────
    ax2 = axes[1]; ax2.set_facecolor(DARK)
    ax2.set_xlim(0, 11); ax2.set_ylim(0, 11); ax2.axis("off")
    ax2.text(5.5, 10.7, "Use Case: ICU Gateway Assessment", ha="center",
             fontsize=13, fontweight="bold", color=ORANGE)

    # Config
    bbox(ax2, 0.2, 9.2, 10.6, 1.35, RED+"22", ORANGE, lw=2.0, r=0.02)
    ax2.text(0.45, 10.32, "System Configuration Detected", fontsize=10,
             fontweight="bold", color=ORANGE, zorder=10)
    cfgs = [("TLS:",ORANGE,"TLS 1.2"),("Key Exchange:",RED,"ECDHE-P256"),
            ("Cert Sig:",RED,"ECDSA-P256"),("Hash:",AMBER,"SHA-256"),
            ("Lifetime:",RED,"15 years"),("Cert Key:",RED,"RSA-2048")]
    for ci, (ck, cc, cv) in enumerate(cfgs):
        cx2 = 0.5 + (ci % 3) * 3.5
        cy2 = 9.95 - (ci // 3) * 0.38
        ax2.text(cx2, cy2, f"{ck} ", fontsize=8, color=MGRAY, va="center", zorder=10)
        ax2.text(cx2+1.2, cy2, cv, fontsize=8, color=cc, fontweight="bold",
                 va="center", zorder=10)

    # Actions table
    bbox(ax2, 0.2, 3.8, 10.6, 5.18, DARKB, MGRAY, lw=1.2, r=0.015)
    ax2.text(0.45, 8.74, "Candidate Remediation Actions  (n = 7)", fontsize=10,
             fontweight="bold", color=WHITE, zorder=10)
    hdrs = ["Action", "Bi", "Cost", "DT", "Status"]
    hxs  = [0.5, 6.2, 7.4, 8.6, 9.6]
    for hx, ht in zip(hxs, hdrs):
        ax2.text(hx, 8.4, ht, fontsize=8.5, fontweight="bold",
                 color=LBLUE, zorder=10)
    ax2.plot([0.3, 10.7], [8.18, 8.18], color=MGRAY, lw=0.8, zorder=5)

    rows = [
        ("Prompt Injection Firewall",   75, "$8K",  "1h",  True,  "CRITICAL"),
        ("Device Re-Authentication",    75, "$10K", "2h",  True,  "CRITICAL"),
        ("PQ Certificate Migration",    85, "$20K", "4h",  True,  "HIGH"),
        ("TLS 1.3 Upgrade",            90, "$35K", "8h",  False, "HIGH"),
        ("PHI Redaction Middleware",    70, "$8K",  "2h",  True,  "HIGH"),
        ("Full ML-KEM Migration",       95, "$45K", "10h", False, "CRITICAL"),
        ("Firmware Update",            65, "$12K", "6h",  False, "MEDIUM"),
    ]
    for ri, (rname, bi, rcost, rdt, sel, rsev) in enumerate(rows):
        ry = 7.75 - ri * 0.55
        rbg = GREEN+"1A" if sel else DARKB
        rbc = LGREEN if sel else MGRAY
        bbox(ax2, 0.25, ry-0.22, 10.4, 0.46, rbg, rbc, lw=1.0, r=0.01)
        marker = "SEL" if sel else "DEF"
        mc     = LGREEN if sel else AMBER
        ax2.text(0.38, ry, marker, fontsize=7, color=mc, fontweight="bold",
                 va="center", zorder=10)
        ax2.text(0.7, ry, rname[:28], fontsize=8,
                 color=WHITE if sel else MGRAY, va="center", zorder=10)
        for vx, vv in zip([6.2, 7.4, 8.6], [str(bi), rcost, rdt]):
            ax2.text(vx, ry, vv, fontsize=8, ha="center", va="center",
                     color=GOLD if sel else MGRAY, zorder=10)
        sc = RED if rsev=="CRITICAL" else (ORANGE if rsev=="HIGH" else AMBER)
        bbox(ax2, 9.3, ry-0.17, 1.3, 0.35, sc+"33", sc, lw=1.0, r=0.01)
        ax2.text(9.95, ry, rsev[:4], fontsize=7, ha="center", va="center",
                 color=WHITE, zorder=10)

    ax2.plot([0.3, 10.7], [3.97, 3.97], color=MGRAY, lw=0.8, zorder=5)
    ax2.text(0.45, 3.73,
             "Selected: 4 actions  |  Budget: $46K / $100K  |  Downtime: 9h / 40h  |  Deferred: 3",
             fontsize=8.5, color=LGREEN, fontweight="bold", zorder=10)

    # Phased roadmap
    bbox(ax2, 0.2, 0.1, 10.6, 3.35, NAVY+"22", BLUE, lw=1.8, r=0.02)
    ax2.text(5.5, 3.26, "Phased Migration Roadmap", ha="center", fontsize=10,
             fontweight="bold", color=LBLUE, zorder=10)

    phases = [
        ("Phase 1\n0–6 months",    RED,    ["Prompt Injection Firewall","Device Re-Auth"],      "$18K · 3h"),
        ("Phase 2\n6–18 months",   AMBER,  ["PQ Certificate Migration","PHI Redaction"],        "$28K · 6h"),
        ("Phase 3\n18–36 months",  LGREEN, ["TLS 1.3 Upgrade (budget permitting)","ML-KEM"],    "Deferred"),
    ]
    for pi, (ptitle, pcol, pitems, pcost) in enumerate(phases):
        px3 = 0.4 + pi * 3.6
        bbox(ax2, px3, 0.22, 3.2, 2.85, pcol+"1A", pcol, lw=2.0, r=0.022)
        bbox(ax2, px3, 2.75, 3.2, 0.38, pcol+"55", pcol, lw=1.3, r=0.01)
        ax2.text(px3+1.6, 2.94, ptitle, ha="center", fontsize=8.5,
                 fontweight="bold", color=WHITE, zorder=10)
        for ii, item in enumerate(pitems):
            iy = 2.4 - ii * 0.42
            bbox(ax2, px3+0.1, iy-0.16, 2.9, 0.33, pcol+"22", pcol, lw=0.8, r=0.01)
            ax2.text(px3+0.22, iy, f"• {item}", fontsize=7.5,
                     color=WHITE, va="center", zorder=10)
        ax2.text(px3+1.6, 0.44, pcost, ha="center", fontsize=8.5,
                 fontweight="bold", color=pcol, zorder=10)

    plt.tight_layout(rect=[0, 0, 1, 0.96], w_pad=0.5)
    return fig_png(fig, dpi=DPI)


# ══════════════════════════════════════════════════════════════════════════════
# PDF BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def on_page(canvas_obj, doc):
    """Header + footer on every page."""
    canvas_obj.saveState()
    # top bar
    canvas_obj.setFillColor(RL_NAVY)
    canvas_obj.rect(0, PH - 28, PW, 28, fill=1, stroke=0)
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.setFillColor(RL_WHITE)
    canvas_obj.drawString(18, PH - 18, "TIPPSS SafeGuard-PQ  —  Technical Report")
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawRightString(PW - 18, PH - 18,
        "NIST FIPS 203/204/205  ·  IEEE 2933-2024 TIPPSS")
    # bottom bar
    canvas_obj.setFillColor(RL_NAVY)
    canvas_obj.rect(0, 0, PW, 22, fill=1, stroke=0)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(RL_WHITE)
    canvas_obj.drawString(18, 7,
        "github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS")
    canvas_obj.drawRightString(PW - 18, 7, f"Page {doc.page}")
    canvas_obj.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        topMargin=36, bottomMargin=30,
        leftMargin=36, rightMargin=36,
    )

    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

    S_TITLE   = sty("T", fontSize=22, textColor=RL_NAVY, fontName="Helvetica-Bold",
                    alignment=TA_CENTER, spaceAfter=6)
    S_SUB     = sty("S", fontSize=11, textColor=colors.HexColor(BLUE),
                    fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)
    S_H1      = sty("H1", fontSize=14, textColor=RL_NAVY, fontName="Helvetica-Bold",
                    spaceBefore=14, spaceAfter=6)
    S_H2      = sty("H2", fontSize=11, textColor=colors.HexColor(BLUE),
                    fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    S_BODY    = sty("B", fontSize=9.5, fontName="Helvetica", leading=14,
                    alignment=TA_JUSTIFY, spaceAfter=6)
    S_BULLET  = sty("BL", fontSize=9.5, fontName="Helvetica", leading=13,
                    leftIndent=14, bulletIndent=4, spaceAfter=3)
    S_CAPTION = sty("C", fontSize=8.5, fontName="Helvetica-Oblique",
                    alignment=TA_CENTER, textColor=colors.gray, spaceAfter=6)
    S_META    = sty("M", fontSize=9, fontName="Helvetica",
                    alignment=TA_CENTER, textColor=colors.gray, spaceAfter=4)

    W = PW - 96   # usable width (safe margin)

    def hr():
        return HRFlowable(width="100%", thickness=1.2,
                          color=RL_BLUE, spaceAfter=8, spaceBefore=6)

    def h1(t): return Paragraph(t, S_H1)
    def h2(t): return Paragraph(t, S_H2)
    def body(t): return Paragraph(t, S_BODY)
    def bullet(t): return Paragraph(f"&bull;&nbsp; {t}", S_BULLET)
    def sp(n=8): return Spacer(1, n)
    def caption(t): return Paragraph(t, S_CAPTION)

    def diag_img(path_tuple, cap):
        img = rl_img(path_tuple, target_w_pt=W)
        return [PageBreak(), img, caption(cap)]

    story = []

    # ── COVER ─────────────────────────────────────────────────────────────────
    story += [
        sp(60),
        Paragraph("TIPPSS SafeGuard-PQ", S_TITLE),
        Paragraph("Consolidated Technical Report", sty("ST", fontSize=16,
            textColor=colors.HexColor(BLUE), fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=8)),
        sp(6),
        Paragraph(
            "Agentic Post-Quantum Cybersecurity Assessment &amp; Migration Planning<br/>"
            "for Clinical Edge IoT and AI Healthcare Systems",
            sty("ST2", fontSize=12, fontName="Helvetica", alignment=TA_CENTER,
                textColor=colors.gray, spaceAfter=16)),
        hr(),
        sp(8),
    ]
    # Cover metadata table
    meta = [
        ["Author:",        "Pavan Gemmanjunath"],
        ["Contact:",       "pavan5119m@gmail.com"],
        ["Repository:",    "github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS"],
        ["Standards:",     "NIST FIPS 203 / 204 / 205  ·  IEEE 2933-2024 TIPPSS"],
        ["Frameworks:",    "HIPAA  ·  OWASP LLM Top-10  ·  Kirkpatrick SA 1983"],
        ["Novel Element:", "QIRO — Quantum-Inspired Remediation Optimizer"],
    ]
    tbl_style = TableStyle([
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",   (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9.5),
        ("TEXTCOLOR",  (0,0), (0,-1),  RL_NAVY),
        ("TEXTCOLOR",  (1,0), (1,-1),  colors.black),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
        ("GRID",       (0,0), (-1,-1), 0.4, colors.HexColor(MGRAY)),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ])
    story.append(Table([[k, v] for k, v in meta],
                        colWidths=[3.5*cm, W - 3.5*cm],
                        style=tbl_style))
    story += [sp(20), PageBreak()]

    # ── SECTION 1: PROBLEM STATEMENT ─────────────────────────────────────────
    story += [h1("1.  Problem Statement"), hr()]
    story.append(body(
        "Healthcare organisations operate clinical Internet of Things (IoT) networks comprising "
        "infusion pumps, ECG monitors, patient wearables, edge gateways, and AI-assisted EHR "
        "systems. All of these systems transmit and store sensitive patient data using classical "
        "public-key cryptography — RSA-2048, ECDSA-P256, ECDH — that will be rendered mathematically "
        "insecure by Shor's algorithm running on a cryptographically relevant quantum computer, "
        "with expert consensus placing the threat window at 2030–2035."
    ))
    story.append(h2("1.1  The Harvest-Now, Decrypt-Later (HNDL) Threat"))
    story.append(body(
        "Adversaries are already capturing encrypted clinical network traffic today with the "
        "explicit intent of decrypting it when quantum hardware matures. Since healthcare data "
        "must remain confidential for 15–50 years under HIPAA and GDPR, records currently "
        "protected by RSA or ECDSA are already exposed — the harvest window has begun."
    ))
    story.append(h2("1.2  Six Identified Security Gaps"))
    for g in [
        "Quantum-vulnerable cryptography: RSA, ECDSA, ECDH, deprecated TLS across clinical infrastructure — no automated PQ readiness inventory exists.",
        "PHI leakage in AI systems: Patient names, MRNs, diagnoses, and email addresses appearing in clinical AI prompt logs — invisible to classical scanners.",
        "Prompt injection against clinical AI: OWASP LLM Top-10 attack patterns (instruction override, data exfiltration) targeting clinical AI assistants.",
        "Exposed credentials in device telemetry: API keys, AWS access keys, and bearer tokens embedded in medical device debug logs.",
        "Weak medical IoT device identity: Missing certificates, failed authentication, repeated login failures undermining Trust and Identity pillars.",
        "No post-quantum migration path: No existing tool maps findings to NIST FIPS 203/204/205 and produces a budget-constrained, downtime-aware roadmap.",
    ]:
        story.append(bullet(g))

    story.append(h2("1.3  Quantified Risk Exposure"))
    risk_data = [
        ["Metric", "Value", "Source"],
        ["Average healthcare breach cost", "$9.77 million", "IBM Cost of a Data Breach 2024"],
        ["Healthcare breaches (2023)", "725+ incidents / 133M+ records", "HHS Office for Civil Rights"],
        ["Quantum threat timeline", "2030–2035", "NIST IR 8547 / NSA CNSA 2.0"],
        ["Federal PQC migration deadline", "2035 (RSA/ECC deprecated after 2030)", "NIST IR 8547"],
        ["Healthcare data retention", "15–50 years", "HIPAA / national regulations"],
    ]
    risk_tbl_style = TableStyle([
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("BACKGROUND",  (0,0), (-1,0),  RL_NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0),  RL_WHITE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#EBF3FB"), colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor(MGRAY)),
        ("LEFTPADDING",  (0,0),(-1,-1), 7),
        ("RIGHTPADDING", (0,0),(-1,-1), 7),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ])
    story.append(Table(risk_data, colWidths=[6*cm, 5.5*cm, W-11.5*cm],
                        style=risk_tbl_style))
    story += [sp(10), PageBreak()]

    # ── SECTION 2: SOLUTION ──────────────────────────────────────────────────
    story += [h1("2.  Solution Overview"), hr()]
    story.append(body(
        "TIPPSS SafeGuard-PQ is a sequential agentic cybersecurity assessment and migration "
        "planning platform. It evaluates clinical IoT systems and AI healthcare applications "
        "against NIST FIPS 203/204/205 post-quantum standards and the IEEE 2933-2024 TIPPSS "
        "framework through a nine-agent sequential pipeline, then produces a constraint-aware "
        "remediation roadmap using the novel Quantum-Inspired Remediation Optimizer (QIRO)."
    ))
    story.append(h2("2.1  Nine-Agent Assessment Pipeline"))
    agent_data = [
        ["Agent", "Function", "TIPPSS Pillar", "Standards"],
        ["1 — Input Validator", "Schema validation · field normalisation", "All", "—"],
        ["2 — Crypto Classifier", "Classify TLS: PQ-safe / classical / deprecated", "Protection, Security", "FIPS 203/204/205"],
        ["3 — PQ Benchmark", "NIST compliance · HNDL rule (lifetime ≥ 10yr)", "Protection, Privacy", "FIPS 203/204/205"],
        ["4 — IoT Device Identity", "Certificate · auth status · failed logins", "Trust, Identity, Safety", "IEEE 2933-2024 §6.2"],
        ["5 — AI Prompt Privacy", "PHI detection · prompt injection scanning", "Privacy, Security", "IEEE 2933-2024 §6.3 · HIPAA"],
        ["6 — Secret Exposure", "API keys · AWS · GitHub tokens in device logs", "Protection, Security", "OWASP"],
        ["7 — Safety Risk", "Autonomous dosing · alarm overrides", "Safety, Trust", "IEEE 2933-2024 §6.5"],
        ["8 — TIPPSS Scorer", "Six-pillar scoring · composite risk verdict", "All six pillars", "IEEE 2933-2024 §6.1–6.6"],
        ["9 — QIRO Optimizer", "QUBO binary optimisation · migration roadmap", "All pillars", "Kirkpatrick 1983"],
    ]
    ag_style = TableStyle([
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("BACKGROUND",  (0,0), (-1,0),  RL_NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0),  RL_WHITE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#F0F4FA"), colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor(MGRAY)),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("BACKGROUND", (0,8), (-1,8), colors.HexColor(AMBER+"33")),
        ("FONTNAME",   (0,8), (-1,8), "Helvetica-Bold"),
    ])
    story.append(Table(agent_data,
                        colWidths=[3.5*cm, 5.5*cm, 3.5*cm, W-12.5*cm],
                        style=ag_style))

    story.append(h2("2.2  Novel Contribution — QIRO"))
    story.append(body(
        "QIRO (Quantum-Inspired Remediation Optimizer) converts every detected finding into a "
        "candidate remediation action and frames the selection problem as a Quadratic Unconstrained "
        "Binary Optimisation (QUBO) — the same problem class solved by quantum annealers. It then "
        "solves this on a classical CPU using Simulated Annealing (Kirkpatrick, Gelatt, Vecchi, 1983), "
        "selecting the maximum-benefit feasible portfolio under the hospital's budget and downtime "
        "constraints. No existing post-quantum migration tool applies this formulation."
    ))
    story += [sp(8), PageBreak()]

    # ── SECTION 3: ARCHITECTURE DIAGRAM ─────────────────────────────────────
    story += [h1("3.  System Architecture Diagram"), hr()]
    story.append(body(
        "The platform implements a three-tier architecture. Tier 1 (Streamlit, port 8501) handles "
        "scenario selection, file upload, feature extraction, and result visualisation. "
        "Tier 2 (Sequential Agentic Framework, port 5678) orchestrates the nine-agent pipeline. "
        "Tier 3 persists timestamped results as JSON and CSV."
    ))
    story += diag_img(make_architecture(), "Figure 1: Three-tier system architecture — Presentation, Orchestration, and Output layers.")
    story += [sp(4)]

    # ── SECTION 4: DATA FLOW ─────────────────────────────────────────────────
    story += [PageBreak(), h1("4.  End-to-End Data Flow"), hr()]
    story.append(body(
        "Data enters as a JSON payload (from pre-built scenarios or uploaded files), "
        "passes sequentially through nine agents, and exits as a verdict, six-pillar TIPPSS "
        "score, risk gauge, and QIRO migration roadmap. The gold HTTP POST arrow represents "
        "the single webhook call from the dashboard to the agentic framework."
    ))
    story += diag_img(make_dataflow(), "Figure 2: Swimlane data flow from input sources through all agents to output components.")
    story += [sp(4)]

    # ── SECTION 5: NETWORK TOPOLOGY ─────────────────────────────────────────
    story += [PageBreak(), h1("5.  Network Topology & Threat Model"), hr()]
    story.append(body(
        "The threat model maps six attack classes — HNDL adversary, quantum computation, "
        "prompt injection, ARP spoofing / MQTT malformation, secret exposure, and DoS/DDoS — "
        "against the hospital clinical network perimeter. TIPPSS SafeGuard-PQ is positioned "
        "as the assessment layer covering all six TIPPSS pillars across the clinical IoT estate."
    ))
    story += diag_img(make_network_topology(), "Figure 3: Clinical network topology with threat actors, attack vectors, and TIPPSS assessment coverage.")
    story += [sp(4)]

    # ── SECTION 6: QIRO ──────────────────────────────────────────────────────
    story += [PageBreak(), h1("6.  QIRO Optimisation Diagram"), hr()]
    story.append(body(
        "Left panel: full mathematical formulation of QIRO — decision variable, benefit score "
        "Bi = Ri + Pi + Si + Ti, objective function, penalty-based energy function E(x), "
        "Simulated Annealing algorithm, and QUBO/Ising connection. "
        "Right panel: ICU gateway use case showing seven candidate actions with benefit scores, "
        "budget tracking, phased migration roadmap, and selected/deferred action split."
    ))
    story += diag_img(make_qiro(), "Figure 4: QIRO mathematical formulation (left) and ICU gateway use case walkthrough (right).")
    story += [sp(4)]

    # ── SECTION 7: TEST RESULTS ──────────────────────────────────────────────
    story += [h1("7.  Test Results & Empirical Validation"), hr()]
    story.append(body(
        "All 8/8 file upload tests passed against the live sequential agentic pipeline. "
        "Default constraints: budget $100,000, downtime 40 hours. The benign baseline "
        "correctly returns a Safe verdict (score 0, zero findings), confirming correct "
        "discrimination from attack traffic."
    ))
    test_data = [
        ["File", "Attack Type", "Verdict", "Score", "Findings", "QIRO Selected", "QIRO Deferred"],
        ["ARP_Spoofing_test.pcap.csv", "ARP Spoofing", "Not PQ Safe", "61/100", "7", "4", "3"],
        ["Benign_test.pcap.csv", "Baseline", "Safe", "0/100", "0", "0", "0"],
        ["MQTT-Malformed_Data.pcap.csv", "MQTT Malformed", "Not PQ Safe", "61/100", "7", "4", "3"],
        ["Recon-Port_Scan.pcap.csv", "Port Scan", "Not PQ Safe", "61/100", "7", "4", "3"],
        ["TCP_IP-DoS-SYN.pcap.csv", "SYN DoS", "Not PQ Safe", "61/100", "7", "4", "3"],
        ["TCP_IP-DDoS-TCP.pcap.csv", "TCP DDoS", "Not PQ Safe", "61/100", "7", "4", "3"],
        ["patients.csv (Synthea)", "PHI Simulation", "Safe (TLS)", "0/100", "8 PHI", "8", "0"],
        ["conditions.csv (Synthea)", "Clinical Conds.", "Safe", "0/100", "0", "0", "0"],
    ]
    tr_style = TableStyle([
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("BACKGROUND",  (0,0), (-1,0),  RL_NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0),  RL_WHITE),
        ("BACKGROUND",  (0,2), (-1,2),  colors.HexColor("#E2F5E8")),  # benign green
        ("BACKGROUND",  (0,7), (-1,7),  colors.HexColor("#F0E8FA")),  # PHI purple
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#FAFAFA"), colors.white]),
        ("BACKGROUND",  (0,2), (-1,2),  colors.HexColor("#DFFBE9")),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor(MGRAY)),
        ("LEFTPADDING",  (0,0),(-1,-1), 5),
        ("RIGHTPADDING", (0,0),(-1,-1), 5),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("ALIGN", (2,0), (-1,-1), "CENTER"),
    ])
    story.append(Table(test_data,
                        colWidths=[4.8*cm, 2.8*cm, 2.4*cm, 1.5*cm, 1.8*cm, 2.2*cm, W-15.5*cm],
                        style=tr_style))
    story += [sp(10), PageBreak()]

    # ── SECTION 8: STANDARDS ─────────────────────────────────────────────────
    story += [h1("8.  Standards Compliance Matrix"), hr()]
    std_data = [
        ["Component", "Standard", "Clause / Reference", "Status"],
        ["Agent 3 PQ Benchmark", "NIST FIPS 203", "ML-KEM key encapsulation", "Implemented"],
        ["Agent 3 PQ Benchmark", "NIST FIPS 204", "ML-DSA digital signatures", "Implemented"],
        ["Agent 3 PQ Benchmark", "NIST FIPS 205", "SLH-DSA hash-based signatures", "Implemented"],
        ["Agent 4 IoT Identity", "IEEE 2933-2024", "Clause 6.2 — Trust and Identity", "Implemented"],
        ["Agent 5 AI Privacy",   "IEEE 2933-2024", "Clause 6.3 — Privacy", "Implemented"],
        ["Agent 5 PHI Detection","HIPAA 45 CFR §164.514", "Minimum necessary — AI inputs", "Implemented"],
        ["Agent 7 Safety Risk",  "IEEE 2933-2024", "Clause 6.5 — Safety", "Implemented"],
        ["Agent 8 TIPPSS Scorer","IEEE 2933-2024", "Clauses 6.1–6.6 — All six pillars", "Implemented"],
        ["QIRO Algorithm",       "Kirkpatrick et al. 1983", "Simulated Annealing (Science 220)", "Implemented"],
        ["QIRO Formulation",     "QUBO / Ising model", "Binary quadratic optimisation", "Novel"],
    ]
    sd_style = TableStyle([
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("BACKGROUND",  (0,0), (-1,0),  RL_NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0),  RL_WHITE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#F0F4FA"), colors.white]),
        ("BACKGROUND",  (0,-1),(-1,-1), colors.HexColor(AMBER+"33")),
        ("FONTNAME",    (0,-1),(-1,-1), "Helvetica-Bold"),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor(MGRAY)),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("ALIGN", (3,0), (3,-1), "CENTER"),
    ])
    story.append(Table(std_data,
                        colWidths=[4.2*cm, 3.8*cm, 5.5*cm, W-13.5*cm],
                        style=sd_style))
    story += [sp(14)]
    story.append(Paragraph(
        "This document was prepared for technical evaluation of the TIPPSS SafeGuard-PQ system. "
        "All datasets are publicly available research data (CICIoMT2024 — University of New Brunswick; "
        "Synthea — MITRE Corporation, Apache 2.0). No real patient data was used.",
        sty("Note", fontSize=8.5, fontName="Helvetica-Oblique",
            textColor=colors.gray, alignment=TA_CENTER)))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    kb = PDF_PATH.stat().st_size // 1024
    print(f"  {PDF_PATH.name}  ({kb} KB,  {doc.page} pages)")


if __name__ == "__main__":
    import os
    print("\nGenerating consolidated PDF technical report ...\n")
    build_pdf()
    for f in _tmp_files:
        try: os.remove(f)
        except: pass
    print(f"\nSaved: {PDF_PATH}")
