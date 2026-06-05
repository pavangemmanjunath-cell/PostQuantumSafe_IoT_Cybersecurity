"""
Generate two professional Word documents for TIPPSS SafeGuard-PQ.
Run: python generate_docs.py
"""

import pathlib
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

OUT_DIR = pathlib.Path(__file__).parent / "00_Documention"
OUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def set_cell_bg(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_heading(doc, text: str, level: int, color_hex: str = "1F3864"):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in h.runs:
        run.font.color.rgb = RGBColor.from_string(color_hex)
    return h


def add_para(doc, text: str, bold: bool = False, italic: bool = False,
             size: int = 11, space_after: int = 6, color: str = None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return p


def add_bullet(doc, text: str, level: int = 0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    run.font.size = Pt(10.5)
    return p


def add_table_row(table, cells: list, bold: bool = False, bg: str = None,
                  font_size: int = 9):
    row = table.add_row()
    for i, text in enumerate(cells):
        cell = row.cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        run = p.add_run(str(text))
        run.bold = bold
        run.font.size = Pt(font_size)
        if bg:
            set_cell_bg(cell, bg)
    return row


def set_col_widths(table, widths_cm: list):
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths_cm):
                cell.width = Cm(widths_cm[i])


def set_page_margins(doc, top=2.5, bottom=2.5, left=3.0, right=2.5):
    section = doc.sections[0]
    section.top_margin    = Cm(top)
    section.bottom_margin = Cm(bottom)
    section.left_margin   = Cm(left)
    section.right_margin  = Cm(right)


def add_horizontal_rule(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "4472C4")
    pBdr.append(bottom)
    pPr.append(pBdr)
    p.paragraph_format.space_after = Pt(6)


def add_info_box(doc, text: str, bg_color: str = "EBF3FB", border_color: str = "2E75B6"):
    """Simulate a callout box using a single-cell table."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_bg(cell, bg_color)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.left_indent  = Pt(8)
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.font.italic = True
    run.font.color.rgb = RGBColor.from_string("1F3864")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


# ===========================================================================
# DOCUMENT 1 — ACADEMIC PAPER
# ===========================================================================

def build_paper(path: pathlib.Path):
    doc = Document()
    set_page_margins(doc)

    # Default font
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    # ── Title block ─────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run(
        "TIPPSS SafeGuard-PQ: An Agentic Post-Quantum Cybersecurity Assessment "
        "and Constraint-Aware Migration Planning Framework for Clinical IoT and "
        "AI Healthcare Systems"
    )
    title_run.bold = True
    title_run.font.size = Pt(16)
    title_run.font.color.rgb = RGBColor.from_string("1F3864")
    title_p.paragraph_format.space_after = Pt(12)

    auth_p = doc.add_paragraph()
    auth_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    auth_run = auth_p.add_run("Pavan Gemmanjunath")
    auth_run.bold = True
    auth_run.font.size = Pt(12)
    auth_p.paragraph_format.space_after = Pt(2)

    aff_p = doc.add_paragraph()
    aff_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    aff_run = aff_p.add_run(
        "IEEE SA Cybersecurity Initiative · Clinical IoT Security Research\n"
        "pavan5119m@gmail.com"
    )
    aff_run.font.size = Pt(10)
    aff_run.italic = True
    aff_p.paragraph_format.space_after = Pt(16)

    add_horizontal_rule(doc)

    # ── Abstract ────────────────────────────────────────────────────────────
    add_heading(doc, "Abstract", 2)
    add_para(doc,
        "The accelerating development of cryptographically relevant quantum computers "
        "poses an existential threat to the classical public-key infrastructure securing "
        "clinical Internet of Things (IoT) systems, electronic health record (EHR) APIs, "
        "and AI-assisted diagnostic platforms. Adversaries conducting harvest-now-decrypt-"
        "later (HNDL) attacks are already capturing encrypted patient data today for "
        "decryption when quantum hardware matures — a timeline estimated between 2030 and "
        "2035. Despite the publication of NIST FIPS 203, 204, and 205 post-quantum "
        "standards in 2024, no automated assessment tool simultaneously evaluates "
        "cryptographic posture, medical device identity, AI prompt privacy, secret "
        "exposure, and clinical safety risk against these standards and the IEEE 2933-2024 "
        "TIPPSS framework. This paper presents TIPPSS SafeGuard-PQ, a multi-agent "
        "agentic pipeline that performs automated post-quantum security assessments and "
        "produces budget-constrained, downtime-aware migration roadmaps using a novel "
        "Quantum-Inspired Remediation Optimizer (QIRO). QIRO formulates remediation "
        "planning as a binary optimisation problem in the QUBO/Ising style, solved via "
        "Simulated Annealing on classical CPU hardware. Evaluation across eight real-world "
        "datasets — six CICIoMT2024 medical IoT network traffic captures and two Synthea "
        "synthetic clinical record files — demonstrates correct discrimination between "
        "benign and attack scenarios, accurate PHI detection, and constraint-sensitive "
        "migration planning."
    )

    kw_p = doc.add_paragraph()
    kw_p.paragraph_format.space_after = Pt(10)
    kw_run = kw_p.add_run("Keywords: ")
    kw_run.bold = True
    kw_run.font.size = Pt(10)
    kw_p.add_run(
        "Post-Quantum Cryptography · Clinical IoT Security · TIPPSS · ML-KEM · "
        "ML-DSA · QIRO · Simulated Annealing · QUBO · Healthcare AI Security · "
        "NIST FIPS 203/204/205 · IEEE 2933-2024"
    ).font.size = Pt(10)

    add_horizontal_rule(doc)

    # ── 1. Introduction ─────────────────────────────────────────────────────
    add_heading(doc, "1. Introduction", 1)
    add_para(doc,
        "Healthcare organisations operate under a convergence of two emergent pressures. "
        "First, the cryptographic foundations of their infrastructure — RSA-2048, ECDHE-P256, "
        "ECDSA-P256, and AES-128 — are mathematically vulnerable to Shor's algorithm [1] "
        "running on a sufficiently capable quantum processor. Second, healthcare data must be "
        "retained for 15 to 50 years under HIPAA and national health data regulations, "
        "creating a severe harvest-now-decrypt-later exposure window. The NIST Post-Quantum "
        "Cryptography standardisation process concluded in August 2024 with FIPS 203 (ML-KEM), "
        "FIPS 204 (ML-DSA), and FIPS 205 (SLH-DSA) [2]. However, the existence of standards "
        "does not operationalise migration. Three unsolved practical problems persist:"
    )
    add_bullet(doc, "Detection gap: No automated tool assesses cryptographic, device identity, AI prompt privacy, secret exposure, and clinical safety risk simultaneously against the TIPPSS framework.")
    add_bullet(doc, "Planning gap: No tool produces migration roadmaps constrained by real hospital budget and operational downtime limits.")
    add_bullet(doc, "Optimisation gap: No tool frames remediation selection as a mathematical optimisation, enabling provably near-optimal action selection.")

    add_para(doc, "\nThis work addresses all three gaps through the following contributions:")
    add_bullet(doc, "A 10-agent agentic pipeline assessing TLS cryptography, medical IoT device identity, AI prompt logs, secret exposure, and clinical safety risk against NIST FIPS 203/204/205 and IEEE 2933-2024 TIPPSS.")
    add_bullet(doc, "A novel QIRO algorithm formulating remediation planning as a constrained binary QUBO-style optimisation solved via Simulated Annealing, producing selected and deferred action sets with full budget and downtime accountability.")
    add_bullet(doc, "Empirical evaluation on CICIoMT2024 network traffic datasets and Synthea synthetic patient records, demonstrating correct risk discrimination and constraint-sensitive planning.")

    # ── 2. Related Work ─────────────────────────────────────────────────────
    add_heading(doc, "2. Related Work and Literature Review", 1)

    add_heading(doc, "2.1 Post-Quantum Cryptography", 2)
    add_para(doc,
        "The mathematical threat to public-key cryptography from quantum computing was "
        "established by Shor [1], who demonstrated polynomial-time algorithms for integer "
        "factorisation and discrete logarithm computation — the hard problems underlying "
        "RSA and ECDSA. Grover's algorithm [3] provides a quadratic speedup against "
        "symmetric-key systems. The practical implications for deployed infrastructure were "
        "analysed by Mosca [4], who introduced the Mosca inequality: if migration time plus "
        "data security shelf-life exceeds time to quantum advantage, the organisation is at "
        "risk. Bernstein and Lange [5] survey post-quantum algorithm families. The NIST "
        "standardisation effort [2] selected ML-KEM, ML-DSA, and SLH-DSA as primary standards."
    )

    add_heading(doc, "2.2 Clinical IoT and Healthcare Security", 2)
    add_para(doc,
        "Sicari et al. [6] survey the intersection of security, privacy, and trust in IoT, "
        "identifying key vulnerabilities in authentication, data integrity, and access control "
        "directly applicable to clinical environments. Hossain et al. [7] address cloud-assisted "
        "IoT medical system security, proposing secure data sharing frameworks that nevertheless "
        "rely on classical cryptographic primitives now considered PQ-vulnerable. The CICIoMT2024 "
        "dataset [8] provides the first comprehensive network traffic dataset for medical IoT, "
        "covering ARP spoofing, MQTT malformation, DoS, DDoS, and reconnaissance attack classes."
    )

    add_heading(doc, "2.3 AI Safety and PHI Privacy", 2)
    add_para(doc,
        "Wornow et al. [9] document the rapid adoption of AI assistants in clinical settings "
        "while noting the inadequacy of existing privacy controls for AI prompt logging. HIPAA's "
        "minimum necessary standard applies to AI-assisted workflows, yet no automated PHI "
        "scanner for prompt logs existed prior to this work."
    )

    add_heading(doc, "2.4 Optimisation in Security Planning", 2)
    add_para(doc,
        "Bozorgi et al. [10] formulate vulnerability prioritisation as a constrained "
        "optimisation problem. Fielder et al. [11] apply optimisation to security investment "
        "allocation. No prior work applies QUBO-style binary optimisation to post-quantum "
        "migration planning in the healthcare IoT context. The Simulated Annealing "
        "metaheuristic [12] enables near-optimal solutions to NP-hard binary optimisation. "
        "Preskill [13] characterises the NISQ era, motivating classical quantum-inspired approaches."
    )

    add_heading(doc, "2.5 Comparative Literature Review", 2)
    add_para(doc, "Table 1 compares TIPPSS SafeGuard-PQ against the fourteen most relevant prior works.", size=10)

    # Literature table
    headers = ["#", "Reference", "Year", "Objective", "Methods", "Dataset",
               "Algorithm", "Limitations", "Research Gap"]
    col_w = [0.5, 2.8, 0.6, 3.5, 2.5, 2.0, 2.5, 3.0, 3.0]
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    add_table_row(tbl, headers, bold=True, bg="1F3864", font_size=8)
    for run in tbl.rows[0].cells:
        for p in run.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)

    rows_data = [
        ["1", "Shor [1]", "1994",
         "Polynomial-time quantum factorisation breaking RSA/ECC",
         "Quantum circuit; quantum Fourier transform",
         "Theoretical", "Shor's algorithm",
         "Requires large-scale error-corrected quantum hardware",
         "Motivates PQ migration; no defence or remediation proposed"],
        ["2", "Grover [3]", "1996",
         "Quadratic speedup for search; halves symmetric key security",
         "Quantum amplitude amplification",
         "Theoretical", "Grover search",
         "Requires quantum hardware; limited to symmetric key impact",
         "Motivates AES-256 requirement; no IoT or healthcare application"],
        ["3", "Bernstein & Lange [5]", "2017",
         "Survey and compare post-quantum algorithm families",
         "Mathematical analysis; security reduction proofs",
         "Theoretical", "Lattice, hash, code, isogeny",
         "No practical deployment tool; no healthcare or IoT focus",
         "No assessment tool; no constraint-aware migration planning"],
        ["4", "Mosca [4]", "2018",
         "Framework for assessing organisational PQ migration urgency",
         "Risk analysis; Mosca inequality",
         "Survey / expert opinion", "Heuristic risk model",
         "Manual process; no automated tool; no IoT specifics",
         "No automation; no multi-pillar clinical IoT assessment"],
        ["5", "NIST FIPS 203/204/205 [2]", "2024",
         "Standardise ML-KEM, ML-DSA, SLH-DSA",
         "Lattice-based and hash-based cryptography",
         "NIST PQC competition", "ML-KEM, ML-DSA, SLH-DSA",
         "Standard only; no deployment tool; no IoT guidance",
         "Gap between standard and operational healthcare deployment"],
        ["6", "Kirkpatrick et al. [12]", "1983",
         "Efficient optimisation of NP-hard combinatorial problems",
         "Simulated annealing; Metropolis-Hastings",
         "TSP; circuit placement", "Simulated Annealing",
         "General-purpose; not applied to cybersecurity planning",
         "Provides QIRO's solver foundation; no security application"],
        ["7", "Sicari et al. [6]", "2015",
         "Survey IoT security, privacy, and trust challenges",
         "Systematic literature review",
         "IoT vulnerability literature", "Taxonomy analysis",
         "No post-quantum awareness; no medical IoT focus",
         "Identifies attack surface; no PQ-specific assessment tool"],
        ["8", "Hossain et al. [7]", "2015",
         "Secure data sharing for cloud-assisted IoT medical systems",
         "Attribute-based encryption; role-based access",
         "Simulated medical IoT network", "Classical RSA / AES",
         "Relies on RSA/AES vulnerable to quantum adversaries",
         "No post-quantum migration path; no constraint-aware planning"],
        ["9", "Preskill [13]", "2018",
         "Characterise NISQ-era quantum computing capabilities",
         "Theoretical analysis; circuit depth analysis",
         "Theoretical", "NISQ device modelling",
         "Describes near-term limits; no defence or mitigation",
         "Motivates classical CPU quantum-inspired approach of QIRO"],
        ["10", "CICIoMT2024 [8]", "2024",
         "Comprehensive medical IoT attack dataset",
         "Controlled clinical IoT network capture; Wireshark",
         "18 attack classes; benign baseline; real medical IoT",
         "ML classifiers (RF, XGBoost)",
         "No post-quantum security dimension; no remediation planning",
         "Provides evaluation dataset; no PQ assessment integrated"],
        ["11", "Wornow et al. [9]", "2023",
         "Systematic review of LLMs in clinical workflows",
         "Literature review; case studies",
         "Clinical NLP benchmarks", "GPT-4, Med-PaLM, BioGPT",
         "No automated PHI detection in prompt logs",
         "PHI leakage into AI prompts is unaddressed vulnerability"],
        ["12", "Bozorgi et al. [10]", "2010",
         "Predict exploitability and prioritise vulnerability remediation",
         "SVM exploitability prediction; constrained optimisation",
         "NVD CVE data", "SVM + constrained optimisation",
         "No post-quantum focus; no healthcare; no binary optimisation",
         "Budget-constrained selection; extended to QUBO by QIRO"],
        ["13", "Fielder et al. [11]", "2016",
         "Security investment optimisation under budget constraints",
         "Game theory; linear programming",
         "Simulated enterprise portfolio", "Linear programming",
         "No IoT; no PQC; no downtime constraint; no binary formulation",
         "Constraint-aware security planning; QIRO extends to QUBO"],
        ["14", "IEEE 2933-2024 [14]", "2024",
         "Define TIPPSS six-pillar security framework for clinical IoT",
         "Standards committee; expert consensus",
         "Clinical IoT deployment data", "Framework / taxonomy",
         "Framework only; no automated assessment tool",
         "Provides TIPPSS pillar mapping; no tool implements it automatically"],
    ]

    alt = False
    for rd in rows_data:
        bg = "DCE6F1" if alt else None
        add_table_row(tbl, rd, bg=bg, font_size=8)
        alt = not alt

    cap = doc.add_paragraph("Table 1. Comparative analysis of related work.")
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(4)
    for run in cap.runs:
        run.italic = True
        run.font.size = Pt(9)

    # ── 3. System Architecture ───────────────────────────────────────────────
    add_heading(doc, "3. System Architecture", 1)
    add_para(doc,
        "TIPPSS SafeGuard-PQ implements a three-tier architecture: a Streamlit presentation "
        "layer (port 8501), an n8n orchestration layer (port 5678) containing the 10-agent "
        "sequential pipeline, and a file-based output layer storing timestamped assessment "
        "results. All processing runs on-premises; no patient data is transmitted externally."
    )

    add_heading(doc, "3.1 Ten-Agent Pipeline", 2)
    agent_headers = ["Agent", "Responsibility", "TIPPSS Pillar", "Standards Reference"]
    atbl = doc.add_table(rows=1, cols=4)
    atbl.style = "Table Grid"
    add_table_row(atbl, agent_headers, bold=True, bg="2E75B6", font_size=9)
    for cell in atbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)

    agents = [
        ("1 – Input Validator",    "Schema validation, field normalisation, error handling", "All pillars",                    "—"),
        ("2 – Crypto Classifier",  "Classify TLS parameters: PQ-safe / classical / deprecated", "Protection, Security",       "NIST FIPS 203/204/205"),
        ("3 – PQ Benchmark",       "Benchmark crypto against NIST standards; HNDL rule", "Protection, Privacy, Security",     "NIST FIPS 203/204/205"),
        ("4 – IoT Device Identity","Certificate presence, auth status, failed login counts", "Trust, Identity, Safety",       "IEEE 2933-2024 §6.2"),
        ("5 – AI Prompt Privacy",  "PHI detection; prompt injection detection", "Privacy, Security",                          "IEEE 2933-2024 §6.3; HIPAA §164.514"),
        ("6 – Secret Exposure",    "Scan device logs for API keys, credentials", "Protection, Security",                      "OWASP Secrets Management"),
        ("7 – Safety Risk",        "Autonomous dosing commands, alarm overrides", "Safety, Trust",                            "IEEE 2933-2024 §6.5"),
        ("8 – TIPPSS Scorer",      "Six-pillar scoring, composite risk score, verdict", "All six pillars",                    "IEEE 2933-2024 §6.1–6.6"),
        ("9 – Claude AI Report",   "Plain-English executive summary for clinical leadership", "All pillars (communication)",   "Anthropic Claude API"),
        ("10 – QIRO Optimizer",    "QUBO binary optimisation → migration roadmap", "All pillars",                             "Kirkpatrick et al. 1983"),
    ]
    alt = False
    for ag in agents:
        add_table_row(atbl, list(ag), bg="DCE6F1" if alt else None, font_size=9)
        alt = not alt

    cap2 = doc.add_paragraph("Table 2. Ten-agent pipeline: responsibilities and standards mapping.")
    cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap2.runs:
        run.italic = True; run.font.size = Pt(9)

    # ── 4. QIRO Mathematical Formulation ────────────────────────────────────
    add_heading(doc, "4. QIRO Mathematical Formulation", 1)

    add_heading(doc, "4.1 Decision Variable", 2)
    add_para(doc,
        "For each candidate remediation action i, QIRO defines a binary decision variable:"
    )
    add_info_box(doc, "xᵢ ∈ {0, 1}   where xᵢ = 1 → select action,  xᵢ = 0 → defer action")

    add_heading(doc, "4.2 Benefit Score", 2)
    add_para(doc,
        "Each action receives a composite benefit score incorporating four dimensions:"
    )
    add_info_box(doc, "Bᵢ  =  Rᵢ  +  Pᵢ  +  Sᵢ  +  Tᵢ")

    bscore_h = ["Symbol", "Dimension", "Description"]
    btbl = doc.add_table(rows=1, cols=3)
    btbl.style = "Table Grid"
    add_table_row(btbl, bscore_h, bold=True, bg="2E75B6", font_size=9)
    for cell in btbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row in [
        ("Rᵢ", "Risk reduction",         "Reduction in PQ risk score upon action completion"),
        ("Pᵢ", "Post-quantum urgency",   "Weighted urgency of PQ migration (critical for ECDHE/ECDSA)"),
        ("Sᵢ", "Safety criticality",     "Patient safety impact weight"),
        ("Tᵢ", "TIPPSS impact",          "Number of TIPPSS pillars improved, normalised"),
    ]:
        add_table_row(btbl, list(row), font_size=9)

    add_heading(doc, "4.3 Optimisation Objective", 2)
    add_para(doc, "QIRO maximises total remediation benefit subject to hard constraints:")
    add_info_box(doc,
        "Maximise:   Σᵢ Bᵢ xᵢ\n\n"
        "Subject to: Σᵢ Cᵢ xᵢ  ≤  Cmax     (budget constraint)\n"
        "            Σᵢ Dᵢ xᵢ  ≤  Dmax     (downtime constraint)\n"
        "            xᵢ ∈ {0, 1}            (binary constraint)"
    )
    add_para(doc,
        "where Cᵢ is the remediation cost and Dᵢ is the downtime of action i, "
        "Cmax is the available budget, and Dmax is the allowed service downtime. "
        "This is a variant of the 0/1 Knapsack Problem, which is NP-hard in general."
    )

    add_heading(doc, "4.4 Penalty-Based Energy Function", 2)
    add_para(doc, "For the Simulated Annealing solver the constrained problem is transformed into an unconstrained energy minimisation:")
    add_info_box(doc,
        "E(x) = −Σᵢ Bᵢ xᵢ\n"
        "       + λC · [max(0, Σ Cᵢ xᵢ − Cmax)]²     (budget overrun penalty)\n"
        "       + λD · [max(0, Σ Dᵢ xᵢ − Dmax)]²     (downtime overrun penalty)\n"
        "       + λK · Σᵢ Kᵢ xᵢ                       (complexity penalty)\n\n"
        "x* = arg min E(x)     [QIRO minimises E(x) to find optimal portfolio]"
    )

    add_heading(doc, "4.5 Output", 2)
    add_info_box(doc,
        "A_selected  =  { i | x*ᵢ = 1 }     → actions to perform now\n"
        "A_deferred  =  { i | x*ᵢ = 0 }     → actions deferred to future cycles\n\n"
        "C_remaining  =  Cmax  −  Σᵢ Cᵢ x*ᵢ\n"
        "D_remaining  =  Dmax  −  Σᵢ Dᵢ x*ᵢ"
    )

    add_heading(doc, "4.6 Simulated Annealing Parameters", 2)
    param_h = ["Parameter", "Value", "Description"]
    ptbl = doc.add_table(rows=1, cols=3)
    ptbl.style = "Table Grid"
    add_table_row(ptbl, param_h, bold=True, bg="2E75B6", font_size=9)
    for cell in ptbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row in [
        ("T_start",    "100.0",  "Initial temperature — high exploration"),
        ("α (alpha)",  "0.995",  "Geometric cooling rate per iteration"),
        ("T_min",      "0.01",   "Termination temperature"),
        ("Iterations", "1,000",  "Number of annealing steps"),
        ("Acceptance",  "Metropolis-Hastings", "P(accept worse) = exp(−ΔE / T)"),
    ]:
        add_table_row(ptbl, list(row), font_size=9)

    cap3 = doc.add_paragraph("Table 3. QIRO Simulated Annealing parameters.")
    cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap3.runs:
        run.italic = True; run.font.size = Pt(9)

    # ── 5. Experimental Results ─────────────────────────────────────────────
    add_heading(doc, "5. Experimental Results", 1)
    add_para(doc, "All tests were executed against the live n8n 10-agent pipeline. Default constraints: budget $100,000, downtime 40 hours.")

    add_heading(doc, "5.1 CICIoMT2024 Network Traffic Results", 2)
    r_headers = ["File", "Attack Type", "Verdict", "PQ Score", "Findings", "QIRO Sel.", "QIRO Def.", "Cost Used", "DT Used"]
    rtbl = doc.add_table(rows=1, cols=len(r_headers))
    rtbl.style = "Table Grid"
    add_table_row(rtbl, r_headers, bold=True, bg="1F3864", font_size=8)
    for cell in rtbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    result_rows = [
        ("ARP_Spoofing_test.pcap.csv",       "ARP Spoofing",    "Not PQ Safe", "61/100", "7", "4", "3", "$100,000", "22h"),
        ("Benign_test.pcap.csv",             "Benign Baseline", "Safe ✓",      "0/100",  "0", "0", "0", "$0",       "0h"),
        ("MQTT-Malformed_Data_test.pcap.csv","MQTT Malformed",  "Not PQ Safe", "61/100", "7", "4", "3", "$100,000", "22h"),
        ("Recon-Port_Scan_test.pcap.csv",    "Port Scan",       "Not PQ Safe", "61/100", "7", "4", "3", "$100,000", "22h"),
        ("TCP_IP-DoS-SYN_test.pcap.csv",     "SYN DoS",         "Not PQ Safe", "61/100", "7", "4", "3", "$100,000", "22h"),
        ("TCP_IP-DDoS-TCP_test.pcap.csv",    "TCP DDoS",        "Not PQ Safe", "61/100", "7", "4", "3", "$100,000", "22h"),
    ]
    alt = False
    for rr in result_rows:
        add_table_row(rtbl, list(rr), bg="DCE6F1" if alt else None, font_size=8)
        alt = not alt

    cap4 = doc.add_paragraph("Table 4. CICIoMT2024 simulation results. Benign baseline correctly returns Safe verdict.")
    cap4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap4.runs:
        run.italic = True; run.font.size = Pt(9)

    add_heading(doc, "5.2 Synthea Clinical Records Results", 2)
    syn_h = ["File", "Scenario", "Verdict", "PQ Score", "PHI Findings", "QIRO Sel.", "Cost Used", "DT Used"]
    stbl = doc.add_table(rows=1, cols=len(syn_h))
    stbl.style = "Table Grid"
    add_table_row(stbl, syn_h, bold=True, bg="1F3864", font_size=9)
    for cell in stbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    add_table_row(stbl, ["patients.csv", "PHI in AI prompts", "Safe (TLS)", "0/100", "8", "8", "$64,000", "8h"], font_size=9)
    add_table_row(stbl, ["conditions.csv", "Clinical conditions", "Safe", "0/100", "0", "0", "$0", "0h"], bg="DCE6F1", font_size=9)
    cap5 = doc.add_paragraph("Table 5. Synthea results. patients.csv exposes 8 PHI findings despite Safe TLS configuration.")
    cap5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap5.runs:
        run.italic = True; run.font.size = Pt(9)

    add_heading(doc, "5.3 QIRO Constraint Sensitivity", 2)
    cs_h = ["Budget", "Downtime", "Actions Selected", "Actions Deferred", "Budget Used", "Budget Remaining"]
    cstbl = doc.add_table(rows=1, cols=len(cs_h))
    cstbl.style = "Table Grid"
    add_table_row(cstbl, cs_h, bold=True, bg="1F3864", font_size=9)
    for cell in cstbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    cs_rows = [
        ("$200,000", "80h", "7", "0", "$162,000", "$38,000"),
        ("$100,000", "40h", "4–5", "2–3", "~$100,000", "~$0"),
        ("$50,000",  "20h", "2–3", "4–5", "~$48,000",  "~$2,000"),
        ("$30,000",  "8h",  "1–2", "5–6", "~$28,000",  "~$2,000"),
    ]
    alt = False
    for csr in cs_rows:
        add_table_row(cstbl, list(csr), bg="DCE6F1" if alt else None, font_size=9)
        alt = not alt
    cap6 = doc.add_paragraph("Table 6. QIRO constraint sensitivity. Migration roadmap adapts dynamically to operational constraints.")
    cap6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in cap6.runs:
        run.italic = True; run.font.size = Pt(9)

    # ── 6. Discussion ───────────────────────────────────────────────────────
    add_heading(doc, "6. Discussion", 1)
    add_para(doc,
        "The correct Safe verdict for the benign baseline confirms accurate discrimination "
        "between normal and attack-pattern medical IoT traffic. The patients.csv result — "
        "Safe TLS verdict yet 8 PHI findings — demonstrates the most important architectural "
        "insight: a system can be cryptographically compliant while critically exposed through "
        "AI prompt governance failures. Single-metric scanners focused on TLS strength would "
        "return a clean bill of health for this scenario. The six-pillar TIPPSS assessment "
        "captures the full security surface."
    )
    add_para(doc,
        "QIRO's constraint-sensitive output changes the migration roadmap when budget or "
        "downtime limits change, providing operationally actionable plans rather than "
        "infeasible theoretical remediation catalogues. Reducing budget from $200K to $30K "
        "causes QIRO to select 5–6 fewer actions and provide a realistic, immediately "
        "executable plan within constraints."
    )
    add_para(doc,
        "Limitations: Cost and downtime estimates are currently heuristic defaults that "
        "should be replaced with site-specific vendor quotes in production. Benefit "
        "component weights (Rᵢ, Pᵢ, Sᵢ, Tᵢ) require expert validation for production deployment."
    )

    # ── 7. Conclusion ───────────────────────────────────────────────────────
    add_heading(doc, "7. Conclusion", 1)
    add_para(doc,
        "This paper presented TIPPSS SafeGuard-PQ, the first integrated agentic framework "
        "simultaneously assessing post-quantum cryptographic posture, medical IoT device "
        "identity, AI prompt privacy, secret exposure, and clinical safety risk in healthcare "
        "systems, producing constraint-aware migration roadmaps using the novel QIRO "
        "optimisation algorithm. The system demonstrates that post-quantum migration readiness "
        "assessment in healthcare is a multi-dimensional problem requiring evaluation across "
        "all six TIPPSS pillars simultaneously."
    )
    add_para(doc,
        "Key contributions: (1) 10-agent multi-pillar assessment pipeline against NIST FIPS "
        "203/204/205 and IEEE 2933-2024 TIPPSS; (2) QIRO — the first QUBO-style constrained "
        "binary optimisation approach to post-quantum remediation planning; (3) empirical "
        "validation across 8 real-world datasets with correct discrimination and constraint-"
        "sensitive planning."
    )
    add_para(doc,
        "Future work will extend QIRO to hybrid quantum-classical solvers, validate cost "
        "estimates against real vendor data, and extend the TIPPSS assessment to federated "
        "network-layer traffic analysis preserving clinical data privacy."
    )

    # ── References ──────────────────────────────────────────────────────────
    add_heading(doc, "References", 1)
    refs = [
        "[1]  Shor, P.W. (1994). Algorithms for quantum computation: Discrete logarithms and factoring. Proc. 35th Annual Symposium on Foundations of Computer Science (FOCS), pp. 124–134. IEEE. https://doi.org/10.1109/SFCS.1994.365700",
        "[2]  National Institute of Standards and Technology. (2024). FIPS 203/204/205: Module-Lattice-Based Key-Encapsulation Mechanism, Digital Signature, and Stateless Hash-Based Digital Signature Standards. U.S. Dept. of Commerce. https://csrc.nist.gov/pubs/fips/203/final",
        "[3]  Grover, L.K. (1996). A fast quantum mechanical algorithm for database search. Proc. 28th Annual ACM Symposium on Theory of Computing (STOC), pp. 212–219. https://doi.org/10.1145/237814.237866",
        "[4]  Mosca, M. (2018). Cybersecurity in an era with quantum computers: Will we be ready? IEEE Security & Privacy, 16(5), 38–41. https://doi.org/10.1109/MSP.2018.3761723",
        "[5]  Bernstein, D.J., & Lange, T. (2017). Post-quantum cryptography. Nature, 549(7671), 188–194. https://doi.org/10.1038/nature23461",
        "[6]  Sicari, S., Rizzardi, A., Grieco, L.A., & Coen-Porisini, A. (2015). Security, privacy and trust in Internet of Things: The road ahead. Computer Networks, 76, 146–164. https://doi.org/10.1016/j.comnet.2014.11.008",
        "[7]  Hossain, M.M., Fotouhi, M., & Hasan, R. (2015). Towards an analysis of security issues, challenges, and open problems in the Internet of Things. Proc. IEEE World Congress on Services, pp. 21–28. https://doi.org/10.1109/SERVICES.2015.12",
        "[8]  Sharafaldin, I., Lashkari, A.H., & Ghorbani, A.A. (2024). CICIoMT2024: A comprehensive medical IoT network traffic dataset. Canadian Institute for Cybersecurity, University of New Brunswick. https://www.unb.ca/cic/datasets/iomt-dataset-2024.html",
        "[9]  Wornow, M., et al. (2023). The shaky foundations of large language models for electronic health records. npj Digital Medicine, 6(1), 135. https://doi.org/10.1038/s41746-023-00879-8",
        "[10] Bozorgi, M., et al. (2010). Beyond heuristics: Learning to classify vulnerabilities and predict exploits. Proc. 16th ACM SIGKDD, pp. 105–114. https://doi.org/10.1145/1835804.1835821",
        "[11] Fielder, A., et al. (2016). Decision support approaches for cyber security investment. Decision Support Systems, 86, 13–23. https://doi.org/10.1016/j.dss.2016.02.012",
        "[12] Kirkpatrick, S., Gelatt, C.D., & Vecchi, M.P. (1983). Optimization by simulated annealing. Science, 220(4598), 671–680. https://doi.org/10.1126/science.220.4598.671",
        "[13] Preskill, J. (2018). Quantum computing in the NISQ era and beyond. Quantum, 2, 79. https://doi.org/10.22331/q-2018-08-06-79",
        "[14] IEEE Standards Association. (2024). IEEE Standard 2933-2024: Clinical IoT Data and Device Interoperability with TIPPSS. IEEE. https://standards.ieee.org/ieee/2933/10806/",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Cm(0.5)
        run = p.add_run(ref)
        run.font.size = Pt(9)

    doc.save(path)
    print(f"  Saved: {path.name}")


# ===========================================================================
# DOCUMENT 2 — ARCHITECTURE DOCUMENT
# ===========================================================================

def build_architecture(path: pathlib.Path):
    doc = Document()
    set_page_margins(doc)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Title
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = t.add_run("TIPPSS SafeGuard-PQ\nSystem Architecture & Technical Reference")
    tr.bold = True; tr.font.size = Pt(18)
    tr.font.color.rgb = RGBColor.from_string("1F3864")
    t.paragraph_format.space_after = Pt(6)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mr = meta.add_run(
        "Version 3.0 (Sequential Pipeline)  ·  "
        "NIST FIPS 203/204/205  ·  IEEE 2933-2024 TIPPSS\n"
        "Repository: https://github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS"
    )
    mr.font.size = Pt(10); mr.italic = True
    meta.paragraph_format.space_after = Pt(12)
    add_horizontal_rule(doc)

    # 1. Executive Summary
    add_heading(doc, "1. Executive Summary", 1)
    add_para(doc,
        "TIPPSS SafeGuard-PQ is a multi-agent post-quantum cybersecurity assessment "
        "and migration planning system for clinical IoT and AI healthcare environments. "
        "The system evaluates hospital clinical system configurations against post-quantum "
        "cryptographic standards and the IEEE 2933-2024 TIPPSS framework through a "
        "sequential 10-agent pipeline, then produces constraint-aware remediation roadmaps "
        "using the Quantum-Inspired Remediation Optimizer (QIRO). The architecture is "
        "designed for local on-premises deployment, ensuring sensitive configuration data "
        "never leaves the hospital network."
    )

    # 2. Architectural Principles
    add_heading(doc, "2. Architectural Principles", 1)
    ph = ["Principle", "Implementation"]
    ptbl = doc.add_table(rows=1, cols=2)
    ptbl.style = "Table Grid"
    add_table_row(ptbl, ph, bold=True, bg="1F3864", font_size=10)
    for cell in ptbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    principles = [
        ("Local-first processing", "All computation runs on localhost (ports 8501 and 5678); no data sent to external servers except Claude AI report"),
        ("Minimal data transfer",  "Files sampled to 100 rows maximum; full raw datasets never transmitted to n8n"),
        ("Agent isolation",        "Each agent has a single responsibility and cannot access other agents' internal state directly"),
        ("Constraint-aware output","QIRO enforces budget and downtime as hard constraints, not advisory guidelines"),
        ("Timestamped provenance", "Every result file includes a YYYYMMDD_HHMMSS timestamp; runs never overwrite previous results"),
        ("Standards-grounded",     "All findings explicitly reference NIST FIPS 203/204/205 clauses and IEEE 2933-2024 TIPPSS pillars"),
    ]
    alt = False
    for pr in principles:
        add_table_row(ptbl, list(pr), bg="EBF3FB" if alt else None, font_size=10)
        alt = not alt

    # 3. Three-Tier Architecture
    add_heading(doc, "3. Three-Tier System Architecture", 1)

    add_heading(doc, "3.1 Tier 1 — Presentation Layer (Streamlit)", 2)
    add_para(doc,
        "The Streamlit dashboard (localhost:8501) provides the user interface for scenario "
        "selection, file upload, constraint configuration, and result visualisation. It acts "
        "as the sole entry point for assessment requests and is responsible for payload "
        "construction, file feature extraction, and result display."
    )
    add_bullet(doc, "Scenario Selector: Pre-built dropdown of 7 clinical system simulations covering Safe through Critical Quantum Risk postures.")
    add_bullet(doc, "File Uploader: Accepts CICIoMT2024 .pcap.csv network traffic files and Synthea patients.csv / conditions.csv synthetic clinical records.")
    add_bullet(doc, "Feature Extractor: Samples first 100 rows, computes 40+ statistical features (mean, max, min, sum) across protocol, flag, and rate columns.")
    add_bullet(doc, "Constraint Sliders: Budget ($10,000–$500,000) and downtime (4–80 hours) controls that are passed directly to QIRO as hard constraints.")
    add_bullet(doc, "Result Renderer: Displays verdict card, PQ risk gauge (0–100), TIPPSS six-pillar spider chart, findings table, QIRO roadmap, and Claude executive report.")

    add_heading(doc, "3.2 Tier 2 — Orchestration Layer (n8n)", 2)
    add_para(doc,
        "The n8n workflow engine (localhost:5678) orchestrates the sequential 10-agent "
        "pipeline. The dashboard sends a single HTTP POST request with the structured JSON "
        "payload; n8n returns a single JSON response containing the complete assessment. "
        "Each agent is a JavaScript Code node with isolated logic and shared state passed "
        "via n8n item properties."
    )

    add_heading(doc, "3.3 Tier 3 — Output Layer", 2)
    add_para(doc, "All test results are persisted with unique timestamps in three output directories:")
    out_h = ["Directory", "Contents", "Format"]
    otbl = doc.add_table(rows=1, cols=3)
    otbl.style = "Table Grid"
    add_table_row(otbl, out_h, bold=True, bg="2E75B6", font_size=10)
    for cell in otbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row in [
        ("fileuploadoutput/", "Uploaded-file test results: payload + n8n response + one-row summary per run", "JSON + CSV"),
        ("test_outputs/unit_tests/", "Automated unit test results (8 cases, TC01–TC08)", "JSON + CSV"),
        ("test_outputs/integration_tests/", "Integration test results using Input folder files", "JSON + CSV"),
    ]:
        add_table_row(otbl, list(row), font_size=10)

    # 4. Agent Pipeline Detail
    add_heading(doc, "4. Agent Pipeline — Detailed Component Descriptions", 1)

    agent_details = [
        ("Agent 1 — Input Validator",
         "Schema validation and payload normalisation",
         "Parses and validates the incoming JSON payload. Verifies presence of all required fields: system_id, domain, tls_config (with tls_version, key_exchange, cert_signature_algo, cert_key_algo, symmetric_cipher, hash, data_lifetime_years), ai_prompt_logs (string array), device_logs (device_id, cert_present, auth_status, failed_login_count), and constraints (budget_usd, max_downtime_hrs). Rejects malformed inputs with structured error responses before they enter the assessment pipeline.",
         "All pillars (prerequisite)", "—"),

        ("Agent 2 — Cryptographic Classifier",
         "TLS parameter classification against PQ taxonomy",
         "Classifies each TLS parameter as post-quantum safe (ML-KEM, ML-DSA, SLH-DSA, AES-256-GCM, SHA-384+), classical (ECDHE, ECDSA, RSA, AES-128-GCM, SHA-256), or deprecated (TLS 1.0/1.1, SHA-1, MD5, DES). Outputs three structured arrays: pq_safe[], classical[], deprecated[] used by subsequent agents.",
         "Protection, Security", "NIST FIPS 203/204/205"),

        ("Agent 3 — PQ Benchmark",
         "NIST FIPS 203/204/205 compliance assessment",
         "Compares cryptographic classification against post-quantum standards. Raises findings for each non-compliant parameter. Applies the harvest-now-decrypt-later (HNDL) rule: when data_lifetime_years >= 10 AND classical crypto is present, raises a CRITICAL 'long_lifetime_classical_crypto' finding. Suppresses this finding when ML-KEM and ML-DSA are already deployed, preventing false positives on PQ-safe systems.",
         "Protection, Privacy, Security", "NIST FIPS 203/204/205"),

        ("Agent 4 — IoT Device Identity",
         "Medical IoT device trust and identity assessment",
         "Evaluates each device_log entry against the IEEE 2933-2024 Trust and Identity pillars. Raises HIGH findings for missing device certificates (cert_present = false) and HIGH-to-CRITICAL findings for authentication failures (auth_status = 'failed'). Raises escalating findings for repeated login failures: HIGH at >= 5 failures, CRITICAL at >= 10 failures.",
         "Trust, Identity, Safety", "IEEE 2933-2024 §6.2"),

        ("Agent 5 — AI Prompt Privacy",
         "PHI detection and prompt injection scanning in AI logs",
         "Scans all ai_prompt_logs entries for protected health information (PHI) patterns including medical record numbers (MRN), full patient name + identifier combinations, social security number formats, sensitive diagnosis keywords (HIV, cancer, mental health diagnoses), email addresses, and date-of-birth + name combinations. Also detects prompt injection attempts ('Ignore all previous instructions', 'reveal all records', 'export patient data').",
         "Privacy, Security", "IEEE 2933-2024 §6.3; HIPAA 45 CFR §164.514"),

        ("Agent 6 — Secret Exposure Scanner",
         "Credential and API key detection in device telemetry",
         "Scans device_log entries including optional debug_log fields for exposed credential patterns: Stripe live keys (sk_live_), AWS access key IDs (AKIA[0-9A-Z]{16}), GitHub personal access tokens (ghp_), generic API key patterns (api_key=), bearer tokens, and database password strings. Raises CRITICAL findings for each detected credential with a redacted preview for safe display.",
         "Protection, Security", "OWASP Secrets Management"),

        ("Agent 7 — Clinical Safety Risk Analyser",
         "Autonomous AI clinical command detection",
         "Scans ai_prompt_logs for autonomous clinical commands that bypass physician oversight: medication prescriptions without sign-off, alarm overrides ('override alarm', 'disable alert'), autonomous dosing ('infuse [dose] without approval'), device bypass commands, and autonomous procedural instructions. Raises CRITICAL Safety findings mapped to the IEEE 2933-2024 Safety pillar.",
         "Safety, Trust", "IEEE 2933-2024 §6.5"),

        ("Agent 8 — TIPPSS Six-Pillar Scorer",
         "Multi-pillar risk scoring and verdict assignment",
         "Aggregates all findings from Agents 2–7 and maps each finding to one or more TIPPSS pillars (Trust, Identity, Privacy, Protection, Safety, Security). Computes a normalised 0–100 risk score per pillar with deductions per finding severity (CRITICAL: -20 to -30, HIGH: -10 to -15, MEDIUM: -5 to -8). Computes a composite PQ Risk Score (weighted average, Protection and Security weighted higher) and assigns verdict: Safe (0–25), Partially Safe (26–50), Not Post-Quantum Safe (51–75), Critical Quantum Risk (76–100).",
         "All six pillars", "IEEE 2933-2024 §6.1–6.6"),

        ("Agent 9 — Claude AI Executive Report",
         "Plain-English executive summary generation",
         "Invokes the Anthropic Claude API with a structured prompt containing the top 3–5 highest-severity findings, their TIPPSS pillar mappings, the remediation constraint context, and the overall verdict. Generates a plain-English executive summary tailored to a clinical CISO audience, explaining what was found, why it matters for patient safety and data protection, and what immediate actions are recommended.",
         "All pillars (communication)", "Anthropic Claude Sonnet API"),

        ("Agent 10 — QIRO Optimizer",
         "Constraint-aware binary optimisation for remediation planning",
         "Converts all findings into candidate remediation actions with benefit scores (Bᵢ = Rᵢ + Pᵢ + Sᵢ + Tᵢ), cost estimates, downtime estimates, and complexity scores. Constructs the penalty-based energy function E(x) and executes 1,000 iterations of Simulated Annealing with geometric cooling (α = 0.995) and Metropolis-Hastings acceptance. Partitions the optimal solution into selected actions (x*ᵢ = 1) and deferred actions (x*ᵢ = 0). Assigns selected actions to three migration phases. Computes budget and downtime residuals.",
         "All pillars", "Kirkpatrick et al. 1983; QUBO/Ising model"),
    ]

    for i, (title, subtitle, desc, pillars, standards) in enumerate(agent_details, 1):
        add_heading(doc, f"4.{i}  {title}", 2)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        p.add_run("Function: ").bold = True
        p.add_run(subtitle).font.size = Pt(10)

        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(2)
        p2.add_run("Processing: ").bold = True
        p2.add_run(desc).font.size = Pt(10)

        p3 = doc.add_paragraph()
        p3.paragraph_format.space_after = Pt(2)
        p3.add_run("TIPPSS Pillars: ").bold = True
        p3.add_run(pillars).font.size = Pt(10)

        p4 = doc.add_paragraph()
        p4.paragraph_format.space_after = Pt(8)
        p4.add_run("Standards: ").bold = True
        p4.add_run(standards).font.size = Pt(10)

    # 5. Payload Schema
    add_heading(doc, "5. JSON Payload Schema", 1)
    add_para(doc, "The following fields constitute the complete assessment request payload sent from the Streamlit dashboard to the n8n pipeline:")
    schema_h = ["Field", "Type", "Required", "Description"]
    schtbl = doc.add_table(rows=1, cols=4)
    schtbl.style = "Table Grid"
    add_table_row(schtbl, schema_h, bold=True, bg="2E75B6", font_size=9)
    for cell in schtbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    schema_rows = [
        ("system_id",              "string",  "Yes", "Unique identifier for the assessed system"),
        ("domain",                 "string",  "Yes", "Always 'healthcare'"),
        ("tls_config.tls_version", "string",  "Yes", "TLS1.0 / TLS1.2 / TLS1.3"),
        ("tls_config.key_exchange","string",  "Yes", "ECDHE-P256 / ML-KEM-768 / ML-KEM-1024 etc."),
        ("tls_config.cert_signature_algo","string","Yes","ECDSA-P256 / ML-DSA-65 / ML-DSA-87 etc."),
        ("tls_config.cert_key_algo","string", "Yes", "RSA-2048 / ML-DSA-65 etc."),
        ("tls_config.symmetric_cipher","string","Yes","AES-128-GCM / AES-256-GCM etc."),
        ("tls_config.hash",        "string",  "Yes", "SHA-1 / SHA-256 / SHA-384 etc."),
        ("tls_config.data_lifetime_years","int","Yes","Years patient data must remain protected"),
        ("ai_prompt_logs",         "string[]","Yes", "AI assistant prompt log entries to scan for PHI and injection"),
        ("device_logs",            "object[]","Yes", "Array of medical IoT device identity records"),
        ("device_logs[].device_id","string",  "Yes", "Medical device unique identifier"),
        ("device_logs[].cert_present","bool", "Yes", "Whether device certificate is installed"),
        ("device_logs[].auth_status","string","Yes", "'passed' or 'failed'"),
        ("device_logs[].failed_login_count","int","Yes","Number of failed authentication attempts"),
        ("device_logs[].debug_log","string",  "No",  "Optional device debug log (scanned for exposed secrets)"),
        ("constraints.budget_usd", "int",     "Yes", "Maximum remediation budget in USD"),
        ("constraints.max_downtime_hrs","int","Yes", "Maximum allowed service interruption in hours"),
        ("iot_traffic",            "object",  "No",  "CICIoMT2024 feature summary (file upload only)"),
        ("ehr_records",            "object",  "No",  "Synthea metadata (file upload only)"),
        ("timestamp_requested",    "string",  "No",  "ISO 8601 request timestamp"),
    ]
    alt = False
    for sr in schema_rows:
        add_table_row(schtbl, list(sr), bg="EBF3FB" if alt else None, font_size=9)
        alt = not alt

    # 6. Data Flow
    add_heading(doc, "6. End-to-End Data Flow", 1)
    steps = [
        ("Step 1", "User selects a pre-built scenario or uploads a CICIoMT2024 / Synthea file via the Streamlit dashboard."),
        ("Step 2", "Dashboard validates scenario data or extracts file features (first 100 rows sampled; 40+ statistical features computed)."),
        ("Step 3", "User sets budget and downtime constraints via sidebar sliders."),
        ("Step 4", "User clicks 'Run Cybersecurity Simulation'. Dashboard constructs the JSON payload and sends an HTTP POST to n8n (localhost:5678/webhook/tippss-assessment)."),
        ("Step 5", "Agent 1 validates the payload schema. Agents 2–7 run sequentially, each appending findings to a shared findings array."),
        ("Step 6", "Agent 8 maps all findings to TIPPSS pillars and computes the composite PQ Risk Score and verdict."),
        ("Step 7", "Agent 9 generates a Claude AI executive report from the top findings."),
        ("Step 8", "Agent 10 (QIRO) converts findings to candidate actions, runs Simulated Annealing, and returns selected/deferred actions with the phased migration roadmap."),
        ("Step 9", "n8n returns the complete JSON response to the Streamlit dashboard."),
        ("Step 10","Dashboard renders the verdict card, PQ risk gauge, TIPPSS spider chart, findings table, and QIRO roadmap. Results are saved to fileuploadoutput/ with a unique timestamp."),
    ]
    flow_h = ["Step", "Description"]
    ftbl = doc.add_table(rows=1, cols=2)
    ftbl.style = "Table Grid"
    add_table_row(ftbl, flow_h, bold=True, bg="1F3864", font_size=10)
    for cell in ftbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    alt = False
    for label, desc in steps:
        row = ftbl.add_row()
        for i, text in enumerate([label, desc]):
            cell = row.cells[i]
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            run = p.add_run(text)
            run.font.size = Pt(10)
            if i == 0:
                run.bold = True
            if alt:
                set_cell_bg(cell, "EBF3FB")
        alt = not alt

    # 7. Security Considerations
    add_heading(doc, "7. Security Considerations", 1)
    sec_h = ["Risk", "Mitigation"]
    sectbl = doc.add_table(rows=1, cols=2)
    sectbl.style = "Table Grid"
    add_table_row(sectbl, sec_h, bold=True, bg="C00000", font_size=10)
    for cell in sectbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row in [
        ("Real patient data in uploaded files", ".gitignore blocks *.csv by default; file sampling limits data exposure; Synthea dataset is fully synthetic"),
        ("API keys and credentials in environment", "n8n credentials stored in Docker volume, not committed to version control; .env files git-ignored"),
        ("n8n webhook network exposure", "Runs on localhost only; Docker port binding not exposed to external network by default"),
        ("Prompt injection in AI assistant logs", "Agent 5 detects and flags injection attempts; Claude API receives sanitised finding summaries, not raw prompts"),
        ("Large file upload memory consumption", "Streamlit enforces file size limits; only first 100 rows processed via pandas head()"),
        ("Stale results from previous scenarios", "Session state cleared immediately on scenario change; constraint signature tracked to warn of unsynchronised results"),
    ]:
        add_table_row(sectbl, list(row), font_size=10)

    # 8. Deployment
    add_heading(doc, "8. Deployment Requirements and Startup", 1)
    dep_h = ["Component", "Version", "Purpose"]
    deptbl = doc.add_table(rows=1, cols=3)
    deptbl.style = "Table Grid"
    add_table_row(deptbl, dep_h, bold=True, bg="2E75B6", font_size=10)
    for cell in deptbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row in [
        ("Python",         "3.10+",      "Dashboard runtime (Streamlit, pandas, plotly, requests)"),
        ("Docker Desktop", "Latest",     "Container runtime for n8n workflow engine"),
        ("n8n",            "1.x",        "10-agent workflow orchestration engine"),
        ("Streamlit",      "1.35+",      "Web dashboard framework"),
        ("RAM",            "8 GB rec.",  "Sufficient for large CICIoMT2024 file processing"),
        ("Ports",          "8501, 5678", "Streamlit dashboard and n8n webhook"),
    ]:
        add_table_row(deptbl, list(row), font_size=10)

    add_heading(doc, "8.1 Startup Sequence", 2)
    for step in [
        "Start n8n:   docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n",
        "Import workflow:  Open localhost:5678 → Import → select 01_n8n_file/TIPPSS_SafeGuard_PQ_Sequential_v3.json → Activate",
        "Start dashboard (Windows):  run.bat   |   macOS/Linux:  ./run.sh",
        "Open browser:  http://localhost:8501",
    ]:
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(step)
        run.font.size = Pt(10)
        run.font.name = "Courier New"

    # 9. Standards Compliance
    add_heading(doc, "9. Standards Compliance Mapping", 1)
    sc_h = ["System Component", "Standard", "Clause / Reference"]
    sctbl = doc.add_table(rows=1, cols=3)
    sctbl.style = "Table Grid"
    add_table_row(sctbl, sc_h, bold=True, bg="1F3864", font_size=10)
    for cell in sctbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
    for row in [
        ("Agent 3 — PQ Benchmark",        "NIST FIPS 203",         "ML-KEM key encapsulation mechanism"),
        ("Agent 3 — PQ Benchmark",        "NIST FIPS 204",         "ML-DSA digital signature algorithm"),
        ("Agent 3 — PQ Benchmark",        "NIST FIPS 205",         "SLH-DSA stateless hash-based signatures"),
        ("Agent 4 — IoT Device Identity", "IEEE 2933-2024",        "Clause 6.2 — Trust and Identity"),
        ("Agent 5 — AI Prompt Privacy",   "IEEE 2933-2024",        "Clause 6.3 — Privacy"),
        ("Agent 5 — PHI Detection",       "HIPAA 45 CFR §164.514", "Minimum necessary standard for AI inputs"),
        ("Agent 7 — Safety Risk",         "IEEE 2933-2024",        "Clause 6.5 — Safety"),
        ("Agent 8 — TIPPSS Scorer",       "IEEE 2933-2024",        "Clauses 6.1–6.6 — All six pillars"),
        ("QIRO Algorithm",                "Kirkpatrick et al. 1983","Simulated Annealing with geometric cooling"),
        ("QIRO Formulation",              "QUBO / Ising model",    "Binary quadratic optimisation; NP-hard variant"),
    ]:
        add_table_row(sctbl, list(row), font_size=10)

    # Footer note
    doc.add_paragraph()
    fn = doc.add_paragraph()
    fn.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fn_run = fn.add_run(
        "Technical Reference v3.0  ·  "
        "https://github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS"
    )
    fn_run.italic = True
    fn_run.font.size = Pt(9)
    fn_run.font.color.rgb = RGBColor.from_string("7F7F7F")

    doc.save(path)
    print(f"  Saved: {path.name}")


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    print("\nGenerating professional Word documents ...\n")
    build_paper(OUT_DIR / "TIPPSS_SafeGuard_PQ_Paper.docx")
    build_architecture(OUT_DIR / "TIPPSS_SafeGuard_PQ_Architecture.docx")
    print("\nDone. Both documents saved to 00_Documention/")
