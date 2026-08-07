import os

from src.sandbox.base import Sandbox
from src.sandbox.docker_sandbox import DockerSandbox
from src.sandbox.mock import MockSandbox

_PROVIDERS = {
    "mock": MockSandbox,
    "docker": DockerSandbox,
}


def get_sandbox(provider: str | None = None) -> Sandbox:
    """Return a Sandbox for the requested provider.

    Reads SANDBOX_PROVIDER from the environment when provider is not given.
    Defaults to "mock" so the app and test suite work offline, without
    Docker, out of the box. If SANDBOX_ENABLED=false, sandbox execution is
    disabled entirely and the mock provider (which performs no real
    execution) is always used regardless of SANDBOX_PROVIDER.
    """
    enabled = os.getenv("SANDBOX_ENABLED", "true").strip().lower() != "false"
    if not enabled:
        return MockSandbox()

    name = (provider or os.getenv("SANDBOX_PROVIDER") or "mock").strip().lower()
    provider_cls = _PROVIDERS.get(name, MockSandbox)
    return provider_cls()
