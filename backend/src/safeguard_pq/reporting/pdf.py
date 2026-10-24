"""PDF reports (ReportLab): single assessment and fleet summary."""

from __future__ import annotations

import io
import re
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .. import __version__
from ..domain.models import AssessmentResult

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#475569")
LINE = colors.HexColor("#cbd5e1")
HEAD_BG = colors.HexColor("#e2e8f0")
STATUS_COLORS = {"SAFE": colors.HexColor("#15803d"), "AT_RISK": colors.HexColor("#b45309"), "UNSAFE": colors.HexColor("#b91c1c")}
SEV_COLORS = {"critical": "#b91c1c", "high": "#c2410c", "medium": "#a16207", "low": "#4d7c0f", "info": "#475569"}

_CHAR_MAP = {"→": "->", "≤": "<=", "≥": ">=", "…": "...", "×": "x", "−": "-", "✓": "OK", "•": "-", "≈": "~", "’": "'", "“": '"', "”": '"'}

DISCLAIMER = ("Research prototype output (TIPPSS SafeGuard-PQ v{v}). Findings come from transparent rule-based heuristics; "
              "remediation costs and downtimes are illustrative placeholders. This is not a certified security assessment, "
              "not a compliance attestation, and must not be used for clinical decision-making.")


def _t(text: Any) -> str:
    s = "" if text is None else str(text)
    for k, v in _CHAR_MAP.items():
        s = s.replace(k, v)
    s = s.encode("cp1252", errors="replace").decode("cp1252")
    return escape(s)


def _styles() -> dict[str, ParagraphStyle]:
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=7.5, leading=9.5, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base, fontSize=7.8, leading=9.6),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=4),
        "banner": ParagraphStyle("banner", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=19,
                                 textColor=colors.white, alignment=TA_CENTER),
        "banner_sub": ParagraphStyle("banner_sub", parent=base, fontSize=9.5, textColor=colors.white, alignment=TA_CENTER),
    }


