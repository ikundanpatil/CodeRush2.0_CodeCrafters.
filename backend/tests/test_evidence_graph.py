import asyncio

from fastapi.testclient import TestClient

from src.api.main import app
from src.evidence.claim_extractor import extract_claims
from src.evidence.contradiction import classify_relationship
from src.evidence.graph_builder import build_evidence_graph
from src.evidence.store import EvidenceStore
from src.evidence.verifier import verify_claim
from src.llm.providers.mock import MockAdapter
from src.models.evidence import (
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceRelationship,
    EvidenceType,
    NodeType,
    RelationshipType,
)
from src.models.schemas import EvidenceRecord, Source

client = TestClient(app)


# --------------------------------------------------------------------------
# Store: claim / evidence / relationship persistence
# --------------------------------------------------------------------------

def test_store_claim_creation_and_retrieval():
    store = EvidenceStore()
    claim = Claim(research_run_id="run1", claim_text="Test claim")
    store.save_claim(claim)
    fetched = store.get_claim(claim.id)
    assert fetched.claim_text == "Test claim"
    assert fetched.status == ClaimStatus.UNVERIFIED


def test_store_evidence_creation_and_source_linking():
    store = EvidenceStore()
    claim = Claim(research_run_id="run1", claim_text="c")
    store.save_claim(claim)
    ev = Evidence(
        research_run_id="run1", claim_id=claim.id, source_id="src1",
        evidence_text="e1", evidence_type=EvidenceType.SUPPORTING,
    )
    store.save_evidence(ev)
    linked = store.list_evidence_by_claim(claim.id)
    assert len(linked) == 1
    assert linked[0].source_id == "src1"


def test_store_relationship_supports():
    store = EvidenceStore()
    rel = EvidenceRelationship(
        research_run_id="run1", from_type=NodeType.CLAIM, from_id="c1",
        relationship_type=RelationshipType.SUPPORTS, to_type=NodeType.EVIDENCE, to_id="e1",
    )
    store.save_relationship(rel)
    assert store.list_relationships_from("c1")[0].relationship_type == RelationshipType.SUPPORTS


def test_store_relationship_contradicts():
    store = EvidenceStore()
    rel = EvidenceRelationship(
        research_run_id="run1", from_type=NodeType.CLAIM, from_id="c1",
        relationship_type=RelationshipType.CONTRADICTS, to_type=NodeType.EVIDENCE, to_id="e1",
    )
    store.save_relationship(rel)
    assert store.list_relationships_from("c1")[0].relationship_type == RelationshipType.CONTRADICTS


def test_store_relationship_derived_from():
    store = EvidenceStore()
    rel = EvidenceRelationship(
        research_run_id="run1", from_type=NodeType.EVIDENCE, from_id="e1",
        relationship_type=RelationshipType.DERIVED_FROM, to_type=NodeType.SOURCE, to_id="s1",
    )
    store.save_relationship(rel)
    assert store.list_relationships_from("e1")[0].relationship_type == RelationshipType.DERIVED_FROM


def test_store_relationship_related_to():
    store = EvidenceStore()
    rel = EvidenceRelationship(
        research_run_id="run1", from_type=NodeType.CLAIM, from_id="c1",
        relationship_type=RelationshipType.RELATED_TO, to_type=NodeType.EVIDENCE, to_id="e2",
    )
    store.save_relationship(rel)
    assert store.list_relationships_from("c1")[0].relationship_type == RelationshipType.RELATED_TO


