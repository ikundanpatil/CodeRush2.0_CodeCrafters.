"""Phase 8 policy exceptions."""


class PolicyError(Exception):
    """Base class for policy-layer errors."""


class PolicyDeniedError(PolicyError):
    """Raised when code explicitly requires ALLOW (via
    `PolicyEngine.require_allow`) and the request was denied."""

    def __init__(self, result):
        self.result = result
        super().__init__(f"Policy denied {result.action.value}: {result.reason}")
