"""Shared helper for getting Pydantic-validated JSON out of an LLMAdapter.

Used by the orchestrator (plan/report) and the Phase 4 evidence pipeline
(claim extraction, relationship classification) so the retry/validate logic
lives in exactly one place.
"""

import json
from typing import Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.llm.base import LLMAdapter, LLMError

ModelT = TypeVar("ModelT", bound=BaseModel)


async def generate_structured(
    llm: LLMAdapter,
    system_prompt: str,
    prompt: str,
    model_cls: Type[ModelT],
    retries: int = 1,
) -> Tuple[Optional[ModelT], Optional[Exception]]:
    """Call the LLM and validate its JSON output against model_cls.

    Retries up to `retries` extra times with a stricter prompt on invalid
    JSON/schema. Never raises: returns (None, error) on total failure so
    callers can apply their own fallback and emit their own AgentEvent.
    """
    last_error: Optional[Exception] = None
    current_prompt = prompt

    for _ in range(retries + 1):
        try:
            raw = await llm.generate(current_prompt, system_prompt=system_prompt, response_format="json")
            data = json.loads(raw)
            return model_cls.model_validate(data), None
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            current_prompt = (
                current_prompt
                + "\n\nYour previous response was not valid JSON matching the required schema. "
                "Respond with ONLY the raw JSON object -- no markdown fences, no commentary."
            )
        except LLMError as e:
            last_error = e
            break
        except Exception as e:  # noqa: BLE001 - last-resort safety net
            last_error = e
            break

    return None, last_error
