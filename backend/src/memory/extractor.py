"""Memory extraction from completed research runs.

Turns a finished :class:`ResearchRun` into a focused set of useful memories.
Deliberately does NOT dump the raw research response -- it synthesizes concise,
type-tagged memories with confidence/importance scores and source references.

Extraction respects the security boundary: it only consumes already-sanitized
source content (the orchestrator sanitizes retrieval output before evidence is
built), so malicious instructions can never become trusted memory.
"""

from typing import List

from src.models.memory import Memory, MemoryType
from src.models.schemas import ResearchRun


def _clip(text: str, limit: int = 280) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class MemoryExtractor:
    def extract(self, run: ResearchRun) -> List[Memory]:
        memories: List[Memory] = []

        memories.append(self._research_summary(run))
        memories.extend(self._findings(run))
        memories.extend(self._sources(run))
        if run.answer:
            memories.append(self._conclusion(run))
        memories.append(self._strategy(run))

        return [m for m in memories if m is not None]

    def _research_summary(self, run: ResearchRun) -> Memory:
        content = (
            f"Research on '{run.question}' synthesised {len(run.sources)} sources "
            f"into a source-backed report."
        )
        return Memory(
            memory_type=MemoryType.RESEARCH_SUMMARY,
            content=content,
            summary=f"Summary of research run: {run.question}",
            research_run_id=run.run_id,
            source_ids=[s.id for s in run.sources],
            confidence=0.95,
            importance=0.8,
            metadata={"question": run.question, "source_count": len(run.sources)},
        )

    def _findings(self, run: ResearchRun) -> List[Memory]:
        findings: List[Memory] = []
        for idx, evidence in enumerate(run.evidence[:10]):
            claim = _clip(evidence.claim or evidence.passage)
            if not claim:
                continue
            findings.append(Memory(
                memory_type=MemoryType.FINDING,
                content=f"{claim} (from {evidence.source_title}).",
                summary=_clip(claim, 120),
                research_run_id=run.run_id,
                source_ids=[evidence.source_id] if evidence.source_id else [],
                confidence=max(0.0, min(0.99, evidence.confidence)),
                importance=0.7,
                metadata={"source_url": evidence.source_url},
            ))
        return findings

    def _sources(self, run: ResearchRun) -> List[Memory]:
        sources: List[Memory] = []
        for source in run.sources[:8]:
            title = _clip(source.title, 140)
            sources.append(Memory(
                memory_type=MemoryType.SOURCE,
                content=f"Source: {title} by {source.publisher} ({source.url}).",
                summary=title,
                research_run_id=run.run_id,
                source_ids=[source.id],
                confidence=0.9,
                importance=0.5,
                metadata={"url": source.url, "publisher": source.publisher},
            ))
        return sources

    def _conclusion(self, run: ResearchRun) -> Memory:
        text = " ".join((run.answer or "").split())
        return Memory(
            memory_type=MemoryType.CONCLUSION,
            content=_clip(text, 420),
            summary="Conclusion drawn from this research run.",
            research_run_id=run.run_id,
            source_ids=[s.id for s in run.sources],
            confidence=0.85,
            importance=0.85,
            metadata={"question": run.question},
        )

    def _strategy(self, run: ResearchRun) -> Memory:
        return Memory(
            memory_type=MemoryType.STRATEGY,
            content=(
                f"Research strategy for '{run.question}': decomposing the question, "
                f"running web searches, enforcing the prompt-injection security "
                f"boundary, cross-verifying claims from evidence, and generating a "
                f"source-backed report."
            ),
            summary="Plan-decompose-search-secure-verify-synthesize strategy.",
            research_run_id=run.run_id,
            source_ids=[],
            confidence=0.8,
            importance=0.6,
            metadata={"question": run.question, "source_count": len(run.sources)},
        )


memory_extractor = MemoryExtractor()