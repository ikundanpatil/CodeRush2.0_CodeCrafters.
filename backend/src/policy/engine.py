"""Phase 8 deterministic Policy Engine.

No branch in `evaluate()` depends on an LLM response -- action -> decision
is a fixed table plus, for strategy actions, the pure bounds/allowlist
validation in `rules.py`. This is intentional: security-critical decisions
must be reproducible from config alone (see module docstring in rules.py).
"""

from datetime import datetime, timezone
from typing import Callable, Optional

from src.policy import rules
from src.policy.audit import policy_audit_log
from src.policy.exceptions import PolicyDeniedError
from src.policy.models import PolicyAction, PolicyDecision, PolicyRequest, PolicyResult, PolicyRisk

# Research actions the agent needs to operate at all. Always ALLOW -- the
# policy engine's role here is observability/audit (every sensitive action
# is explicitly evaluated and logged), not gating, since these are not
# actions that should ever be blocked in normal operation.
_ALWAYS_ALLOW = {
    PolicyAction.SEARCH,
    PolicyAction.BROWSE,
    PolicyAction.STORE_MEMORY,
    PolicyAction.BUILD_EVIDENCE_GRAPH,
    PolicyAction.EXECUTE_SANDBOX,
}

# Actions that can never be permitted through the policy layer, no matter
# who/what requests them -- including content the LLM produced from
# untrusted retrieved text. Deliberately a fixed set, not derived from
# anything the LLM or evolution system can influence.
_ALWAYS_DENY_CRITICAL = {
    PolicyAction.MODIFY_CODE,
    PolicyAction.MODIFY_SECURITY,
    PolicyAction.MODIFY_POLICY,
    PolicyAction.EXECUTE_HOST_COMMAND,
}

_STRATEGY_ACTIONS = {PolicyAction.EVOLVE_STRATEGY, PolicyAction.APPLY_STRATEGY}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PolicyEngine:
    def __init__(self, event_sink: Optional[Callable[..., None]] = None):
        self._event_sink = event_sink

    def set_event_sink(self, sink: Optional[Callable[..., None]]):
        self._event_sink = sink

    def _emit(self, event_type: str, title: str, message: str, data: Optional[dict] = None):
        if self._event_sink is not None:
            try:
                self._event_sink(event_type, title, message, data)
            except Exception:
                pass

    # -- core dispatch -------------------------------------------------------
    def evaluate(self, request: PolicyRequest) -> PolicyResult:
        action = request.action

        if action in _STRATEGY_ACTIONS:
            result = self._evaluate_strategy(request)
        elif action == PolicyAction.ACCESS_SECRET:
            # Never echo request content back -- not even in the reason --
            # since it may itself be an attempt to smuggle a secret name/value.
            result = PolicyResult(
                decision=PolicyDecision.DENY,
                risk=PolicyRisk.CRITICAL,
                reason="secret_access_attempt: access to secrets is never permitted through the policy layer.",
                policy_rule="deny_secret_access",
                action=action,
                timestamp=_utc_now(),
            )
        elif action in _ALWAYS_DENY_CRITICAL:
            result = PolicyResult(
                decision=PolicyDecision.DENY,
                risk=PolicyRisk.CRITICAL,
                reason=f"{action.value} is not permitted through the policy layer.",
                policy_rule="deny_dangerous_action",
                action=action,
                timestamp=_utc_now(),
            )
        elif action in _ALWAYS_ALLOW:
            result = PolicyResult(
                decision=PolicyDecision.ALLOW,
                risk=PolicyRisk.LOW,
                reason=f"{action.value} is within approved research boundaries.",
                policy_rule="always_allow",
                action=action,
                timestamp=_utc_now(),
            )
        else:
            # UNKNOWN, or any action string the caller couldn't map to a
            # known PolicyAction -- deny by default rather than guess.
            result = PolicyResult(
                decision=PolicyDecision.DENY,
                risk=PolicyRisk.HIGH,
                reason="Action is not recognized by the policy engine and is denied by default.",
                policy_rule="deny_unknown_action",
                action=PolicyAction.UNKNOWN,
                timestamp=_utc_now(),
            )

        policy_audit_log.record(request, result)
        self._emit_decision(request, result)
        return result

    def require_allow(self, request: PolicyRequest) -> PolicyResult:
        """Like `evaluate`, but raises PolicyDeniedError instead of returning
        a DENY/REQUIRE_REVIEW result -- for call sites that cannot proceed
        without an explicit ALLOW (e.g. sandbox execution)."""
        result = self.evaluate(request)
        if result.decision != PolicyDecision.ALLOW:
            raise PolicyDeniedError(result)
        return result

    def _evaluate_strategy(self, request: PolicyRequest) -> PolicyResult:
        candidate = request.parameters.get("strategy", request.parameters)
        validation = rules.validate_strategy_candidate(candidate)
        return PolicyResult(
            decision=PolicyDecision.ALLOW if validation.ok else PolicyDecision.DENY,
            risk=validation.risk,
            reason=validation.reason,
            policy_rule="evolution_boundary",
            action=request.action,
            timestamp=_utc_now(),
        )

    def _emit_decision(self, request: PolicyRequest, result: PolicyResult):
        from src.models.schemas import EventType

        event_type = {
            PolicyDecision.ALLOW: EventType.POLICY_ALLOWED,
            PolicyDecision.DENY: EventType.POLICY_DENIED,
            PolicyDecision.REQUIRE_REVIEW: EventType.POLICY_REVIEW_REQUIRED,
        }[result.decision]
        self._emit(
            event_type.value,
            f"Policy {result.decision.value}: {request.action.value}",
            result.reason,
            {
                "action": request.action.value,
                "decision": result.decision.value,
                "risk": result.risk.value,
                "policy_rule": result.policy_rule,
                "run_id": request.run_id,
                "strategy_id": request.strategy_id,
            },
        )

    # -- sandbox integration --------------------------------------------------
    async def execute_sandboxed(
        self, code: str, language: str = "python", timeout_seconds: int = 10,
        run_id: Optional[str] = None,
    ):
        """The only sanctioned way to run agent/LLM-produced code: policy
        check first, then delegate to the existing Sandbox abstraction
        (src/sandbox/) -- never os.system/subprocess/shell on the host."""
        from src.sandbox.factory import get_sandbox

        self.require_allow(PolicyRequest(
            action=PolicyAction.EXECUTE_SANDBOX, target="sandbox", run_id=run_id,
        ))
        return await get_sandbox().execute(code, language=language, timeout_seconds=timeout_seconds)


policy_engine = PolicyEngine()
