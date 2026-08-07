"""Sandbox-internal exceptions.

These are used internally by provider implementations while building a
result; they never cross the `Sandbox.execute()` boundary. Callers only
ever see a `SandboxResult` with a controlled `status` -- a sandbox failure
(unsupported language, Docker missing, timeout, resource limit) is always
reported as data, never as an unhandled exception that could crash the
backend or a research run.
"""


class SandboxError(Exception):
    """Base class for all sandbox failures."""


class SandboxUnsupportedLanguageError(SandboxError):
    """The requested language is not supported by this MVP."""


class SandboxUnavailableError(SandboxError):
    """The underlying execution backend (e.g. Docker) is not available."""


class SandboxTimeoutError(SandboxError):
    """Execution exceeded the configured timeout and was killed."""


class SandboxResourceLimitError(SandboxError):
    """Execution was killed for exceeding a resource limit (memory/CPU/pids)."""
