"""
Generate professional Word document answering all project questions.
Replaces n8n with Sequential Agentic Framework; removes non-professional language.
Run: python generate_qa_doc.py
"""

import pathlib
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT_DIR = pathlib.Path(__file__).parent / "00_Documention"
OUT_DIR.mkdir(exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def set_cell_bg(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_margins(doc, top=2.5, bottom=2.5, left=3.0, right=2.5):
    s = doc.sections[0]
    s.top_margin    = Cm(top)
    s.bottom_margin = Cm(bottom)
    s.left_margin   = Cm(left)
    s.right_margin  = Cm(right)


def add_hr(doc, color="2E75B6"):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "6")
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), color)
    pBdr.append(bot)
    pPr.append(pBdr)
    p.paragraph_format.space_after = Pt(4)


def heading(doc, text, level, color="1F3864"):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for r in h.runs:
        r.font.color.rgb = RGBColor.from_string(color)
    return h


def para(doc, text, bold=False, italic=False, size=11, after=6, color=None,
         indent=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if indent:
        p.paragraph_format.left_indent = Cm(0.5)
    r = p.add_run(text)
    r.bold   = bold
    r.italic = italic
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    return p


def bullet(doc, text, size=11):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.size = Pt(size)
    return p


def numbered(doc, text, size=11):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.size = Pt(size)
    return p


def section_box(doc, title, color_hex="1F3864"):
    """Section divider box."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.cell(0, 0)
    set_cell_bg(cell, color_hex)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.left_indent  = Pt(8)
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor(255, 255, 255)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def q_block(doc, q_num, q_title, q_hint):
    """Question heading + hint."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(2)
    r = p.add_run(f"{q_num}: {q_title}")
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor.from_string("2E75B6")

    hint_p = doc.add_paragraph()
    hint_p.paragraph_format.space_after = Pt(6)
    hr = hint_p.add_run(q_hint)
    hr.italic = True
    hr.font.size = Pt(10)
    hr.font.color.rgb = RGBColor.from_string("595959")


def answer_para(doc, text, size=11):
    p = doc.add_paragraph()
    p.paragraph_format.space_after  = Pt(6)
    p.paragraph_format.space_before = Pt(0)
    r = p.add_run(text)
    r.font.size = Pt(size)
    return p


def answer_bullet(doc, label, text, size=11):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    r_label = p.add_run(label + " ")
    r_label.bold = True
    r_label.font.size = Pt(size)
    r_text = p.add_run(text)
    r_text.font.size = Pt(size)


def callout(doc, text, bg="EBF3FB"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.cell(0, 0)
    set_cell_bg(cell, bg)
    p = cell.paragraphs[0]
    p.paragraph_format.left_indent  = Pt(8)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor.from_string("1F3864")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


# ── main document builder ────────────────────────────────────────────────────

def build(path: pathlib.Path):
    doc = Document()
    set_margins(doc)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    # ── Cover ────────────────────────────────────────────────────────────────
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = tp.add_run("TIPPSS SafeGuard-PQ")
    tr.bold = True
    tr.font.size = Pt(22)
    tr.font.color.rgb = RGBColor.from_string("1F3864")
    tp.paragraph_format.space_after = Pt(4)

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sp.add_run(
        "Agentic Post-Quantum Cybersecurity Assessment & Migration Planning\n"
        "for Clinical Edge IoT and AI Healthcare Systems"
    )
    sr.font.size = Pt(13)
    sr.font.color.rgb = RGBColor.from_string("2E75B6")
    sp.paragraph_format.space_after = Pt(4)

    mp = doc.add_paragraph()
    mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mr = mp.add_run(
        "Pavan Gemmanjunath  ·  pavan5119m@gmail.com\n"
        "Repository: https://github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS\n"
        "Standards: NIST FIPS 203/204/205  ·  IEEE 2933-2024 TIPPSS"
    )
    mr.italic = True
    mr.font.size = Pt(10)
    mr.font.color.rgb = RGBColor.from_string("595959")
    mp.paragraph_format.space_after = Pt(10)
    add_hr(doc)

    # ── Project Summary ──────────────────────────────────────────────────────
    callout(doc,
        "Summary:  Hospitals run AI systems and connected medical devices over cryptography "
        "that quantum computers will break — and adversaries are already harvesting encrypted "
        "patient data today to decrypt it when quantum hardware matures. Healthcare records "
        "carry 15-to-30-year confidentiality requirements, making this an immediate operational "
        "risk rather than a future concern. TIPPSS SafeGuard-PQ is a sequential agentic "
        "platform that scans clinical IoT systems, AI workflows, and hospital networks, "
        "identifies quantum-vulnerable cryptography, PHI leakage in AI prompts, and device "
        "identity weaknesses — all mapped to the IEEE 2933-2024 TIPPSS framework — and "
        "delivers a clear, budget-aware migration roadmap to NIST post-quantum standards.",
        bg="EBF3FB"
    )

    callout(doc,
        "Track Alignment:  TIPPSS SafeGuard-PQ addresses the Healthcare and Assistive "
        "Technologies security domain by tackling the most critical and overlooked threat "
        "to clinical systems: post-quantum vulnerability. Medical IoT devices, AI healthcare "
        "assistants, and EHR systems operate on classical cryptography (RSA, ECDSA, ECDH) "
        "that quantum computers will render insecure. Patient data carries 15-to-30-year "
        "confidentiality requirements under HIPAA and GDPR, meaning harvest-now-decrypt-later "
        "attacks already expose today's clinical records to future adversaries. The platform "
        "scans Clinical Edge IoT devices, hospital edge gateways, EHR APIs, and AI prompt logs "
        "to detect PHI leakage, weak device identity, exposed credentials, prompt injection, "
        "and quantum-vulnerable cryptography. Every finding is mapped to the TIPPSS framework "
        "and benchmarked against NIST-standardised post-quantum algorithms ML-KEM, ML-DSA, "
        "and SLH-DSA. The platform delivers a risk verdict, TIPPSS score, and migration plan "
        "— providing automated readiness assessment that no current healthcare cybersecurity "
        "tool delivers.",
        bg="E2EFDA"
    )

    add_hr(doc)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION A — PROBLEM STATEMENT
    # ════════════════════════════════════════════════════════════════════════
    section_box(doc, "SECTION A — PROBLEM STATEMENT")

    # Q1
    q_block(doc, "Question 1", "Description of the Problem",
        "(Clearly articulate the specific cybersecurity gap, vulnerability, or systemic "
        "challenge your project addresses. Avoid vague generalizations; pinpoint the exact "
        "technical or operational bottleneck.)")

    answer_para(doc,
        "Hospitals operating AI-driven clinical assistants and connected medical IoT devices "
        "— including ECG monitors, infusion pumps, patient wearables, edge gateways, and EHR "
        "APIs — currently lack any automated mechanism to assess whether their cryptographic "
        "infrastructure, AI workflow controls, and device-identity systems are post-quantum "
        "safe and aligned with the IEEE 2933-2024 TIPPSS framework."
    )
    answer_para(doc,
        "The specific technical gap is the complete absence of a unified, agentic assessment "
        "pipeline that simultaneously detects all of the following risk categories in one "
        "coherent platform:"
    )
    answer_bullet(doc, "(1) Quantum-vulnerable cryptography:",
        "RSA, ECDSA, ECDH, deprecated TLS versions (1.0, 1.1), and SHA-1 across the "
        "hospital network — all broken by Shor's algorithm on a sufficiently capable "
        "quantum processor.")
    answer_bullet(doc, "(2) PHI and PII leakage in AI systems:",
        "Protected health information appearing inside AI prompt logs, inter-service API "
        "payloads, and EHR data flows — a direct HIPAA violation that current tools do "
        "not detect at the AI layer.")
    answer_bullet(doc, "(3) Prompt injection against clinical AI:",
        "OWASP LLM Top-10 attack patterns — instruction override, role manipulation, "
        "system-prompt extraction, and fake-authorisation claims — that could cause a "
        "clinical AI assistant to disclose records, override alarms, or prescribe without "
        "physician authorisation.")
    answer_bullet(doc, "(4) Exposed credentials in device telemetry:",
        "API tokens, bearer tokens, AWS access keys, Stripe live keys, and database "
        "connection strings embedded in medical device debug logs and gateway configuration "
        "files — typically invisible to traditional vulnerability scanners.")
    answer_bullet(doc, "(5) Weak medical IoT device identity:",
        "Missing device certificates, failed authentication states, and repeated login "
        "failures on medical IoT devices — undermining the Trust and Identity pillars of "
        "clinical infrastructure.")
    answer_bullet(doc, "(6) Absence of a post-quantum migration path:",
        "No tool maps these findings to NIST-standardised post-quantum algorithms "
        "(ML-KEM / FIPS 203, ML-DSA / FIPS 204, SLH-DSA / FIPS 205) and produces an "
        "executable, constraint-aware remediation roadmap.")
    answer_para(doc,
        "Existing tools — penetration testing platforms, classical vulnerability scanners, "
        "and data loss prevention suites — address only isolated fragments of this risk "
        "surface. None map findings to the TIPPSS framework or evaluate cryptographic "
        "posture against the 2024 NIST post-quantum standards. The operational bottleneck "
        "is unambiguous: hospital security teams currently have no way to produce a single, "
        "explainable readiness verdict and budget-aware remediation roadmap covering all six "
        "TIPPSS pillars in a single automated assessment."
    )

    add_hr(doc)

    # Q2
    q_block(doc, "Question 2", "Real-World Relevance and Impact",
        "(Explain why solving this problem matters right now. Quantify the risk, economic "
        "impact, or security exposure if this issue remains unaddressed.)")

    answer_para(doc,
        "This problem is operationally urgent for three converging and measurable reasons."
    )
    answer_para(doc,
        "First, harvest-now-decrypt-later (HNDL) attacks are already active. Adversaries "
        "are capturing today's encrypted clinical network traffic with the explicit intent "
        "of decrypting it when a cryptographically relevant quantum computer becomes "
        "available — a timeline security agencies estimate at 2030 to 2035. Healthcare "
        "records must remain confidential for 15 to 30 years under HIPAA and GDPR. Any "
        "data currently protected by RSA, ECDSA, or ECDH is therefore already at risk of "
        "future exposure, regardless of when the actual quantum device arrives."
    )
    answer_para(doc,
        "Second, regulatory mandates have been issued and deadlines are binding. The United "
        "States National Institute of Standards and Technology (NIST) has mandated federal "
        "post-quantum migration by 2035, with RSA and ECC deprecated for new federal systems "
        "after 2030 under NIST IR 8547. The NSA's CNSA 2.0 suite requires ML-KEM-1024 and "
        "ML-DSA-87 for national security systems. Hospitals serving Medicare, Veterans "
        "Affairs, and federally insured patients fall within the scope of these directives, "
        "yet the majority have no migration inventory, no readiness assessment, and no "
        "actionable roadmap."
    )
    answer_para(doc,
        "Third, the economic and patient-safety exposure is quantifiable and severe. IBM's "
        "2024 Cost of a Data Breach Report places the average healthcare breach at $9.77 "
        "million — the highest of any industry sector for fourteen consecutive years. The "
        "U.S. Department of Health and Human Services Office for Civil Rights recorded over "
        "725 healthcare breaches in 2023, exposing more than 133 million patient records. "
        "These figures represent only classically exploited breaches; the post-quantum "
        "exposure is additional and currently invisible in breach statistics. Compounded "
        "by rising prompt injection attacks targeting clinical AI assistants (OWASP LLM01) "
        "and insufficiently verified medical IoT device identity, hospitals that do not "
        "act now face simultaneous compliance failure, multi-million-dollar breach liability, "
        "patient-safety incidents from compromised clinical AI, and irreversible privacy "
        "loss once quantum-capable adversaries become operational."
    )

    add_hr(doc)

    # Q3
    q_block(doc, "Question 3", "Who Is Affected and How?",
        "(Identify your target stakeholders, victims, or users and detail the exact "
        "consequences they face.)")

    answer_para(doc,
        "Five distinct stakeholder groups face direct and measurable consequences from "
        "the unaddressed vulnerability described above."
    )
    answer_bullet(doc, "(1) Hospitals and integrated health systems:",
        "Face simultaneous HIPAA, GDPR, and emerging NIST PQC compliance failures; "
        "multi-million-dollar breach liability; ransomware-driven operational shutdowns "
        "that delay or cancel patient care; and potential loss of federal Medicare and "
        "Veterans Affairs contracts if PQ migration mandates are not met.")
    answer_bullet(doc, "(2) Patients:",
        "Are the most directly vulnerable group. Harvested clinical records will "
        "eventually expose sensitive diagnoses — HIV status, mental health treatment "
        "history, genomic data, substance-abuse records — enabling insurance "
        "discrimination, employment discrimination, and identity-theft cascades that "
        "follow patients for the remainder of their lives. This harm is permanent and "
        "irreversible once data has been captured.")
    answer_bullet(doc, "(3) Medical device manufacturers:",
        "Face product liability exposure under FDA cybersecurity guidance and forced "
        "firmware recalls if shipped devices incorporate quantum-vulnerable cryptographic "
        "libraries that cannot be updated to post-quantum standards within their "
        "operational lifetime.")
    answer_bullet(doc, "(4) Clinical AI assistant vendors:",
        "Face liability from prompt-injection attacks that cause PHI exfiltration, "
        "from unlogged PHI exposure in AI prompt logs, and from unsafe autonomous "
        "clinical outputs — amplified by the EU AI Act's high-risk AI classification "
        "for clinical decision support and FDA AI/ML Software as a Medical Device "
        "lifecycle guidance.")
    answer_bullet(doc, "(5) Health regulators (HHS OCR, FDA, CMS):",
        "Face systemic oversight failure if quantum-enabled breaches accelerate without "
        "an actionable, standardised assessment framework that healthcare organisations "
        "can use to demonstrate compliance.")
    answer_para(doc,
        "The cascading consequence of inaction is the erosion of public trust in "
        "healthcare AI and clinical IoT at precisely the moment when their clinical "
        "benefits are most needed — alongside permanent, large-scale privacy loss for "
        "hundreds of millions of patients whose encrypted data has already been captured "
        "by harvest-now adversaries."
    )

    add_hr(doc)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION B — SOLUTION
    # ════════════════════════════════════════════════════════════════════════
    section_box(doc, "SECTION B — SOLUTION")

    # Q1
    q_block(doc, "Question 1", "Overview of the Idea",
        "(Provide a high-level executive summary of your solution. What is it, how does "
        "it work conceptually, and what makes it unique?)")

    answer_para(doc,
        "TIPPSS SafeGuard-PQ is a sequential agentic cybersecurity assessment and "
        "migration planning platform that evaluates whether hospital clinical edge IoT "
        "systems and AI healthcare applications are post-quantum ready and aligned with "
        "the IEEE 2933-2024 TIPPSS framework."
    )
    answer_para(doc,
        "The platform operates through a ten-agent sequential pipeline coordinated by "
        "a purpose-built agentic orchestration framework. Each agent is a specialised, "
        "single-responsibility security module that receives the accumulated assessment "
        "state from all preceding agents and appends its findings to a shared result "
        "structure. The ten agents collectively scan TLS configurations, medical IoT "
        "network traffic, device certificate states, AI prompt logs, and device telemetry "
        "for the following threat categories:"
    )
    answer_bullet(doc, "Quantum-vulnerable cryptography:", "RSA, ECDSA, ECDH, deprecated TLS versions, and SHA-1 — all vulnerable to Shor's algorithm")
    answer_bullet(doc, "Protected health information (PHI) in AI systems:", "Patient names, MRNs, diagnoses, email addresses, and dates of birth in AI prompt logs")
    answer_bullet(doc, "Prompt injection attacks:", "OWASP LLM Top-10 patterns targeting clinical AI assistants")
    answer_bullet(doc, "Exposed credentials:", "API keys, AWS access keys, bearer tokens, and private keys in device telemetry")
    answer_bullet(doc, "Medical IoT device identity failures:", "Missing certificates, failed authentication, and repeated login anomalies")
    answer_bullet(doc, "Clinical AI safety risks:", "Autonomous dosing commands, alarm overrides, and unauthorised clinical actions")
    answer_para(doc,
        "Every detected finding is mapped to one or more of the six TIPPSS pillars — "
        "Trust, Identity, Privacy, Protection, Safety, and Security — and benchmarked "
        "against NIST-standardised post-quantum algorithms: ML-KEM (FIPS 203), ML-DSA "
        "(FIPS 204), and SLH-DSA (FIPS 205). The platform then produces a 0–100 "
        "Post-Quantum Risk Score, a six-pillar TIPPSS assessment, an overall verdict "
        "(Safe / Partially Safe / Not Post-Quantum Safe / Critical Quantum Risk), and "
        "a budget-constrained, downtime-aware migration roadmap generated by the novel "
        "Quantum-Inspired Remediation Optimizer (QIRO)."
    )
    callout(doc,
        "What makes this unique:  No existing healthcare cybersecurity tool simultaneously "
        "combines TIPPSS framework alignment, NIST FIPS 203/204/205 post-quantum benchmarking, "
        "AI prompt PHI and injection scanning, medical IoT device identity assessment, secret "
        "exposure detection, and constraint-aware QUBO-style optimisation into a single, "
        "explainable, automated pipeline."
    )

    add_hr(doc)

    # Q2
    q_block(doc, "Question 2", "Key Features",
        "(List the core functional components and capabilities that define your solution. "
        "Use a bulleted format to highlight the primary mechanisms of your system.)")

    answer_bullet(doc, "Ten-Agent Sequential Assessment Pipeline:",
        "Ten specialised security agents coordinated through a sequential agentic "
        "orchestration framework, providing auditability, transparent execution, and "
        "extensibility without requiring manual scripting.")
    answer_bullet(doc, "Post-Quantum Benchmark Engine (Agent 3):",
        "Detects quantum-vulnerable cryptography — RSA, ECC, ECDSA, ECDH, deprecated "
        "TLS versions — and benchmarks each finding against NIST-finalised post-quantum "
        "standards: ML-KEM (FIPS 203), ML-DSA (FIPS 204), and SLH-DSA (FIPS 205). "
        "Applies the harvest-now-decrypt-later rule: long data lifetimes combined with "
        "classical crypto generate Critical findings.")
    answer_bullet(doc, "IEEE 2933-2024 TIPPSS Mapping Layer (Agent 8):",
        "Every detected issue is categorised under Trust, Identity, Privacy, Protection, "
        "Safety, and Security, with per-pillar weighted risk scoring and a composite "
        "0–100 Post-Quantum Risk Score.")
    answer_bullet(doc, "Clinical Privacy Agent — PHI Detection (Agent 5):",
        "Detects protected health information leakage in AI prompt logs using "
        "pattern-matching across medical record numbers, full patient names, sensitive "
        "diagnoses (HIV, cancer, mental health), SSN formats, and email addresses. "
        "Evaluated using Synthea synthetic EHR records (MITRE, Apache 2.0).")
    answer_bullet(doc, "Prompt Injection Detection (Agent 5):",
        "Identifies OWASP LLM Top-10 attack patterns targeting clinical AI assistants: "
        "instruction override ('Ignore all previous instructions'), role manipulation, "
        "system-prompt extraction, jailbreaks, and fake-authorisation data-exfiltration "
        "commands.")
    answer_bullet(doc, "Medical IoT Device Identity Verification (Agent 4):",
        "Validates edge-device certificate presence, authentication state, and failed "
        "login counts for medical IoT devices — ECG monitors, infusion pumps, SpO2 "
        "sensors, patient wearables, and hospital edge gateways — evaluated using the "
        "CICIoMT2024 medical IoT traffic dataset (University of New Brunswick).")
    answer_bullet(doc, "Secret Exposure Scanner (Agent 6):",
        "Detects leaked API tokens, AWS access key IDs, Stripe live keys, GitHub "
        "personal access tokens, bearer tokens, and database connection strings "
        "embedded in device logs and configuration telemetry.")
    answer_bullet(doc, "Clinical Safety Risk Agent (Agent 7):",
        "Flags AI-generated outputs that could trigger unsafe clinical actions: "
        "autonomous medication dosing without physician sign-off, infusion pump alarm "
        "overrides, unauthorised PHI disclosure, and autonomous clinical procedures.")
    answer_bullet(doc, "Explainable Risk Scoring Engine (Agent 8):",
        "Produces a 0–100 Post-Quantum Risk Score and six-pillar TIPPSS score using "
        "a transparent weighted formula, classifying systems as Safe (0–25), Partially "
        "Safe (26–50), Not Post-Quantum Safe (51–75), or Critical Quantum Risk (76–100).")
    answer_bullet(doc, "QIRO — Quantum-Inspired Remediation Optimizer (Agent 10):",
        "Novel QUBO-style constrained binary optimisation. Converts every finding into "
        "a candidate remediation action with benefit score Bᵢ = Rᵢ + Pᵢ + Sᵢ + Tᵢ, "
        "cost, and downtime. Selects the maximum-benefit feasible portfolio under the "
        "hospital's available budget and allowed service downtime. Solved by Simulated "
        "Annealing with geometric cooling (α = 0.995), producing selected actions, "
        "deferred actions with reasons, and a three-phase migration roadmap "
        "(0–6 months / 6–18 months / 18–36 months).")
    answer_bullet(doc, "Interactive Streamlit Dashboard:",
        "Seven pre-built clinical simulation scenarios (ICU gateway to fully PQ-safe "
        "edge gateway); file upload for CICIoMT2024 network traffic and Synthea patient "
        "records; budget and downtime constraint sliders; live TIPPSS six-pillar spider "
        "chart; PQ risk gauge; QIRO selected and deferred action tables; Claude AI "
        "executive report.")
    answer_bullet(doc, "Automated Output Persistence:",
        "Every assessment run saved with a unique timestamp as payload JSON, result "
        "JSON, and summary CSV in the fileuploadoutput/ directory. Combined run summary "
        "generated automatically.")

    add_hr(doc)

    # Q3
    q_block(doc, "Question 3", "How It Addresses the Problem",
        "(Explicitly map your solution's features back to the problem statement. Explain "
        "the direct causal link between your technology and the mitigation of the problem.)")

    answer_para(doc,
        "Each component of TIPPSS SafeGuard-PQ maps directly and causally to a specific "
        "gap identified in the problem statement."
    )
    answer_bullet(doc, "(1) Quantum-vulnerable cryptography →",
        "Agents 2 and 3 (Cryptographic Classifier and PQ Benchmark) parse TLS "
        "configurations and device certificates, classify each parameter as post-quantum "
        "safe, classical, or deprecated, and compare findings against NIST ML-KEM, "
        "ML-DSA, and SLH-DSA standards. This closes the gap of having no automated "
        "PQ readiness inventory for clinical infrastructure.")
    answer_bullet(doc, "(2) PHI and PII leakage in AI systems →",
        "Agent 5 (AI Prompt Privacy) scans all AI prompt logs for patient identifiers, "
        "diagnoses, MRNs, and protected health information using rule-based pattern "
        "detection validated against Synthea synthetic EHR records. This directly "
        "addresses the regulatory gap where AI prompt governance is absent from "
        "existing clinical security audits.")
    answer_bullet(doc, "(3) Prompt injection against clinical AI →",
        "Agent 5 also detects OWASP LLM Top-10 attack patterns across all prompt log "
        "entries, identifying instruction-override and data-exfiltration attempts that "
        "traditional vulnerability scanners cannot detect.")
    answer_bullet(doc, "(4) Exposed credentials in device telemetry →",
        "Agent 6 (Secret Exposure Scanner) applies credential-pattern detection to "
        "device_log entries, including optional debug log fields that medical device "
        "manufacturers routinely populate during operational diagnostics.")
    answer_bullet(doc, "(5) Weak medical IoT device identity →",
        "Agent 4 (IoT Device Identity) evaluates certificate presence, authentication "
        "state, and failed login counts for every device in the assessment payload, "
        "using CICIoMT2024 traffic profiles from six attack classes as evaluation "
        "benchmarks.")
    answer_bullet(doc, "(6) No post-quantum migration path →",
        "QIRO (Agent 10) closes the most critical operational gap: converting a list "
        "of findings into an executable, budget-constrained, downtime-aware migration "
        "roadmap. Rather than producing an infeasible list of all required fixes, QIRO "
        "selects the maximum-benefit feasible subset and explicitly defers the remainder "
        "with stated reasons — giving hospital security teams an immediately actionable "
        "plan within their real operational constraints.")
    answer_para(doc,
        "The TIPPSS Scoring Engine (Agent 8) closes the framework gap by mapping every "
        "finding to one or more of the six IEEE 2933-2024 pillars, producing a unified "
        "six-pillar score and composite risk verdict that provides a complete and "
        "explainable assessment no existing tool delivers."
    )

    add_hr(doc)

    # Q4
    q_block(doc, "Question 4", "Working Prototype Repository Link",
        "(Provide the GitHub repository link to the working prototype.)")

    callout(doc,
        "Repository:  https://github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS\n\n"
        "The repository contains the complete working implementation including:\n"
        "  •  dashboard.py — Streamlit frontend (7 scenarios, file upload, QIRO visualisation)\n"
        "  •  01_n8n_file/TIPPSS_SafeGuard_PQ_Sequential_v3.json — importable workflow\n"
        "  •  00_input_files/ — CICIoMT2024 network traffic datasets\n"
        "  •  run_file_upload_tests.py — automated 8-file test runner\n"
        "  •  fileuploadoutput/ — timestamped results from 8/8 live test runs\n"
        "  •  run_tests.py — 8-case unit test suite (TC01–TC08)\n"
        "  •  README.md — full documentation with Mermaid architecture diagrams",
        bg="E2EFDA"
    )

    add_hr(doc)

    # Q5
    q_block(doc, "Question 5", "User Experience (UX) and Human Factors",
        "(Describe the user interface or operational experience for the administrators or "
        "end-users interacting with your system. How does the design minimize human "
        "configuration errors?)")

    answer_para(doc,
        "TIPPSS SafeGuard-PQ is designed for three primary clinical security user "
        "personas — hospital security analysts, IT administrators, and compliance "
        "officers — with deliberate UX choices throughout to minimise configuration "
        "errors and reduce the domain knowledge required for effective operation."
    )
    answer_para(doc, "The platform exposes three interaction surfaces:")
    answer_bullet(doc, "Streamlit Web Dashboard (primary interface):",
        "Presents a three-step workflow in the sidebar: (1) select a clinical system "
        "simulation from a pre-built dropdown of seven scenarios or upload a real "
        "CICIoMT2024 / Synthea file; (2) set remediation constraints — budget and "
        "allowed downtime — via clearly labelled sliders with explanatory help text; "
        "(3) click a single 'Run Cybersecurity Simulation' button. The main content "
        "area renders a colour-coded verdict card, a PQ Risk Score gauge (0–100), a "
        "TIPPSS six-pillar spider chart, a severity-banded findings table, and the "
        "QIRO migration roadmap with selected and deferred action tables.")
    answer_bullet(doc, "Agentic Workflow Editor (advanced / audit interface):",
        "The sequential agentic framework provides a visual representation of the "
        "ten-agent pipeline where each agent appears as a labelled node with "
        "inspectable inputs and outputs. This allows security engineers and compliance "
        "auditors to verify exactly what each agent checked, what data it received, "
        "and what findings it produced — eliminating the opaque rule-engine pattern "
        "of traditional vulnerability scanners.")
    answer_bullet(doc, "Automated Output Layer:",
        "Every assessment run produces a timestamped payload JSON, result JSON, and "
        "summary CSV — providing a reproducible audit trail suitable for compliance "
        "reporting without any manual export steps.")
    answer_para(doc, "Human-factor safeguards built into the design include:")
    answer_bullet(doc, "State-clearing on scenario change:",
        "Changing the scenario dropdown immediately clears previous results from the "
        "session, preventing stale risk verdicts from being misread as current.")
    answer_bullet(doc, "Constraint-change warning:",
        "If the budget or downtime slider is adjusted after a result is displayed, a "
        "yellow warning banner appears: 'Inputs changed — click Run to recompute the "
        "QIRO plan.' This prevents users from acting on an outdated migration roadmap.")
    answer_bullet(doc, "Scenario validation with warnings:",
        "The dashboard validates every loaded scenario against required field schema "
        "before display, with a sidebar expander showing any ignored entries and why.")
    answer_bullet(doc, "Pre-built scenario library:",
        "Seven clinically realistic scenarios eliminate the need for manual payload "
        "authoring, covering the complete risk spectrum from fully PQ-safe to "
        "worst-case TLS 1.0 with SHA-1 and 20-year data lifetime.")
    answer_bullet(doc, "Explainable findings:",
        "Every finding includes severity level, the TIPPSS pillar it maps to, a "
        "plain-English detail field, and a specific recommended remediation step — "
        "designed to be actionable by clinical IT staff without specialised "
        "cryptographic expertise.")
    answer_bullet(doc, "Synthetic-data-only operation:",
        "The platform operates exclusively on synthetic and publicly available datasets "
        "(Synthea, CICIoMT2024), eliminating the risk of accidental real PHI exposure "
        "during assessment or demonstration.")
    answer_bullet(doc, "QIRO constraint display:",
        "The QIRO section shows applied budget and downtime constraints, budget "
        "remaining after selected actions, downtime remaining, and a progress bar for "
        "each — providing immediate visual confirmation that the plan respects "
        "operational limits.")

    add_hr(doc)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION C — IMPLEMENTATION
    # ════════════════════════════════════════════════════════════════════════
    section_box(doc, "SECTION C — IMPLEMENTATION")

    # Q1
    q_block(doc, "Question 1", "Technologies Required",
        "(Detail the complete technical stack needed to build, deploy, and run your solution.)")

    answer_para(doc, "The platform is built entirely on open-source technologies with no commercial licence requirements.")

    # Tech table
    th = ["Layer", "Technology", "Version", "Purpose"]
    ttbl = doc.add_table(rows=1, cols=4)
    ttbl.style = "Table Grid"
    ttbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    row0 = ttbl.rows[0]
    for i, h in enumerate(th):
        cell = row0.cells[i]
        set_cell_bg(cell, "1F3864")
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.bold = True; r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)

    tech_rows = [
        ("Frontend",       "Streamlit",                    "1.35+",    "Interactive web dashboard — scenario selector, file uploader, constraint sliders, result charts"),
        ("Visualisation",  "Plotly",                       "5.x",      "TIPPSS six-pillar spider chart, PQ risk gauge, QIRO risk-reduction bar chart"),
        ("Backend Logic",  "Python",                       "3.10+",    "Rule engines, parsers, feature extraction, scoring logic, test runners"),
        ("Data Processing","pandas",                       "2.x",      "CSV file sampling, network feature extraction, output CSV generation"),
        ("Pattern Matching","re (regex)",                  "stdlib",   "PHI detection, secret exposure scanning, prompt injection identification"),
        ("Agentic Orchestration","Sequential Agentic Framework","v3.0", "Ten-agent pipeline orchestration — each agent is a single-responsibility code module"),
        ("AI Report Layer","Anthropic Claude API",          "Sonnet",   "Natural-language executive summary generation from top findings"),
        ("HTTP Client",    "requests",                     "2.x",      "Dashboard-to-pipeline communication (HTTP POST / JSON)"),
        ("Word Generation","python-docx",                  "1.2",      "Professional document generation for assessment reports"),
        ("Containerisation","Docker",                      "Latest",   "Self-hosted pipeline deployment"),
        ("Source Control", "GitHub",                       "—",        "Version control, CI, documentation hosting"),
        ("Output Storage", "JSON + CSV (filesystem)",      "—",        "Timestamped per-run results in fileuploadoutput/"),
        ("Standards Ref.", "NIST FIPS 203/204/205",        "2024",     "Post-quantum algorithm benchmark targets"),
        ("Framework Ref.", "IEEE 2933-2024",               "2024",     "TIPPSS six-pillar clinical IoT security mapping"),
    ]
    alt = False
    for tr_data in tech_rows:
        row = ttbl.add_row()
        for i, text in enumerate(tr_data):
            cell = row.cells[i]
            if alt:
                set_cell_bg(cell, "EBF3FB")
            p = cell.paragraphs[0]
            p.paragraph_format.space_after  = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            r = p.add_run(text)
            r.font.size = Pt(9)
        alt = not alt

    cap_t = doc.add_paragraph("Table: Complete technology stack.")
    cap_t.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for r in cap_t.runs:
        r.italic = True; r.font.size = Pt(9)

    add_hr(doc)

    # Q2
    q_block(doc, "Question 2", "Dependencies",
        "(Identify any external systems, third-party APIs, data feeds, or open-source "
        "infrastructure your solution relies upon to function.)")

    answer_para(doc, "All dependencies are freely available for academic and research use. The platform requires no real patient data and no live hospital network access.")

    answer_bullet(doc, "CICIoMT2024 dataset (University of New Brunswick / Canadian Institute for Cybersecurity):",
        "Medical IoT network traffic captures covering six attack classes — ARP spoofing, "
        "MQTT malformed data, TCP SYN DoS, TCP DDoS, reconnaissance port scanning — "
        "and a benign baseline. Free for academic use with citation. Used for device "
        "identity assessment and IoT attack-pattern evaluation.")
    answer_bullet(doc, "Synthea synthetic patient data (MITRE Corporation, Apache 2.0):",
        "Realistic but entirely synthetic patient records including names, MRNs, dates "
        "of birth, diagnoses, and clinical conditions. No privacy restrictions. Used "
        "to simulate PHI exposure in AI prompt logs and test the privacy detection "
        "agents without involving real patient data.")
    answer_bullet(doc, "NIST FIPS 203, 204, 205 (2024):",
        "The three finalized post-quantum cryptography standards — ML-KEM, ML-DSA, and "
        "SLH-DSA — serve as the benchmark targets for the PQ compliance assessment. "
        "Publicly available, no licence required.")
    answer_bullet(doc, "NIST IR 8547 — PQC Migration Guidance:",
        "U.S. federal transition guidance specifying the deprecation timeline for RSA "
        "and ECC and the adoption requirements for post-quantum algorithms in federal "
        "and federally regulated systems.")
    answer_bullet(doc, "OWASP LLM Top-10:",
        "Reference taxonomy for large language model attack patterns, used by Agent 5 "
        "to define and detect prompt injection patterns in clinical AI prompt logs.")
    answer_bullet(doc, "IEEE 2933-2024 TIPPSS Standard:",
        "The Trust, Identity, Privacy, Protection, Safety, Security framework for "
        "Clinical IoT interoperability and security. Used as the primary assessment "
        "and scoring framework for all detected findings.")
    answer_bullet(doc, "Anthropic Claude API (optional, Agent 9 only):",
        "Invoked by Agent 9 to generate plain-English executive summaries of the "
        "highest-severity findings. The remaining nine agents operate without any "
        "external API dependency; Claude is the only blocking optional dependency.")
    answer_bullet(doc, "Python open-source ecosystem:",
        "pandas, requests, plotly, streamlit, python-docx, pathlib — all MIT or "
        "BSD-licensed, no commercial software required.")

    add_hr(doc)

    # Q3
    q_block(doc, "Question 3", "Expected Challenges",
        "(Honestly assess the primary technical, operational, or deployment hurdles you "
        "anticipate during development, and briefly note how you plan to overcome them.)")

    numbered(doc,
        "Scope management across ten agents.  "
        "Coordinating ten specialised agents with consistent data contracts across the "
        "sequential pipeline requires rigorous schema discipline. Mitigation: a strict "
        "payload schema (validated by Agent 1) and a shared findings[] array pattern "
        "ensure each agent can operate independently while maintaining pipeline integrity. "
        "The five highest-priority agents (Crypto Classifier, PQ Benchmark, AI Prompt "
        "Privacy, IoT Device Identity, TIPPSS Scorer) were implemented and validated "
        "first; the remaining five were layered on top."
    )
    numbered(doc,
        "Dataset limitations for cryptographic assessment.  "
        "The CICIoMT2024 dataset captures network-layer packet features rather than "
        "TLS handshake details or certificate contents. Mitigation: seven hand-crafted "
        "TLS configuration simulation scenarios covering the full risk spectrum — from "
        "fully PQ-safe (ML-KEM-1024 / ML-DSA-87 / TLS 1.3) to worst-case deprecated "
        "(TLS 1.0 / SHA-1 / RSA / 20-year data lifetime) — serve as the primary input "
        "for cryptographic detection. CICIoMT2024 is used for device identity and "
        "attack-pattern demonstration."
    )
    numbered(doc,
        "Post-quantum library maturity.  "
        "Production-grade ML-KEM and ML-DSA implementations are still maturing across "
        "language ecosystems. Mitigation: the platform benchmarks systems against PQ "
        "standards and generates migration recommendations rather than implementing "
        "post-quantum cryptography itself, eliminating library-maturity risk from the "
        "critical path entirely."
    )
    numbered(doc,
        "QIRO scoring weight validation.  "
        "The benefit score components (Rᵢ risk reduction, Pᵢ PQ urgency, Sᵢ safety "
        "criticality, Tᵢ TIPPSS impact) are currently calibrated using informed "
        "heuristic defaults derived from the NIST and IEEE standards rather than "
        "empirically validated clinical deployment data. Mitigation: the scoring "
        "formula is fully transparent and documented; the weights are framed as a "
        "configurable starting baseline and proposed calibration against real hospital "
        "security team data as a Phase 2 research direction."
    )
    numbered(doc,
        "Orchestration framework resilience.  "
        "The sequential agentic framework is the operational spine of the pipeline; "
        "any instability in the framework layer affects the entire assessment flow. "
        "Mitigation: the Python test runners (run_tests.py, run_file_upload_tests.py) "
        "provide a fully independent, CLI-based fallback that exposes identical agent "
        "functionality and saves identical output without depending on the orchestration "
        "layer. This has been validated across 8/8 live integration tests."
    )
    numbered(doc,
        "Synthetic-versus-real hospital gap.  "
        "Synthetic data and structured test cases may not capture the full complexity "
        "of a real hospital's heterogeneous device estate, legacy EHR integrations, "
        "and operational network topology. Mitigation: the platform is architected as "
        "a benchmark framework demonstrating the approach and methodology; real-hospital "
        "validation, with institution-approved de-identified configuration data, is "
        "proposed as the primary Phase 2 deliverable."
    )
    numbered(doc,
        "Demonstration reproducibility.  "
        "Demonstrations of live pipeline assessments must be reliable under operational "
        "conditions. Mitigation: a 'demo mode' runs the pipeline deterministically on "
        "pre-loaded simulation scenarios with known expected outputs; the automated "
        "test suite (8/8 pass confirmed) provides independent verification of pipeline "
        "correctness independent of any live demonstration."
    )

    add_hr(doc)

    # footer
    fp = doc.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run(
        "TIPPSS SafeGuard-PQ  ·  Standards: NIST FIPS 203/204/205 · IEEE 2933-2024 TIPPSS  ·  "
        "https://github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS"
    )
    fr.italic = True
    fr.font.size = Pt(9)
    fr.font.color.rgb = RGBColor.from_string("7F7F7F")

    doc.save(path)
    print(f"  Saved: {path.name}")


if __name__ == "__main__":
    out = OUT_DIR / "TIPPSS_SafeGuard_PQ_QA_Response.docx"
    print("\nGenerating Q&A response document ...\n")
    build(out)
    print(f"\nDone. Saved to 00_Documention/{out.name}")
