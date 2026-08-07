"""Pure, deterministic checks used by FinalAnswerVerifier. Every function
here reads only real runtime objects (Claim, Source, the generated answer
text) -- never an LLM's opinion of its own answer.
"""

import re
from typing import List, Set
from urllib.parse import urlparse

from src.models.evidence import Claim, ClaimStatus
from src.models.schemas import Source
from src.quality.rules import is_valid_url

_URL_PATTERN = re.compile(r"https?://[^\s\)\]<>\"']+")
_SOURCE_COUNT_PATTERN = re.compile(r"(\d+)\s+(?:unique\s+)?sources?\b", re.IGNORECASE)
_CITATION_MARKER_PATTERN = re.compile(r"\[(\d+)\]")


def extract_urls(text: str) -> Set[str]:
    return {u.rstrip(".,;:)") for u in _URL_PATTERN.findall(text or "")}


def find_fabricated_urls(answer_text: str, sources: List[Source]) -> List[str]:
    """Any URL appearing in the answer text that isn't one of the run's
    real, collected sources is a fabricated citation -- never invented."""
    real_urls = {s.url for s in sources}
    mentioned = extract_urls(answer_text)
    return sorted(mentioned - real_urls)


def find_source_count_mismatches(answer_text: str, sources: List[Source]) -> List[str]:
    """Catches a stray "N sources" claim in free-text prose that doesn't
    match the real collected count -- the quality-stats block the
    orchestrator appends is already real, but LLM-authored prose earlier in
    the answer is not otherwise checked anywhere."""
    real_count = len(sources)
    issues = []
    for match in _SOURCE_COUNT_PATTERN.finditer(answer_text or ""):
        claimed = int(match.group(1))
        if claimed != real_count:
            issues.append(
                f"Answer text claims {claimed} source(s), but {real_count} were actually collected."
            )
    return issues


def find_invalid_citation_markers(answer_text: str, citation_count: int) -> List[str]:
    """A [n] marker referencing a citation number that doesn't exist is a
    fabricated citation."""
    issues = []
    for match in _CITATION_MARKER_PATTERN.finditer(answer_text or ""):
        n = int(match.group(1))
        if n < 1 or n > citation_count:
            issues.append(f"Citation marker [{n}] does not correspond to any real source.")
    return issues


def find_invalid_source_urls(sources: List[Source]) -> List[str]:
    return [f"Source '{s.title}' has an invalid URL: {s.url!r}" for s in sources if not is_valid_url(s.url)]


def classify_claims(claims: List[Claim]):
    """Splits claims into (verified, unsupported, contradicted) using only
    the real, already-computed Claim.status from Phase 4's evidence
    verification -- never re-judged by an LLM here."""
    verified, unsupported, contradicted = [], [], []
    for claim in claims:
        if claim.status == ClaimStatus.SUPPORTED:
            verified.append(claim)
        elif claim.status in (ClaimStatus.CONTRADICTED, ClaimStatus.MIXED):
            contradicted.append(claim)
        else:  # UNVERIFIED, or supported/contradicting counts are both zero
            unsupported.append(claim)
    return verified, unsupported, contradicted
