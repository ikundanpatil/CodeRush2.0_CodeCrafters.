"""Phase 8 policy domain models.

Kept independent of every other module (no imports from src.engine,
src.evolution, src.sandbox, etc.) so the policy layer can be reasoned about,
tested, and reused on its own.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PolicyAction(str, Enum):
    SEARCH = "SEARCH"
    BROWSE = "BROWSE"
    STORE_MEMORY = "STORE_MEMORY"
    BUILD_EVIDENCE_GRAPH = "BUILD_EVIDENCE_GRAPH"
    EXECUTE_SANDBOX = "EXECUTE_SANDBOX"
    EVOLVE_STRATEGY = "EVOLVE_STRATEGY"
    APPLY_STRATEGY = "APPLY_STRATEGY"
    MODIFY_CODE = "MODIFY_CODE"
    MODIFY_SECURITY = "MODIFY_SECURITY"
    MODIFY_POLICY = "MODIFY_POLICY"
    ACCESS_SECRET = "ACCESS_SECRET"
    EXECUTE_HOST_COMMAND = "EXECUTE_HOST_COMMAND"
    UNKNOWN = "UNKNOWN"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"


class PolicyRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyRequest(BaseModel):
    action: PolicyAction
    actor: str = "system"
    target: Optional[str] = None
    # Structured parameters only (e.g. a candidate strategy's numeric
    # fields). Never put secrets here -- PolicyResult/audit logging assume
    # this dict is safe to summarize/log.
    parameters: Dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None
    strategy_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    decision: PolicyDecision
    risk: PolicyRisk
    reason: str
    policy_rule: str
    action: PolicyAction
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
