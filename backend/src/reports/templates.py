"""ReportLab style definitions for the PDF research report -- kept separate
from the rendering logic in generator.py so layout tweaks don't touch the
data-flow code."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch

PAGE_SIZE = LETTER
MARGIN = 0.75 * inch

BRAND_COLOR = colors.HexColor("#0F172A")
ACCENT_COLOR = colors.HexColor("#06B6D4")
MUTED_COLOR = colors.HexColor("#64748B")
WARNING_COLOR = colors.HexColor("#B45309")

_base = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "EvoTitle", parent=_base["Title"], fontSize=22, textColor=BRAND_COLOR, spaceAfter=2,
)
SUBTITLE_STYLE = ParagraphStyle(
    "EvoSubtitle", parent=_base["Normal"], fontSize=11, textColor=ACCENT_COLOR,
    spaceAfter=18, fontName="Helvetica-Bold",
)
SECTION_HEADING_STYLE = ParagraphStyle(
    "EvoSectionHeading", parent=_base["Heading2"], fontSize=14, textColor=BRAND_COLOR,
    spaceBefore=16, spaceAfter=8,
)
BODY_STYLE = ParagraphStyle(
    "EvoBody", parent=_base["Normal"], fontSize=10, leading=14, spaceAfter=6,
)
META_STYLE = ParagraphStyle(
    "EvoMeta", parent=_base["Normal"], fontSize=8.5, textColor=MUTED_COLOR, spaceAfter=2,
)
BULLET_STYLE = ParagraphStyle(
    "EvoBullet", parent=BODY_STYLE, leftIndent=14, bulletIndent=2, spaceAfter=4,
)
WARNING_STYLE = ParagraphStyle(
    "EvoWarning", parent=BODY_STYLE, textColor=WARNING_COLOR,
)
SOURCE_STYLE = ParagraphStyle(
    "EvoSource", parent=_base["Normal"], fontSize=8.5, leading=11, spaceAfter=6,
)

TABLE_HEADER_BG = colors.HexColor("#1E293B")
TABLE_ROW_BG = colors.HexColor("#F8FAFC")
TABLE_GRID_COLOR = colors.HexColor("#CBD5E1")
