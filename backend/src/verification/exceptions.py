class VerificationError(Exception):
    """Base class for verification-layer errors. The verifier itself never
    raises during normal operation (it always returns a VerificationResult,
    even for a fully-unsupported answer) -- reserved for genuinely
    unexpected failures in callers that choose to be strict."""
