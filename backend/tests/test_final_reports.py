"""Final Completion Phase - Part F: PDF Research Summary tests."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.models.schemas import ResearchRun, RunStatus
from src.reports.generator import generate_pdf
from src.reports.service import build_report_data
from src.storage.store import store

client = TestClient(app)


def _completed_run() -> ResearchRun:
    run = ResearchRun(question="Does exercise improve long-term health?")
    run.status = RunStatus.COMPLETED
    run.answer = "Exercise improves long-term health outcomes."
    run.report_summary = "Exercise improves long-term health outcomes."
    run.report_key_findings = ["Regular exercise reduces cardiovascular risk."]
    run.report_limitations = ["Long-term studies are limited in sample size."]
    run.citations = [{"citation_id": 1, "title": "Real Study", "publisher": "Real Journal",
                       "url": "https://real.example.com", "accessed_at": "2026-01-01T00:00:00Z"}]
    run.quality_result = {"valid": True, "source_count": 3, "unique_source_count": 3,
                           "evidence_count": 4, "claim_count": 2, "supported_claim_count": 2,
                           "contradicted_claim_count": 0, "unverified_claim_count": 0}
    run.verification_result = {"valid": True, "score": 1.0, "verified_claims": [], "unsupported_claims": [], "contradicted_claims": []}
    run.iterations = [{"iteration_number": 1, "gaps": []}]
    run.research_decision = "complete"
    store.save_run(run)
    return run


def test_pdf_is_a_real_valid_pdf_file():
    run = _completed_run()
    data = build_report_data(run)
    pdf_bytes = generate_pdf(data)

    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 500  # a real rendered document, not an empty stub


def test_pdf_endpoint_returns_correct_content_type_not_json():
    run = _completed_run()
    response = client.get(f"/api/research/{run.run_id}/report/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"
    assert "attachment" in response.headers["content-disposition"]
    assert f"evoresearch-{run.run_id}.pdf" in response.headers["content-disposition"]


def test_pdf_endpoint_404s_for_unknown_run():
    assert client.get("/api/research/does-not-exist/report/pdf").status_code == 404


def test_json_report_uses_only_real_run_data():
    run = _completed_run()
    data = build_report_data(run)

    assert data.question == run.question
    assert data.executive_summary == run.report_summary
    assert data.key_findings == run.report_key_findings
    assert data.citations == run.citations
    assert data.quality == run.quality_result
    assert data.run_id == run.run_id


def test_report_data_never_fabricates_missing_sections():
    run = ResearchRun(question="A run with nothing generated yet.")
    store.save_run(run)
    data = build_report_data(run)

    assert data.executive_summary == ""
    assert data.key_findings == []
    assert data.citations == []
    assert data.quality == {}
    # Still produces a real (if mostly empty) PDF -- never crashes.
    pdf_bytes = generate_pdf(data)
    assert pdf_bytes[:5] == b"%PDF-"


def test_report_json_endpoint():
    run = _completed_run()
    response = client.get(f"/api/research/{run.run_id}/report")
    assert response.status_code == 200
    body = response.json()
    assert body["question"] == run.question
    assert body["key_findings"] == run.report_key_findings


def test_report_post_requires_completed_run():
    run = ResearchRun(question="Still running.")
    run.status = RunStatus.SEARCHING
    store.save_run(run)
    response = client.post(f"/api/research/{run.run_id}/report")
    assert response.status_code == 409
