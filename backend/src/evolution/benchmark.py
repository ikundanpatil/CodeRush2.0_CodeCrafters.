"""Fixed benchmark used by Phase 7 to test a candidate strategy before it can
be accepted. Deterministic and offline (mock LLM + mock search) so evolution
cycles are fast, free, and repeatable -- matching the mock-first convention
already used across the test suite.
"""

from typing import List

from src.search.base import SearchProvider, SearchResult

BENCHMARK_QUESTIONS: List[str] = [
    "What is the impact of generative AI on software developer productivity?",
    "How effective are AI code review assistants at catching real bugs?",
    "Does pair programming improve long-term code quality?",
]

# A larger, varied pool than the default MockSearchProvider's 4 fixed results
# so that max_iterations / max_sources_per_iteration actually change how much
# evidence a strategy can accumulate within the benchmark. `build_evidence_graph`
# extracts one claim per run (MockAdapter always returns the same one) and then
# classifies *every* evidence item against it, so mixing SUPPORTS/CONTRADICTS
# content here would make the single claim MIXED regardless of how much
# evidence is gathered -- deliberately kept uniformly SUPPORTS-triggering
# ("boost"/"improved", MockAdapter's keyword classifier) so accumulating more
# evidence predictably keeps the claim supported instead of flipping to mixed;
# contradiction handling itself is already covered by Phase 4/5/6 tests.
_POOL: List[SearchResult] = [
    SearchResult(
        title="Controlled Study Shows Productivity Boost from AI Tooling",
        url="https://a1.example.org/study",
        content="A controlled study found a measurable boost in task completion speed.",
        source="Example Journal A", score=0.95,
    ),
    SearchResult(
        title="Industry Survey: Developers Report Improved Output",
        url="https://a2.example.org/survey",
        content="Developers self-reported improved output after adopting AI assistants.",
        source="Example Journal B", score=0.9,
    ),
    SearchResult(
        title="Meta-Analysis of AI Coding Assistant Studies",
        url="https://a3.example.org/meta-analysis",
        content="A meta-analysis found a consistent boost in short-term throughput across studies.",
        source="Example Journal C", score=0.85,
    ),
    SearchResult(
        title="Enterprise Case Study on Assistant-Driven Development",
        url="https://a4.example.org/case-study",
        content="Case study teams reported improved cycle time after rollout.",
        source="Example Journal D", score=0.8,
    ),
    SearchResult(
        title="Replication Study Confirms Earlier Productivity Boost",
        url="https://a5.example.org/replication",
        content="A replication attempt confirmed the boost in productivity reported elsewhere.",
        source="Example Journal E", score=0.78,
    ),
    SearchResult(
        title="Follow-Up Analysis of Long-Term Codebase Health",
        url="https://a6.example.org/follow-up",
        content="Follow-up analysis found a boost in initial velocity and improved review turnaround.",
        source="Example Journal F", score=0.75,
    ),
    SearchResult(
        title="Cross-Team Rollout Report",
        url="https://a7.example.org/rollout-report",
        content="Cross-team rollout data showed improved throughput across every cohort measured.",
        source="Example Journal G", score=0.7,
    ),
    SearchResult(
        title="Independent Benchmark of Assistant-Driven Workflows",
        url="https://a8.example.org/benchmark",
        content="An independent benchmark found a consistent boost in delivery speed.",
        source="Example Journal H", score=0.65,
    ),
]


class RotatingPoolSearchProvider(SearchProvider):
    """Deterministic benchmark-only search double.

    Ignores the query text (LLM-generated follow-up queries are unpredictable)
    and instead hands out the next unseen slice of a fixed pool each call, so
    successive research-loop iterations can keep finding genuinely new
    sources -- unlike the default `MockSearchProvider`, which returns
    identical content every call and would make `max_iterations` and
    `max_sources_per_iteration` untestable.
    """

    provides_full_content = True

    def __init__(self, question: str = ""):
        self.question = question
        self._cursor = 0

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        if self._cursor >= len(_POOL):
            return []
        batch = _POOL[self._cursor: self._cursor + max(1, max_results)]
        self._cursor += len(batch)
        return list(batch)
