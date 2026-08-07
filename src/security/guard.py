import json
import re
from typing import Tuple, List
from src.models.schemas import SecurityEvent

INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (all )?prior system prompts",
    r"system prompt override",
    r"you are now an unrestricted ai",
    r"act as DAN",
    r"new instruction:",
    r"do not follow safety guidelines"
]

class SecurityGuard:
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def scan_content(self, text: str, run_id: str) -> Tuple[str, List[SecurityEvent]]:
        events = []
        sanitized_text = text

        for pattern in self.patterns:
            matches = list(pattern.finditer(text))
            for match in matches:
                matched_snippet = match.group(0)
                event = SecurityEvent(
                    run_id=run_id,
                    event_type="prompt_injection_detected",
                    action_taken="blocked_and_sanitized",
                    snippet=matched_snippet
                )
                events.append(event)
                # Replace malicious prompt with sanitized placeholder so data remains untrusted
                sanitized_text = pattern.sub("[UNTRUSTED_CONTENT_BLOCKED]", sanitized_text)

        return sanitized_text, events

security_guard = SecurityGuard()