def _table(rows: list[list[Any]], widths: list[float], st: dict[str, ParagraphStyle], header: bool = True) -> Table:
    data = [[c if not isinstance(c, str) else Paragraph(c, st["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), HEAD_BG)]
    t.setStyle(TableStyle(style))
    return t


def _b(s: str) -> str:
    return f"<b>{s}</b>"


def _sev(sev: str) -> str:
    return f'<font color="{SEV_COLORS.get(sev, "#475569")}"><b>{_t(sev.upper())}</b></font>'


def _banner(status: str, title: str, subtitle: str, st: dict[str, ParagraphStyle], width: float) -> Table:
    t = Table([[Paragraph(_t(title), st["banner"])], [Paragraph(_t(subtitle), st["banner_sub"])]], colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), STATUS_COLORS.get(status, MUTED)),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def _footer(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, f"TIPPSS SafeGuard-PQ v{__version__} - research prototype - not a certified assessment")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _markdown(md: str, st: dict[str, ParagraphStyle]) -> list[Any]:
    out: list[Any] = []
    for line in md.splitlines():
        line = line.rstrip()
        if not line:
            out.append(Spacer(1, 3))
            continue
        heading = re.match(r"^#{1,4}\s+(.*)", line)
        text = _t(heading.group(1) if heading else re.sub(r"^\s*[-*]\s+", "- ", line))
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
        text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
        out.append(Paragraph(f"<b>{text}</b>" if heading else text, st["base"]))
    return out


def build_assessment_pdf(result: AssessmentResult) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"SafeGuard-PQ assessment {result.system_id}", author="TIPPSS SafeGuard-PQ",
                            subject="Post-quantum and TIPPSS security assessment")
    W = doc.width
    r = result
    q = r.qiro_optimization
    posture = r.pq_posture
    ex = r.explanation
    safe = r.environment_status == "SAFE"
    story: list[Any] = [
        Paragraph("TIPPSS SafeGuard-PQ - Security Assessment Report", st["h1"]),
        Paragraph(_t(f"System {r.system_id} | domain {r.domain} | assessment {r.assessment_id} | {r.timestamp}"), st["small"]),
        Spacer(1, 6),
        _banner(r.environment_status,
                f"ENVIRONMENT STATUS: {r.environment_status.replace('_', ' ')}",
                f"Is the environment safe? {'YES' if safe else 'NO'} - {'; '.join(r.environment_reasons)}", st, W),
        Spacer(1, 8),
        _table([
            ["PQ risk score", "PQ verdict", "PQ readiness", "Findings", "Plan (QIRO)"],
            [_b(f"{r.pq_risk_score}/100"), _t(r.verdict), _t(posture.get("readiness", "Unknown")), _b(str(r.findings_count)),
             _t(f"{q.get('selection_count', 0)} actions, ${q.get('total_cost_usd', 0):,.0f}, {q.get('total_downtime_hrs', 0):g}h")],
        ], [W * 0.17, W * 0.22, W * 0.2, W * 0.13, W * 0.28], st),
    ]
    if r.metadata.get("scenario_summary"):
        story += [Spacer(1, 5), Paragraph(_t(r.metadata["scenario_summary"]), st["base"])]

    story.append(Paragraph("1. Explanation summary", st["h2"]))
    story += [Paragraph(_t(f"- {s}"), st["base"]) for s in ex.get("summary", [])]
    story.append(Paragraph(_t(ex.get("method", "")), st["small"]))

    story.append(Paragraph("2. Post-quantum identification", st["h2"]))
    if r.crypto_inventory:
        rows = [["Field", "Value", "Quantum status", "Threat", "Recommended replacement"]]
        for e in r.crypto_inventory:
            rows.append([_t(e["field"]), _t(e["value"]), _t(e["quantum_status"]), _t(e.get("quantum_attack") or "-"),
                         _t(e.get("replacement") or "-")])
        story.append(_table(rows, [W * 0.17, W * 0.18, W * 0.2, W * 0.15, W * 0.30], st))
    else:
        story.append(Paragraph("No cryptographic configuration supplied - PQ posture unverified.", st["base"]))
    story.append(Paragraph(_t(f"Readiness: {posture.get('readiness')} - {posture.get('readiness_reason', '')}"), st["base"]))
    if (m := posture.get("mosca")):
        story.append(Paragraph(_t(
            f"Mosca's inequality (assumptions): data lifetime x={m['x_data_lifetime_years']:g}y + migration y={m['y_migration_years']:g}y "
            f"vs years-to-CRQC z={m['z_years_to_crqc']:g}y -> {'AT RISK' if m['at_risk'] else 'within margin'}. {m['note']}"), st["base"]))
    for adv in posture.get("advisories", []):
        story.append(Paragraph(_t(f"- {adv}"), st["base"]))
    if posture.get("transition_reference"):
        story.append(Paragraph(_t(posture["transition_reference"]), st["small"]))

    story.append(Paragraph("3. TIPPSS pillars (IEEE 2933-2024) and score attribution", st["h2"]))
    prow = [["Pillar", "Score", "Findings"]] + [
        [_t(k), _b(str(v["score"])), _t(", ".join(v["finding_ids"]) or "-")] for k, v in r.tippss_scores.items()]
    arow = [["Score category", "Value x weight", "Points", "Share"]] + [
        [_t(a["label"]), _t(f"{a['value']:g} x {a['weight']:.2f}"), _b(f"{a['contribution']:g}"), _t(f"{a['share_pct']:g}%")]
        for a in ex.get("score_attribution", [])]
    story.append(Table([[_table(prow, [W * 0.13, W * 0.08, W * 0.19], st),
                         _table(arow, [W * 0.25, W * 0.12, W * 0.08, W * 0.07], st)]], colWidths=[W * 0.42, W * 0.58],
                       style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(Paragraph(_t(f"Raw score {ex.get('raw_score')} rounded to {r.pq_risk_score}. Attribution is an exact decomposition "
                              "of the additive scoring model."), st["small"]))

    story.append(Paragraph("4. Findings and evidence", st["h2"]))
    if r.findings:
        rows = [["ID", "Agent", "Severity", "Finding", "Evidence (redacted)"]]
        for f in r.findings:
            ev = "<br/>".join(_t(f"{e.source}: {e.observed or ''} [{e.rule}]") for e in f.evidence[:2]) or "-"
            rows.append([_t(f.id), _t(f.agent), _sev(f.severity), _t(f"{f.type}: {f.detail}"), ev])
        story.append(_table(rows, [W * 0.06, W * 0.15, W * 0.1, W * 0.32, W * 0.37], st))
    else:
        story.append(Paragraph("No findings for the evaluated controls.", st["base"]))

    story.append(Paragraph("5. Remediation plan (QIRO)", st["h2"]))
    story.append(Paragraph(_t(q.get("constraint_explanation", "")), st["base"]))
    if q.get("selected_actions"):
        rows = [["#", "Action", "Addresses", "Cost", "Downtime", "Why selected"]]
        for a in q["selected_actions"]:
            rows.append([_t(a["priority_rank"]), _t(a["remediation"]), _t(f"{a['finding_id']} {a['finding_type']}"),
                         _t(f"${a['cost_usd']:,.0f}"), _t(f"{a['downtime_hrs']:g}h"), _t(a["selection_reason"])])
        story.append(_table(rows, [W * 0.04, W * 0.3, W * 0.17, W * 0.1, W * 0.09, W * 0.3], st))
    if q.get("excluded_actions"):
        story.append(Spacer(1, 4))
        rows = [["Deferred action", "Cost", "Reason"]] + [
            [_t(a["remediation"]), _t(f"${a['cost_usd']:,.0f}"), _t(a["reason"])] for a in q["excluded_actions"]]
        story.append(_table(rows, [W * 0.42, W * 0.1, W * 0.48], st))
    if (o := q.get("optimality")):
        story.append(Paragraph(_t(f"Optimizer: {q.get('algorithm')}; seed {q.get('seed')}; objective {o['heuristic_objective']:g}; "
                                  f"exact optimum {o['exact_objective'] if o['exact_objective'] is not None else 'n/a'}; "
                                  f"gap {o['gap_pct'] if o['gap_pct'] is not None else 'n/a'}%."), st["small"]))
    story.append(Paragraph("Costs and downtimes are illustrative placeholders, not market data.", st["small"]))

    cfs = ex.get("counterfactuals", [])[:8]
    if cfs:
        story.append(KeepTogether([
            Paragraph("6. Counterfactuals (what if this were fixed?)", st["h2"]),
            _table([["Scenario", "PQ score", "Status after", "Weakest pillar after"]] + [
                [_t(c["scenario"]), _t(f"{c['before']['pq_risk_score']} -> {c['after']['pq_risk_score']}"),
                 _t(c["after"]["environment_status"]), _t(f"{c['after']['weakest_pillar']} {c['after']['weakest_pillar_score']}")]
                for c in cfs] + [[_b("Apply QIRO plan"),
                                  _t(f"{ex['plan_projection']['before']['pq_risk_score']} -> {ex['plan_projection']['after']['pq_risk_score']}"),
                                  _b(ex["plan_projection"]["after"]["environment_status"]),
                                  _t(f"{ex['plan_projection']['after']['weakest_pillar']} {ex['plan_projection']['after']['weakest_pillar_score']}")]],
                [W * 0.45, W * 0.15, W * 0.17, W * 0.23], st),
        ]))

    story.append(Paragraph("7. Agent trace", st["h2"]))
    rows = [["Agent", "Status", "Time (ms)", "Tool calls", "Findings", "Reasoning (last note)"]]
    for t in r.trace:
        rows.append([_t(t.title), _t(t.status), _t(f"{t.duration_ms:.2f}"), _t(len(t.tool_calls)), _t(len(t.finding_ids)),
                     _t(t.notes[-1] if t.notes else "")])
    story.append(_table(rows, [W * 0.2, W * 0.1, W * 0.09, W * 0.08, W * 0.08, W * 0.45], st))

    story += [PageBreak(), Paragraph("8. Narrative report", st["h2"]),
              Paragraph(_t(f"Generator: {r.report.get('generator')}" + (f" ({r.report.get('llm_provider')}, {r.report.get('llm_model')})"
                           if r.report.get("llm_provider") else "")), st["small"])]
    story += _markdown(r.report.get("markdown", ""), st)

    story += [Paragraph("9. Reproducibility and limitations", st["h2"]),
              Paragraph(_t(f"Software version {r.version}; optimizer seed {r.metadata.get('seed')}; disabled agents: "
                           f"{', '.join(r.metadata.get('disabled_agents') or []) or 'none'}; inputs: "
                           f"{', '.join(r.metadata.get('input_types_detected') or [])}."), st["base"]),
              Spacer(1, 4), Paragraph(_t(DISCLAIMER.format(v=r.version)), st["small"])]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def build_fleet_pdf(fleet: dict[str, Any]) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"SafeGuard-PQ fleet report {fleet['simulation_id']}", author="TIPPSS SafeGuard-PQ")
    W = doc.width
    status = fleet["environment_status"]
    q = fleet["fleet_plan"]
    story: list[Any] = [
        Paragraph("TIPPSS SafeGuard-PQ - Fleet Security Report", st["h1"]),
        Paragraph(_t(f"{fleet['template_label']} | simulation {fleet['simulation_id']} | tick {fleet['tick']} | "
                     f"{fleet['data_source']} telemetry | {fleet['timestamp']}"), st["small"]),
        Spacer(1, 6),
        _banner(status, f"FLEET STATUS: {status.replace('_', ' ')}",
                f"Is the environment safe? {'YES' if status == 'SAFE' else 'NO'} - {fleet['counts']['UNSAFE']} unsafe, "
                f"{fleet['counts']['AT_RISK']} at risk, {fleet['counts']['SAFE']} safe of {len(fleet['devices'])} devices", st, W),
        Spacer(1, 8),
        Paragraph("Devices", st["h2"]),
    ]
    rows = [["Device", "Type", "Status", "PQ score", "PQ readiness", "Findings", "Top issues"]]
    for d in fleet["devices"]:
        rows.append([_t(d["device_id"]), _t(d["label"]), _t(d["environment_status"]), _b(str(d["pq_risk_score"])),
                     _t(d["pq_readiness"]), _t(d["findings_count"]), _t(", ".join(d["top_issues"]) or "-")])
    story.append(_table(rows, [W * 0.15, W * 0.17, W * 0.1, W * 0.08, W * 0.13, W * 0.08, W * 0.29], st))
    story.append(Paragraph("Weakest TIPPSS pillar scores across the fleet", st["h2"]))
    story.append(_table([list(fleet["fleet_pillars"].keys()), [_b(str(v)) for v in fleet["fleet_pillars"].values()]],
                        [W / 6] * 6, st))
    story.append(Paragraph("Fleet remediation plan (QIRO, shared budget)", st["h2"]))
    story.append(Paragraph(_t(q.get("constraint_explanation", "")), st["base"]))
    if q.get("selected_actions"):
        rows = [["#", "Device", "Action", "Cost", "Downtime"]] + [
            [_t(a["priority_rank"]), _t(a.get("device_id") or "-"), _t(a["remediation"]), _t(f"${a['cost_usd']:,.0f}"),
             _t(f"{a['downtime_hrs']:g}h")] for a in q["selected_actions"][:40]]
        story.append(_table(rows, [W * 0.05, W * 0.17, W * 0.56, W * 0.11, W * 0.11], st))
    if q.get("excluded_count"):
        story.append(Paragraph(_t(f"{q['excluded_count']} action(s) deferred under the shared budget/downtime constraints."), st["base"]))
    story += [Spacer(1, 6), Paragraph(_t(DISCLAIMER.format(v=__version__)), st["small"])]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