def test_get_contradictions_for_claim():
    store = EvidenceStore()
    claim = Claim(research_run_id="run1", claim_text="c")
    store.save_claim(claim)
    ev_support = Evidence(research_run_id="run1", claim_id=claim.id, source_id="s1", evidence_text="supports", evidence_type=EvidenceType.SUPPORTING)
    ev_contra = Evidence(research_run_id="run1", claim_id=claim.id, source_id="s2", evidence_text="contradicts", evidence_type=EvidenceType.CONTRADICTING)
    store.save_evidence(ev_support)
    store.save_evidence(ev_contra)
    store.save_relationship(EvidenceRelationship(
        research_run_id="run1", from_type=NodeType.CLAIM, from_id=claim.id,
        relationship_type=RelationshipType.SUPPORTS, to_type=NodeType.EVIDENCE, to_id=ev_support.id,
    ))
    store.save_relationship(EvidenceRelationship(
        research_run_id="run1", from_type=NodeType.CLAIM, from_id=claim.id,
        relationship_type=RelationshipType.CONTRADICTS, to_type=NodeType.EVIDENCE, to_id=ev_contra.id,
    ))
    contradictions = store.get_contradictions_for_claim(claim.id)
    assert len(contradictions) == 1
    assert contradictions[0].id == ev_contra.id


# --------------------------------------------------------------------------
# Verifier: claim status from evidence counts
# --------------------------------------------------------------------------

def test_verify_claim_supported():
    items = [Evidence(research_run_id="r", claim_id="c", source_id="s1", evidence_text="x", evidence_type=EvidenceType.SUPPORTING)]
    assert verify_claim(items)["status"] == ClaimStatus.SUPPORTED


def test_verify_claim_contradicted():
    items = [Evidence(research_run_id="r", claim_id="c", source_id="s1", evidence_text="x", evidence_type=EvidenceType.CONTRADICTING)]
    assert verify_claim(items)["status"] == ClaimStatus.CONTRADICTED


def test_verify_claim_mixed():
    items = [
        Evidence(research_run_id="r", claim_id="c", source_id="s1", evidence_text="x", evidence_type=EvidenceType.SUPPORTING),
        Evidence(research_run_id="r", claim_id="c", source_id="s2", evidence_text="y", evidence_type=EvidenceType.CONTRADICTING),
    ]
    result = verify_claim(items)
    assert result["status"] == ClaimStatus.MIXED
    assert result["supporting_count"] == 1
    assert result["contradicting_count"] == 1


def test_verify_claim_unverified_with_no_evidence():
    assert verify_claim([])["status"] == ClaimStatus.UNVERIFIED


def test_verify_claim_contextual_only_is_unverified():
    items = [Evidence(research_run_id="r", claim_id="c", source_id="s1", evidence_text="x", evidence_type=EvidenceType.CONTEXTUAL)]
    assert verify_claim(items)["status"] == ClaimStatus.UNVERIFIED


# --------------------------------------------------------------------------
# Conservative contradiction detection (mock LLM classifier)
# --------------------------------------------------------------------------

def test_classify_relationship_supports():
    rel, err = asyncio.run(classify_relationship(
        MockAdapter(), "AI improves productivity.", "Studies show a clear boost in productivity."
    ))
    assert rel == RelationshipType.SUPPORTS
    assert err is None


def test_classify_relationship_contradicts():
    rel, err = asyncio.run(classify_relationship(
        MockAdapter(), "AI improves productivity.", "The study did not show measurable productivity gains."
    ))
    assert rel == RelationshipType.CONTRADICTS


def test_classify_relationship_defaults_to_related_to_when_unrelated():
    rel, err = asyncio.run(classify_relationship(
        MockAdapter(), "AI improves productivity.", "The system uses a transformer architecture."
    ))
    assert rel == RelationshipType.RELATED_TO


class _MalformedLLM:
    async def generate(self, prompt, system_prompt=None, **kwargs):
        return "not json"


def test_classify_relationship_never_forces_contradiction_on_malformed_output():
    rel, err = asyncio.run(classify_relationship(_MalformedLLM(), "claim", "evidence"))
    assert rel == RelationshipType.RELATED_TO
    assert err is not None


# --------------------------------------------------------------------------
# Claim extraction (mock LLM)
# --------------------------------------------------------------------------

def test_extract_claims_with_mock_llm():
    evidences = [EvidenceRecord(claim="c", source_id="s1", source_title="T", source_url="https://x", passage="Studies show a boost.")]
    claims, err = asyncio.run(extract_claims(MockAdapter(), "run1", "question?", evidences))
    assert err is None
    assert len(claims) == 1
    assert claims[0].research_run_id == "run1"


