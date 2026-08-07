"""Assembles ReportData from a real ResearchRun (the ONE authoritative path
report/PDF/export all share -- Part O), and generates PDF bytes from it."""

from datetime import datetime, timezone

from src.models.schemas import ResearchRun
from src.reports.generator import generate_pdf
from src.reports.models import ReportData


def build_report_data(run: ResearchRun) -> ReportData:
    verification = run.verification_result or {}
    latest_gaps = run.iterations[-1].get("gaps", []) if run.iterations else []

    return ReportData(
        run_id=run.run_id,
        question=run.question,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        generated_at=datetime.now(timezone.utc).isoformat(),
        research_run_created_at=run.created_at,
        completed_at=run.completed_at,
        executive_summary=run.report_summary or "",
        key_findings=run.report_key_findings,
        limitations=run.report_limitations,
        verified_claims=verification.get("verified_claims", []),
        unsupported_claims=verification.get("unsupported_claims", []),
        contradicted_claims=verification.get("contradicted_claims", []),
        verification_valid=verification.get("valid"),
        verification_score=verification.get("score"),
        citations=run.citations,
        quality=run.quality_result,
        gaps=latest_gaps,
        iteration_count=len(run.iterations),
        research_decision=run.research_decision,
        sources=[s.model_dump() for s in run.sources],
    )


class ReportService:
    def get_report_data(self, run: ResearchRun) -> ReportData:
        return build_report_data(run)

    def generate_pdf_bytes(self, run: ResearchRun) -> bytes:
        return generate_pdf(build_report_data(run))


report_service = ReportService()
