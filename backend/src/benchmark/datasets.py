"""Phase 9 fixed, offline benchmark dataset.

Ten questions across ten research styles, each with a benchmark-fixture
search provider (BENCHMARK FIXTURE DATA below -- not real search results).
Reuses the existing `SearchProvider` abstraction (src/search/base.py)
instead of inventing a second search architecture, the same way Phase 7's
`RotatingPoolSearchProvider` (src/evolution/benchmark.py) does.

Content is deliberately written to trip MockAdapter's keyword-based
relationship classifier consistently toward SUPPORTS ("boost"/"improved"),
so benchmark scoring stays deterministic instead of drifting into MIXED
claim status depending on how many fixture items a strategy happens to
gather -- the same lesson learned building the Phase 7 benchmark.
"""

from typing import Dict, List

from src.benchmark.models import BenchmarkQuestion
from src.search.base import SearchProvider, SearchResult

BENCHMARK_QUESTIONS: List[BenchmarkQuestion] = [
    BenchmarkQuestion(
        benchmark_id="TECH-001",
        question="How is edge computing changing real-time data processing?",
        category="Technology",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="AI-001",
        question="Does generative AI improve software developer productivity?",
        category="AI",
        expected_min_sources=3, expected_min_evidence=5, expected_min_supported_claims=2,
    ),
    BenchmarkQuestion(
        benchmark_id="DEV-001",
        question="Do automated code review tools reduce production bugs?",
        category="Software Development",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="SEC-001",
        question="How effective is multi-factor authentication at preventing account takeover?",
        category="Cybersecurity",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="ENV-001",
        question="Does renewable energy adoption reduce grid-level carbon emissions?",
        category="Environment",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="EDU-001",
        question="Does personalized learning software improve student outcomes?",
        category="Education",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="HEALTH-001",
        question="Can wearable health devices improve early detection of chronic conditions?",
        category="Healthcare Technology",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="BIZ-001",
        question="Does remote work affect productivity in knowledge-work roles?",
        category="Business",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="SCI-001",
        question="What evidence supports CRISPR gene editing as a treatment approach?",
        category="Science",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
    BenchmarkQuestion(
        benchmark_id="GEN-001",
        question="What are the documented benefits of regular physical exercise?",
        category="General Knowledge",
        expected_min_sources=3, expected_min_evidence=4, expected_min_supported_claims=1,
    ),
]

BENCHMARK_DATASET = BENCHMARK_QUESTIONS


def get_question(benchmark_id: str) -> BenchmarkQuestion:
    for q in BENCHMARK_QUESTIONS:
        if q.benchmark_id == benchmark_id:
            return q
    raise KeyError(f"Unknown benchmark_id: {benchmark_id}")


# --------------------------------------------------------------------------
# BENCHMARK FIXTURE DATA -- fixed, offline, deterministic. Not real search
# results. One small pool of realistic-shaped sources per benchmark_id.
# --------------------------------------------------------------------------
def _fixture(benchmark_id: str, topic: str, domain: str) -> List[SearchResult]:
    # Each item lives on its own subdomain -- distinct publishers, not one
    # site with six pages -- so source_diversity reflects genuinely
    # independent sources and gathering more evidence from this pool never
    # perversely lowers diversity.
    bid = benchmark_id.lower()
    return [
        SearchResult(
            title=f"Controlled Study: {topic} Shows Measurable Boost",
            url=f"https://journal.{domain}.example.org/{bid}/controlled-study",
            content=f"A controlled study found a measurable boost related to {topic.lower()}.",
            source=f"{domain.title()} Research Journal", score=0.95,
        ),
        SearchResult(
            title=f"Industry Survey on {topic}",
            url=f"https://industry.{domain}.example.org/{bid}/industry-survey",
            content=f"An industry survey reported improved outcomes tied to {topic.lower()}.",
            source=f"{domain.title()} Industry Report", score=0.9,
        ),
        SearchResult(
            title=f"Meta-Analysis of {topic} Research",
            url=f"https://meta.{domain}.example.org/{bid}/meta-analysis",
            content=f"A meta-analysis of multiple studies found a consistent boost from {topic.lower()}.",
            source=f"{domain.title()} Meta-Analysis Council", score=0.85,
        ),
        SearchResult(
            title=f"Case Study: {topic} in Practice",
            url=f"https://cases.{domain}.example.org/{bid}/case-study",
            content=f"A field case study observed improved results after adopting {topic.lower()}.",
            source=f"{domain.title()} Case Study Archive", score=0.8,
        ),
        SearchResult(
            title=f"Independent Review of {topic}",
            url=f"https://review.{domain}.example.org/{bid}/independent-review",
            content=f"An independent review found a consistent boost attributable to {topic.lower()}.",
            source=f"{domain.title()} Independent Review Board", score=0.75,
        ),
        SearchResult(
            title=f"Follow-Up Analysis of {topic}",
            url=f"https://followup.{domain}.example.org/{bid}/follow-up",
            content=f"Follow-up analysis confirmed improved results consistent with {topic.lower()}.",
            source=f"{domain.title()} Follow-Up Study Group", score=0.7,
        ),
    ]


_FIXTURE_POOLS: Dict[str, List[SearchResult]] = {
    "TECH-001": _fixture("TECH-001", "Edge Computing for Real-Time Processing", "techresearch"),
    "AI-001": _fixture("AI-001", "Generative AI and Developer Productivity", "airesearch"),
    "DEV-001": _fixture("DEV-001", "Automated Code Review Tooling", "devresearch"),
    "SEC-001": _fixture("SEC-001", "Multi-Factor Authentication", "secresearch"),
    "ENV-001": _fixture("ENV-001", "Renewable Energy Adoption", "envresearch"),
    "EDU-001": _fixture("EDU-001", "Personalized Learning Software", "eduresearch"),
    "HEALTH-001": _fixture("HEALTH-001", "Wearable Health Devices", "healthresearch"),
    "BIZ-001": _fixture("BIZ-001", "Remote Work Productivity", "bizresearch"),
    "SCI-001": _fixture("SCI-001", "CRISPR Gene Editing", "sciresearch"),
    "GEN-001": _fixture("GEN-001", "Regular Physical Exercise", "genresearch"),
}


class BenchmarkFixtureSearchProvider(SearchProvider):
    """Deterministic, offline search provider for one benchmark question.

    Returns a different fixed pool of sources per benchmark_id (varies by
    *question*), and hands out the next unseen slice each call so repeated
    queries within a run (varies by *query count*) and looser strategy
    limits (varies by *strategy parameters* -- max_results_per_query /
    max_sources_per_iteration control how much of the pool is consumed)
    yield more evidence, mirroring how Phase 7's evolution benchmark search
    double behaves. Ignores query text itself since follow-up queries are
    LLM-generated and unpredictable.
    """

    provides_full_content = True

    def __init__(self, benchmark_id: str):
        self.benchmark_id = benchmark_id
        self._pool = _FIXTURE_POOLS.get(benchmark_id, [])
        self._cursor = 0

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if self._cursor >= len(self._pool):
            return []
        batch = self._pool[self._cursor: self._cursor + max(1, max_results)]
        self._cursor += len(batch)
        return list(batch)
