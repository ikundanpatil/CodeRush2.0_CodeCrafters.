"""FinalAnswerVerifier: checks the GENERATED ANSWER TEXT after report
generation -- not the research process (that's Phase 5). Deterministic:
the LLM never gets to decide whether its own answer is valid.

    Research data -> Draft Answer -> FinalAnswerVerifier ->
    claim extraction (already done, Phase 4) -> evidence matching ->
    contradiction checking -> citation validation -> VerificationResult
"""

from typing import List

from src.models.evidence import Claim
from src.models.schemas import Source
from src.verification import rules
from src.verification.models import VerificationResult, VerifiedClaim


def _to_verified_claim(claim: Claim) -> VerifiedClaim:
    return VerifiedClaim(
        claim_id=claim.id,
        claim_text=claim.claim_text,
        status=claim.status.value,
        supporting_count=claim.supporting_count,
        contradicting_count=claim.contradicting_count,
        source_count=claim.source_count,
    )


class FinalAnswerVerifier:
    def verify(
        self,
        answer_text: str,
        claims: List[Claim],
        sources: List[Source],
        citation_count: int = 0,
    ) -> VerificationResult:
        verified, unsupported, contradicted = rules.classify_claims(claims)

        citation_errors: List[str] = []
        citation_errors.extend(
            f"Fabricated source URL in answer text (not among collected sources): {url}"
            for url in rules.find_fabricated_urls(answer_text, sources)
        )
        citation_errors.extend(rules.find_source_count_mismatches(answer_text, sources))
        citation_errors.extend(rules.find_invalid_source_urls(sources))
        if citation_count:
            citation_errors.extend(rules.find_invalid_citation_markers(answer_text, citation_count))

        warnings: List[str] = []
        reasons: List[str] = []

        if unsupported:
            warnings.append(f"{len(unsupported)} claim(s) have no supporting or contradicting evidence.")
            reasons.append("Unsupported claims present.")
        if contradicted:
            warnings.append(f"{len(contradicted)} claim(s) have contradicting evidence.")
            reasons.append("Contradicted/mixed claims present.")
        if citation_errors:
            reasons.append("Citation or fabrication issues detected in the answer text.")

        # Grounding score: a contradicted/mixed claim IS grounded in real
        # evidence (it has both supporting and contradicting sources) -- it
        # is an honest research finding, not a defect -- so it earns partial
        # credit rather than zero. Only genuinely unsupported claims and
        # fabrication score nothing.
        total = len(claims)
        grounded = len(verified) + 0.5 * len(contradicted)
        base_score = (grounded / total) if total else 0.0
        score = max(0.0, min(1.0, base_score - 0.1 * len(citation_errors)))

        # `valid` means: nothing fabricated, and nothing asserted without
        # evidence. Conflicting evidence is a legitimate outcome the report
        # is required to state honestly, so it does not by itself
        # invalidate the answer -- but it must never be described as
        # "fully supported" either (that phrasing is only emitted below
        # when there are genuinely no contradicted claims).
        valid = not citation_errors and not unsupported
        if valid:
            if contradicted:
                reasons.append(
                    "Every claim is grounded in real evidence and no fabrication was detected, "
                    "but some claims have conflicting evidence and are reported as mixed."
                )
            else:
                reasons.append("All claims are supported by real evidence; no fabrication detected.")

        return VerificationResult(
            valid=valid,
            score=score,
            verified_claims=[_to_verified_claim(c) for c in verified],
            unsupported_claims=[_to_verified_claim(c) for c in unsupported],
            contradicted_claims=[_to_verified_claim(c) for c in contradicted],
            citation_errors=citation_errors,
            warnings=warnings,
            reasons=reasons,
        )


final_answer_verifier = FinalAnswerVerifier()
