"""Final Completion Phase - Part C: Conversational Research tests.

Backend-side session context, not a frontend illusion: a follow-up like
"what are the disadvantages?" must resolve against the session's stored
topic even though the frontend never sent it.
"""

import asyncio

from fastapi.testclient import TestClient

from src.api.main import app
from src.conversation.intents import ConversationIntent, resolve_intent
from src.conversation.service import ConversationService
from src.conversation.store import ConversationStore
from src.llm.providers.mock import MockAdapter
from src.models.schemas import RunStatus
from src.storage.store import store as research_store

client = TestClient(app)


def _service():
    return ConversationService(store=ConversationStore(engine=None, create_tables=False))


def _schedule(run_ids):
    def _fn(run_id):
        run_ids.append(run_id)
        run = research_store.get_run(run_id)
        # Deterministically "complete" the run synchronously for the test --
        # equivalent to what the real background orchestrator does, without
        # depending on FastAPI's BackgroundTasks machinery here.
        run.status = RunStatus.COMPLETED
        run.answer = "A real generated answer."
        run.report_key_findings = ["Finding one.", "Finding two."]
        run.verification_result = {
            "valid": True,
            "verified_claims": [{"claim_text": "AI boosts productivity."}],
            "contradicted_claims": [{"claim_text": "Effects vary by task."}],
        }
        research_store.save_run(run)
    return _fn


# --------------------------------------------------------------------------
# intent classification (deterministic fallback -- MockAdapter doesn't know
# this prompt shape, exercising the same fallback path by design)
# --------------------------------------------------------------------------

def test_new_conversation_with_no_topic_is_new_research():
    intent, question = asyncio.run(resolve_intent("Research quantum computing.", None, [], MockAdapter()))
    assert intent == ConversationIntent.NEW_RESEARCH
    assert question == "Research quantum computing."


def test_followup_referring_to_current_topic_is_understood():
    intent, question = asyncio.run(resolve_intent(
        "What are the disadvantages?", "generative AI developer productivity", [], MockAdapter(),
    ))
    assert intent == ConversationIntent.FOLLOW_UP
    assert "disadvantages" in question
    assert "generative AI developer productivity" in question


def test_unrelated_new_question_is_not_forced_into_old_topic():
    intent, question = asyncio.run(resolve_intent(
        "Research the history of the Roman Empire.", "generative AI developer productivity", [], MockAdapter(),
    ))
    assert intent == ConversationIntent.NEW_RESEARCH
    assert "Roman Empire" in question


def test_stop_is_always_recognized_regardless_of_topic():
    intent, _ = asyncio.run(resolve_intent("Stop.", "some topic", [], MockAdapter()))
    assert intent == ConversationIntent.STOP


def test_empty_message_is_classified_empty():
    intent, _ = asyncio.run(resolve_intent("   ", "some topic", [], MockAdapter()))
    assert intent == ConversationIntent.EMPTY


# --------------------------------------------------------------------------
# session service: full flow
# --------------------------------------------------------------------------

def test_create_session_starts_research_and_sets_topic():
    service = _service()
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    assert session.topic == "Research generative AI productivity."
    assert session.active_run_id == run_ids[0]
    assert len(session.messages) == 2  # user + assistant ack


def test_followup_continues_the_same_session_with_context():
    service = _service()
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    updated, outcome = asyncio.run(service.add_message(session.session_id, "What are the disadvantages?", _schedule(run_ids)))

    assert outcome == "follow_up"
    assert len(run_ids) == 2  # a new research run was started for the follow-up
    assert updated.active_run_id == run_ids[1]
    last_assistant = [m for m in updated.messages if m.role.value == "assistant"][-1]
    assert "disadvantages" in last_assistant.content.lower() or run_ids[1] in last_assistant.content


def test_summarize_uses_real_stored_findings_not_a_new_run():
    service = _service()
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    updated, outcome = asyncio.run(service.add_message(session.session_id, "Summarize the research.", _schedule(run_ids)))

    assert outcome == "summarize"
    assert len(run_ids) == 1  # no new research run for summarize
    last_assistant = [m for m in updated.messages if m.role.value == "assistant"][-1]
    assert "Finding one." in last_assistant.content


def test_compare_uses_real_verification_data():
    service = _service()
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    updated, outcome = asyncio.run(service.add_message(session.session_id, "Compare the findings.", _schedule(run_ids)))

    assert outcome == "compare"
    last_assistant = [m for m in updated.messages if m.role.value == "assistant"][-1]
    assert "AI boosts productivity." in last_assistant.content
    assert "Effects vary by task." in last_assistant.content


def test_generate_pdf_points_to_the_real_pdf_endpoint_for_current_session():
    service = _service()
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    updated, outcome = asyncio.run(service.add_message(session.session_id, "Create a PDF.", _schedule(run_ids)))

    assert outcome == "generate_pdf"
    last_assistant = [m for m in updated.messages if m.role.value == "assistant"][-1]
    assert f"/api/research/{session.active_run_id}/report/pdf" in last_assistant.content


def test_read_answer_returns_the_real_stored_answer():
    service = _service()
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    updated, outcome = asyncio.run(service.add_message(session.session_id, "Read the answer.", _schedule(run_ids)))

    assert outcome == "read_answer"
    last_assistant = [m for m in updated.messages if m.role.value == "assistant"][-1]
    assert last_assistant.content == "A real generated answer."


def test_missing_session_returns_none():
    service = _service()
    session, outcome = asyncio.run(service.add_message("does-not-exist", "hello", _schedule([])))
    assert session is None
    assert outcome == "not_found"


def test_conversation_persists_and_is_listable():
    store = ConversationStore(engine=None, create_tables=False)
    service = ConversationService(store=store)
    run_ids = []
    session = asyncio.run(service.create_session("Research generative AI productivity.", _schedule(run_ids)))

    fetched = service.get_session(session.session_id)
    assert fetched is not None
    assert fetched.session_id == session.session_id

    sessions = service.list_sessions()
    assert any(s.session_id == session.session_id for s in sessions)

    assert service.delete_session(session.session_id) is True
    assert service.get_session(session.session_id) is None


# --------------------------------------------------------------------------
# API layer (TestClient runs BackgroundTasks synchronously, so by the time
# each response returns the triggered research run has already completed)
# --------------------------------------------------------------------------

def test_api_create_conversation_and_followup():
    response = client.post("/api/conversations", json={"message": "Research generative AI productivity."})
    assert response.status_code == 201
    session = response.json()
    assert session["topic"] == "Research generative AI productivity."
    sid = session["session_id"]

    followup = client.post(f"/api/conversations/{sid}/messages", json={"message": "What are the disadvantages?"})
    assert followup.status_code == 200
    messages = followup.json()["messages"]
    assert messages[-1]["intent"] == "follow_up"


def test_api_get_and_list_and_delete_conversation():
    created = client.post("/api/conversations", json={"message": "Research topic X."}).json()
    sid = created["session_id"]

    assert client.get(f"/api/conversations/{sid}").status_code == 200
    assert any(s["session_id"] == sid for s in client.get("/api/conversations").json())

    assert client.delete(f"/api/conversations/{sid}").status_code == 200
    assert client.get(f"/api/conversations/{sid}").status_code == 404


def test_api_message_to_missing_session_is_404():
    response = client.post("/api/conversations/does-not-exist/messages", json={"message": "hello"})
    assert response.status_code == 404


def test_api_empty_message_is_rejected():
    response = client.post("/api/conversations", json={"message": "   "})
    assert response.status_code == 400
