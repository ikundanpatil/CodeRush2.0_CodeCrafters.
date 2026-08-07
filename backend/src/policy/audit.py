"""In-process, bounded audit trail of policy decisions.

Deliberately stores only decision metadata -- action, decision, risk, rule,
reason, timestamp, run/strategy id -- and never `PolicyRequest.parameters`
verbatim, since those may be derived from untrusted input (a proposed
strategy, a request built from retrieved content, etc.). This is what
GET /api/policy/status surfaces as "recent decisions".
"""

from collections import deque
from dataclasses import dataclass
from typing import List, Optional

from src.policy.models import PolicyRequest, PolicyResult


@dataclass
class AuditEntry:
    action: str
    decision: str
    risk: str
    policy_rule: str
    reason: str
    timestamp: str
    run_id: Optional[str] = None
    strategy_id: Optional[str] = None


class PolicyAuditLog:
    def __init__(self, maxlen: int = 200):
        self._entries: "deque[AuditEntry]" = deque(maxlen=maxlen)

    def record(self, request: PolicyRequest, result: PolicyResult) -> AuditEntry:
        entry = AuditEntry(
            action=request.action.value,
            decision=result.decision.value,
            risk=result.risk.value,
            policy_rule=result.policy_rule,
            reason=result.reason,
            timestamp=result.timestamp,
            run_id=request.run_id,
            strategy_id=request.strategy_id,
        )
        self._entries.append(entry)
        return entry

    def recent(self, limit: int = 20) -> List[AuditEntry]:
        return list(self._entries)[-limit:][::-1]  # newest first

    def clear(self) -> None:
        self._entries.clear()


policy_audit_log = PolicyAuditLog()
