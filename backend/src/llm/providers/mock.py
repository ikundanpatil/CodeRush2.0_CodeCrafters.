import json
from typing import Optional

from src.llm.base import LLMAdapter


class MockAdapter(LLMAdapter):
    """Deterministic, offline provider. Default provider; required for tests."""

    def __init__(self, model: str = "mock-model", **_):
        self.model = model

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        if kwargs.get("mock_response") is not None:
            return kwargs["mock_response"]

        combined = f"{system_prompt or ''}\n{prompt}"

        # Phase 6: follow-up research query generation (checked before the
        # more generic branches below, since its system prompt is the most
        # specific).
        if "research_gap" in combined and "follow-up" in combined.lower():
            return json.dumps({
                "research_gap": "Current evidence is one-sided or insufficient.",
                "queries": [
                    "independent controlled studies on the topic",
                    "critical review and limitations of the claim",
                    "contradicting evidence and counterpoints",
                ],
                "reason": "Mock heuristic follow-up queries targeting the identified research gap.",
            })

        # Phase 4: claim extraction (checked before the more generic branches
        # below, since its system prompt is the most specific).
        if "claim_text" in combined:
            return json.dumps({
                "claims": [
                    {
                        "claim_text": "Generative AI can improve developer productivity.",
                        "confidence": 0.8,
                        "importance": 0.9,
                    },
                ],
            })

        # Phase 4: claim <-> evidence relationship classification.
        if "RELATED_TO" in combined and "CONTRADICTS" in combined and "SUPPORTS" in combined:
            lowered = combined.lower()
            if "did not show measurable productivity gains" in lowered or "not show" in lowered:
                relationship = "CONTRADICTS"
            elif "boost" in lowered or "improved" in lowered:
                relationship = "SUPPORTS"
            else:
                relationship = "RELATED_TO"
            return json.dumps({"relationship": relationship, "reasoning": "Mock heuristic classification."})

        if "sub_queries" in combined:
            return json.dumps({
                "objective": "Investigate the research question using available evidence.",
                "sub_queries": [
                    "What direct evidence addresses the question?",
                    "What benchmarks or studies quantify the effect?",
                    "What risks or limitations are documented?",
                ],
                "source_types": ["research papers", "industry reports", "recent news"],
                "verify": [
                    "Check publication dates for recency.",
                    "Cross-check quantitative claims across independent sources.",
                ],
            })

        if "key_findings" in combined:
            return json.dumps({
                "answer": "Mock answer synthesized from the collected evidence.",
                "key_findings": [
                    "Mock finding one derived from the provided evidence.",
                    "Mock finding two derived from the provided evidence.",
                ],
                "limitations": ["This is a mock report; evidence coverage is limited to sample sources."],
            })

        return "Mock LLM response."
