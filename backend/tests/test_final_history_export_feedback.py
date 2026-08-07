"""Final Completion Phase - Part G (history), Part H (export/share), and
Part I (feedback) tests."""

from fastapi.testclient import TestClient

from src.api.main import app
from src.models.schemas import ResearchRun, RunStatus
from src.storage.store import store

client = TestClient(app)


def _completed_run(question="Does exercise improve long-term health?") -> ResearchRun:
    run = ResearchRun(question=question)
    run.status = RunStatus.COMPLETED
    run.answer = "Exercise improves long-term health outcomes."
    run.source_count = 2
    run.claim_count = 1
    run.quality_valid = True
    run.verification_result = {"valid": True}
    run.citations = [{"citation_id": 1, "title": "Real Study", "publisher": "Real Journal", "url": "https://real.example.com"}]
    store.save_run(run)
    return run


# --------------------------------------------------------------------------
# Part G - history
# --------------------------------------------------------------------------

def test_history_list_reflects_real_run_data():
    run = _completed_run()
    response = client.get("/api/research/history")
    assert response.status_code == 200
    item = next(i for i in response.json() if i["run_id"] == run.run_id)
    assert item["question"] == run.question
    assert item["source_count"] == 2
    assert item["claim_count"] == 1
    assert item["quality_valid"] is True
    assert item["verification_valid"] is True
    assert item["report_available"] is True


def test_history_item_endpoint():
    run = _completed_run()
    response = client.get(f"/api/research/history/{run.run_id}")
    assert response.status_code == 200
    assert response.json()["run_id"] == run.run_id


def test_history_item_404_for_unknown_run():
    assert client.get("/api/research/history/does-not-exist").status_code == 404


def test_incomplete_run_shows_report_not_available():
    run = ResearchRun(question="Still running")
    run.status = RunStatus.SEARCHING
    store.save_run(run)
    response = client.get(f"/api/research/history/{run.run_id}")
    assert response.json()["report_available"] is False


# --------------------------------------------------------------------------
# Part H - export / share
# --------------------------------------------------------------------------

def test_export_json_returns_real_data_as_a_download():
    run = _completed_run()
    response = client.get(f"/api/research/{run.run_id}/export/json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    body = response.json()
    assert body["question"] == run.question
    assert body["answer"] == run.answer


def test_share_view_excludes_internal_bookkeeping():
    run = _completed_run()
    run.memory_context = [{"secret_internal_field": "should not leak"}]
    run.cancel_requested = False
    store.save_run(run)

    response = client.get(f"/api/research/{run.run_id}/share")
    assert response.status_code == 200
    body = response.json()
    assert "memory_context" not in body
    assert "cancel_requested" not in body
    assert "trace" not in body
    assert body["question"] == run.question
    assert body["answer"] == run.answer
    assert body["citations"] == run.citations


def test_share_404_for_unknown_run():
    assert client.get("/api/research/does-not-exist/share").status_code == 404


# --------------------------------------------------------------------------
# Part I - feedback
# --------------------------------------------------------------------------

def test_submit_and_list_feedback():
    run = _completed_run()
    response = client.post(f"/api/research/{run.run_id}/feedback", json={"helpful": True, "rating": 5, "comment": "Great"})
    assert response.status_code == 201
    body = response.json()
    assert body["run_id"] == run.run_id
    assert body["helpful"] is True
    assert body["rating"] == 5

    listed = client.get(f"/api/research/{run.run_id}/feedback")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["run_id"] == run.run_id


def test_feedback_requires_at_least_one_field():
    run = _completed_run()
    response = client.post(f"/api/research/{run.run_id}/feedback", json={})
    assert response.status_code == 400


def test_feedback_404_for_unknown_run():
    response = client.post("/api/research/does-not-exist/feedback", json={"helpful": True})
    assert response.status_code == 404


def test_feedback_rating_bounds_enforced():
    run = _completed_run()
    response = client.post(f"/api/research/{run.run_id}/feedback", json={"rating": 10})
    assert response.status_code == 422  # out of the 1-5 bound
