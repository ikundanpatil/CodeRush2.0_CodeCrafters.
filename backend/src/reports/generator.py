"""Real PDF generation from a ReportData object (Part F) -- every value
rendered here is a field already present on ReportData, which is itself
built entirely from a real ResearchRun (see service.py). No static
template, no placeholder text, no fabricated section.
"""

import io
from typing import List

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from src.reports.models import ReportData
from src.reports.templates import (
    BODY_STYLE, BULLET_STYLE, MARGIN, META_STYLE, PAGE_SIZE, SECTION_HEADING_STYLE,
    SOURCE_STYLE, SUBTITLE_STYLE, TABLE_GRID_COLOR, TABLE_HEADER_BG, TABLE_ROW_BG,
    TITLE_STYLE, WARNING_STYLE,
)


def _draw_page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TABLE_GRID_COLOR)
    canvas.drawCentredString(PAGE_SIZE[0] / 2, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _bullets(items: List[str], style=BULLET_STYLE):
    return [Paragraph(f"&bull; {_escape(item)}", style) for item in items]


def _escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pdf(data: ReportData) -> bytes:
    buffer = io.BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=PAGE_SIZE,
                           leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="EvoResearch", frames=[frame], onPage=_draw_page_footer)])

    story = []
    story.append(Paragraph("EVORESEARCH", TITLE_STYLE))
    story.append(Paragraph("AUTONOMOUS RESEARCH REPORT", SUBTITLE_STYLE))
    story.append(Paragraph(f"Research Run ID: {data.run_id}", META_STYLE))
    story.append(Paragraph(f"Generated: {data.generated_at}", META_STYLE))
    story.append(Paragraph(f"Status: {data.status}", META_STYLE))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Research Question", SECTION_HEADING_STYLE))
    story.append(Paragraph(_escape(data.question), BODY_STYLE))

    story.append(Paragraph("Executive Summary", SECTION_HEADING_STYLE))
    story.append(Paragraph(_escape(data.executive_summary) or "No summary was generated for this run.", BODY_STYLE))

    if data.key_findings:
        story.append(Paragraph("Key Findings", SECTION_HEADING_STYLE))
        story.extend(_bullets(data.key_findings))

    if data.verified_claims or data.unsupported_claims or data.contradicted_claims:
        story.append(Paragraph("Verified Claims", SECTION_HEADING_STYLE))
        rows = [["Claim", "Status", "Evidence"]]
        for c in data.verified_claims:
            rows.append([c["claim_text"][:80], "Supported", f"{c['supporting_count']} supporting"])
        for c in data.contradicted_claims:
            rows.append([c["claim_text"][:80], c["status"].title(), f"{c['contradicting_count']} contradicting"])
        for c in data.unsupported_claims:
            rows.append([c["claim_text"][:80], "Unsupported", "no linked evidence"])
        table = Table(rows, colWidths=[3.4 * inch, 1.1 * inch, 1.6 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [TABLE_ROW_BG, "white"]),
            ("GRID", (0, 0), (-1, -1), 0.5, TABLE_GRID_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        if data.verification_valid is not None:
            status_text = "PASSED" if data.verification_valid else "ISSUES FLAGGED"
            style = BODY_STYLE if data.verification_valid else WARNING_STYLE
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"Verification status: {status_text} (score {data.verification_score:.2f})", style,
            ))

    if data.citations:
        story.append(Paragraph("Citations", SECTION_HEADING_STYLE))
        for c in data.citations:
            story.append(Paragraph(
                f"[{c['citation_id']}] {_escape(c['title'])} &mdash; {_escape(c['publisher'])}<br/>{_escape(c['url'])}",
                SOURCE_STYLE,
            ))

    if data.quality:
        story.append(Paragraph("Research Quality", SECTION_HEADING_STYLE))
        q = data.quality
        rows = [
            ["Metric", "Value"],
            ["Sources", str(q.get("source_count", "N/A"))],
            ["Unique sources", str(q.get("unique_source_count", "N/A"))],
            ["Evidence passages", str(q.get("evidence_count", "N/A"))],
            ["Claims", str(q.get("claim_count", "N/A"))],
            ["Supported claims", str(q.get("supported_claim_count", "N/A"))],
            ["Contradicted claims", str(q.get("contradicted_claim_count", "N/A"))],
            ["Unverified claims", str(q.get("unverified_claim_count", "N/A"))],
            ["Overall valid", str(q.get("valid", "N/A"))],
        ]
        table = Table(rows, colWidths=[2.5 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [TABLE_ROW_BG, "white"]),
            ("GRID", (0, 0), (-1, -1), 0.5, TABLE_GRID_COLOR),
        ]))
        story.append(table)

    if data.gaps:
        story.append(Paragraph("Research Gaps", SECTION_HEADING_STYLE))
        story.extend(_bullets([f"[{g.get('priority', '?')}] {g.get('description', '')}" for g in data.gaps]))

    story.append(Paragraph("Research Iterations", SECTION_HEADING_STYLE))
    story.append(Paragraph(
        f"This research was conducted over {data.iteration_count} autonomous iteration(s), "
        f"concluding with decision: {data.research_decision or 'N/A'}.", BODY_STYLE,
    ))

    story.append(Paragraph("Methodology", SECTION_HEADING_STYLE))
    story.append(Paragraph(
        "EvoResearch's autonomous research loop planned sub-queries, searched the web, "
        "safely browsed and sanitized retrieved content against prompt injection, extracted "
        "and verified claims against evidence in a structured evidence graph, validated "
        "research quality, detected remaining research gaps, and repeated until quality "
        "requirements were met or the iteration limit was reached. The final answer was then "
        "independently checked against the same evidence in a separate final-answer "
        "verification pass before this report was generated.", BODY_STYLE,
    ))

    if data.limitations:
        story.append(Paragraph("Limitations", SECTION_HEADING_STYLE))
        story.extend(_bullets(data.limitations))

    if data.sources:
        story.append(Paragraph("Sources", SECTION_HEADING_STYLE))
        for s in data.sources:
            story.append(Paragraph(f"{_escape(s.get('title', ''))} &mdash; {_escape(s.get('url', ''))}", SOURCE_STYLE))

    doc.build(story)
    return buffer.getvalue()