def test_extract_claims_with_no_evidence_returns_empty():
    claims, err = asyncio.run(extract_claims(MockAdapter(), "run1", "question?", []))
    assert claims == []
    assert err is None


# --------------------------------------------------------------------------
# Graph construction, end to end
# --------------------------------------------------------------------------

def test_build_evidence_graph_end_to_end_mixed_claim():
    store = EvidenceStore()
    evidences = [
        EvidenceRecord(claim="c1", source_id="s1", source_title="Supportive Study", source_url="https://a", passage="Studies show a clear boost in productivity."),
        EvidenceRecord(claim="c2", source_id="s2", source_title="Contradicting Study", source_url="https://b", passage="The study did not show measurable productivity gains."),
    ]
    sources = [
        Source(id="s1", title="Supportive Study", url="https://a"),
        Source(id="s2", title="Contradicting Study", url="https://b"),
    ]
    graph, claims = asyncio.run(build_evidence_graph(
        MockAdapter(), "run-x", "Does AI improve productivity?", evidences, sources, store=store,
    ))

    assert len(claims) == 1
    claim = claims[0]
    assert claim.status == ClaimStatus.MIXED
    assert claim.supporting_count == 1
    assert claim.contradicting_count == 1

    graph_dict = graph.to_dict()
    relationship_types = {e["relationship"] for e in graph_dict["edges"]}
    assert {"SUPPORTS", "CONTRADICTS", "DERIVED_FROM"}.issubset(relationship_types)

    node_types = {n["type"] for n in graph_dict["nodes"]}
    assert node_types == {"claim", "evidence", "source"}


def test_build_evidence_graph_degrades_gracefully_on_extraction_failure():
    class _MalformedLLM:
        async def generate(self, prompt, system_prompt=None, **kwargs):
            return "not json at all"

    evidences = [EvidenceRecord(claim="c", source_id="s1", source_title="T", source_url="https://x", passage="text")]
    sources = [Source(id="s1", title="T", url="https://x")]
    graph, claims = asyncio.run(build_evidence_graph(
        _MalformedLLM(), "run-y", "q?", evidences, sources, store=EvidenceStore(),
    ))
    assert claims == []
    assert graph.nodes == []


def test_build_evidence_graph_empty_evidence_yields_no_claims():
    graph, claims = asyncio.run(build_evidence_graph(
        MockAdapter(), "run-z", "q?", [], [], store=EvidenceStore(),
    ))
    assert claims == []
    assert graph.nodes == []


# --------------------------------------------------------------------------
# Evidence graph API, end to end through a real research run
# --------------------------------------------------------------------------

def test_evidence_api_full_flow():
    response = client.post("/api/research", json={"question": "Does generative AI improve software developer productivity?"})
    run_id = response.json()["run_id"]

    result = client.get(f"/api/research/{run_id}/result").json()
    assert result["claim_count"] >= 1
    assert result["evidence_graph_available"] is True

    claims = client.get(f"/api/evidence/research/{run_id}").json()
    assert len(claims) >= 1
    claim_id = claims[0]["id"]

    claim_detail = client.get(f"/api/evidence/claims/{claim_id}").json()
    assert claim_detail["id"] == claim_id

    evidence_items = client.get(f"/api/evidence/claims/{claim_id}/evidence").json()
    assert len(evidence_items) >= 1

    contradictions = client.get(f"/api/evidence/claims/{claim_id}/contradictions").json()
    assert isinstance(contradictions, list)

    graph = client.get(f"/api/evidence/graph/{run_id}").json()
    assert graph["research_run_id"] == run_id
    assert len(graph["nodes"]) >= 1
    assert len(graph["edges"]) >= 1
    for node in graph["nodes"]:
        assert set(node.keys()) == {"id", "type", "label"}
    for edge in graph["edges"]:
        assert set(edge.keys()) == {"from", "to", "relationship"}


def test_evidence_claim_not_found_returns_404():
    response = client.get("/api/evidence/claims/does-not-exist")
    assert response.status_code == 404
