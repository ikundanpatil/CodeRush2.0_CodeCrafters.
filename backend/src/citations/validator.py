"""Deterministic citation validation -- reuses src/quality/rules.py's URL
check rather than reimplementing it."""

from typing import List

from src.citations.models import Citation
from src.quality.rules import is_valid_url


def validate_citations(citations: List[Citation]) -> List[str]:
    problems: List[str] = []

    seen_ids = set()
    for citation in citations:
        if citation.citation_id in seen_ids:
            problems.append(f"Duplicate citation_id: {citation.citation_id}")
        seen_ids.add(citation.citation_id)

        if not is_valid_url(citation.url):
            problems.append(f"Citation [{citation.citation_id}] has an invalid URL: {citation.url!r}")
        if not citation.title:
            problems.append(f"Citation [{citation.citation_id}] is missing a title.")

    return problems
