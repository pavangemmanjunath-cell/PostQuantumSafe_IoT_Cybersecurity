"""Build the Word version of the Release 3 reviewer-evidence pack with pandoc.

    python scripts/build_release3_docx.py

Concatenates docs/release-3/README.md with its companion documents, embeds the figures (PNG renders) with
numbered captions and writes docs/release-3/SafeGuard-PQ_Release3_Reviewer_Evidence.docx. Requires pandoc.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT / "docs" / "release-3"
FIG = R3 / "figures"
OUT = R3 / "SafeGuard-PQ_Release3_Reviewer_Evidence.docx"

FIGURES = [
    ("fig1_evaluation_design.png", "Figure 1. Evaluation design of SafeGuard-PQ Release 3: inputs, the five-stage agent "
     "pipeline, experiments E1–E12, data sources and the claim boundary.", "6.5in"),
    ("fig2_threat_model.png", "Figure 2. Threat model: adversaries A1–A6, simulated attacks, observable preconditions, "
     "detecting agents and catalogue mitigations; panel (e) is the measurement loop of experiment E11.", "6.5in"),
    ("fig_e3_optimizer_small_n.png", "Figure 3. E3: share of 500 synthetic instances (n ≤ 14) solved to the exhaustive "
     "optimum and the gap distribution for annealing alone and annealing with local search.", "6.5in"),
    ("fig_e8_scalability.png", "Figure 4. E8: optimal share, mean and maximum gap to the HiGHS integer-programming optimum, "
     "and runtime per instance for n = 20–200 (50 instances per size, τ ∈ {0.25, 0.5, 0.75}).", "6.5in"),
    ("fig_e7_sensitivity.png", "Figure 5. E7: (a) maximum |ΔS| and share of systems whose verdict or status changes per "
     "perturbation of the scoring constants; (b) PQ risk score versus the lifetime threshold L per scenario.", "6.5in"),
    ("fig_e9_reassessment.png", "Figure 6. E9: baseline, projected and reassessed PQ risk score per system for the "
     "independent-action planner (plan A) and the shared-root-cause planner (plan B); labels give the status after plan A.",
     "6.5in"),
    ("fig_e6_traffic_same_split.png", "Figure 7. E6: window-level flag rate per CICIoMT2024 test file with Wilson 95 % "
     "intervals; thresholds were selected on this same split (optimistic).", "6.5in"),
    ("fig_e10_traffic_holdout.png", "Figure 8. E10: held-out precision, recall and F1 (bootstrap 95 % intervals) for the "
     "rules with shipped and development-tuned thresholds and for three baselines under three protocols.", "6.5in"),
    ("fig_e11_attack_simulation.png", "Figure 9. E11: (a) outcome per simulated attack over devices and seeds; (b) fleet "
     "trajectory of the ICU Q-Day drill.", "6.5in"),
]

APPENDICES = [
    ("Appendix A. Threat model", "threat_model.md"),
    ("Appendix B. Formulas, constants and instance generators", "formulas.md"),
    ("Appendix C. Clinical deployment feasibility", "deployment_feasibility.md"),
    ("Appendix D. Standards traceability table", "standards_mapping.md"),
]


def strip_links(md: str) -> str:
    """Relative Markdown links point at repository files; in the Word file keep the link text only."""
    return re.sub(r"\[([^\]]+)\]\((?!https?://)[^)]+\)", r"\1", md)


def demote(md: str, levels: int = 1) -> str:
    return re.sub(r"^(#+)", lambda m: "#" * (len(m.group(1)) + levels), md, flags=re.M)


def main() -> int:
    body = strip_links((R3 / "README.md").read_text(encoding="utf-8"))
    body = re.sub(r"^# .*\n", "", body, count=1)  # title comes from the metadata block
    parts = [
        "---",
        'title: "SafeGuard-PQ Release 3 (v0.3.0): Evidence for the Revised Manuscript"',
        'subtitle: "Supplementary material and reviewer responses"',
        f'date: "{date.today().isoformat()}"',
        "---",
        "",
        body,
        "",
        "# Figures",
        "",
    ]
    for name, caption, width in FIGURES:
        png = FIG / name
        if not png.exists():
            print(f"warning: {png.name} missing; run benchmarks/make_figures.py and scripts/svg_to_pdf.cjs", file=sys.stderr)
            continue
        parts += [f"![{caption}]({png.as_posix()}){{width={width}}}", ""]
    for title, fname in APPENDICES:
        text = strip_links((R3 / fname).read_text(encoding="utf-8"))
        text = re.sub(r"^# .*\n", "", text, count=1)
        parts += [f"# {title}", "", demote(text), ""]
    src = R3 / "_combined_for_docx.md"
    src.write_text("\n".join(parts), encoding="utf-8")
    cmd = ["pandoc", str(src), "-o", str(OUT), "--from", "markdown", "--resource-path", str(FIG)]
    subprocess.run(cmd, check=True)
    src.unlink()
    print(f"Written: {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
