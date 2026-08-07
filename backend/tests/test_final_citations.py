"""Final Completion Phase - Part E: Citation Engine tests."""

from src.citations.builder import build_cited_answer, build_citations, format_citation_block, map_claims_to_citations
from src.citations.validator import validate_citations
from src.evidence.graph import EvidenceGraph
from src.models.evidence import Claim, ClaimStatus, RelationshipType
from src.models.schemas import Source


def _source(url, title="Title") -> Source:
    return Source(title=title, url=url)


def _claim(text="A claim") -> Claim:
    return Claim(research_run_id="run1", claim_text=text, status=ClaimStatus.SUPPORTED, supporting_count=1, source_count=1)


def _linked_graph(claim: Claim, source: Source) -> EvidenceGraph:
    graph = EvidenceGraph(research_run_id="run1")
    evidence_id = "ev-1"
    graph.add_node(claim.id, "claim", claim.claim_text)
    graph.add_node(evidence_id, "evidence", "evidence text")
    graph.add_node(source.id, "source", source.title)
    graph.add_edge(claim.id, evidence_id, RelationshipType.SUPPORTS.value)
    graph.add_edge(evidence_id, source.id, RelationshipType.DERIVED_FROM.value)
    return graph


# --------------------------------------------------------------------------
# citations come from real sources only
# --------------------------------------------------------------------------

def test_citations_are_built_from_real_sources_only():
    sources = [_source("https://a.example.com", "A"), _source("https://b.example.com", "B")]
    citations = build_citations(sources)
    assert len(citations) == 2
    assert citations[0].url == "https://a.example.com"
    assert citations[0].citation_id == 1
    assert citations[1].citation_id == 2
    # accessed_at comes from the real Source.retrieved_at field
    assert citations[0].accessed_at == sources[0].retrieved_at


def test_citation_numbering_is_deterministic():
    sources = [_source(f"https://s{i}.example.com") for i in range(5)]
    ids_a = [c.citation_id for c in build_citations(sources)]
    ids_b = [c.citation_id for c in build_citations(sources)]
    assert ids_a == ids_b == [1, 2, 3, 4, 5]


def test_no_citations_are_invented_for_empty_sources():
    assert build_citations([]) == []


# --------------------------------------------------------------------------
# claim -> citation mapping via the real evidence graph
# --------------------------------------------------------------------------

def test_claim_is_mapped_to_its_real_supporting_citation():
    source = _source("https://real.example.com")
    claim = _claim()
    graph = _linked_graph(claim, source)
    citations = build_citations([source])

    mapping = map_claims_to_citations([claim], graph, citations, [source])

    assert mapping[claim.id] == [1]


def test_claim_with_no_graph_linkage_gets_no_citation():
    claim = _claim()
    mapping = map_claims_to_citations([claim], None, [], [])
    assert claim.id not in mapping


def test_cited_answer_and_format_block_use_real_data_only():
    source = _source("https://real.example.com", "Real Study")
    claim = _claim("AI improves productivity")
    graph = _linked_graph(claim, source)

    cited = build_cited_answer([claim], [source], graph)
    block = format_citation_block(cited, [claim])

    assert "Real Study" in block
    assert "https://real.example.com" in block
    assert "[1]" in block
    assert "AI improves productivity" in block


# --------------------------------------------------------------------------
# citation validation
# --------------------------------------------------------------------------

def test_validate_citations_flags_invalid_url():
    sources = [_source("not-a-url")]
    citations = build_citations(sources)
    problems = validate_citations(citations)
    assert any("invalid URL" in p for p in problems)


def test_validate_citations_passes_for_real_sources():
    sources = [_source("https://real.example.com")]
    citations = build_citations(sources)
    assert validate_citations(citations) == []
