import asyncio

from src.sandbox.base import SUPPORTED_LANGUAGES
from src.sandbox.docker_sandbox import DockerSandbox
from src.sandbox.mock import (
    FORCE_FAILURE_MARKER,
    FORCE_RESOURCE_LIMIT_MARKER,
    FORCE_TIMEOUT_MARKER,
    MockSandbox,
)
from src.sandbox.models import SandboxResult, SandboxStatus


# --------------------------------------------------------------------------
# MockSandbox: deterministic scenarios, no Docker required
# --------------------------------------------------------------------------

def test_mock_sandbox_successful_execution():
    result = asyncio.run(MockSandbox().execute("print('hello')", language="python"))
    assert result.status == SandboxStatus.SUCCESS
    assert result.succeeded is True
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.resource_limited is False
    assert "hello" in result.stdout


def test_mock_sandbox_failed_execution():
    result = asyncio.run(MockSandbox().execute(f"raise ValueError()\n{FORCE_FAILURE_MARKER}"))
    assert result.status == SandboxStatus.FAILED
    assert result.succeeded is False
    assert result.exit_code == 1
    assert result.timed_out is False
    assert result.resource_limited is False


def test_mock_sandbox_timeout():
    result = asyncio.run(
        MockSandbox().execute(f"while True: pass\n{FORCE_TIMEOUT_MARKER}", timeout_seconds=5)
    )
    assert result.status == SandboxStatus.TIMEOUT
    assert result.timed_out is True
    assert result.succeeded is False
    assert result.duration_ms == 5000


def test_mock_sandbox_resource_limit_exceeded():
    result = asyncio.run(MockSandbox().execute(f"a = []\n{FORCE_RESOURCE_LIMIT_MARKER}"))
    assert result.status == SandboxStatus.RESOURCE_LIMIT_EXCEEDED
    assert result.resource_limited is True
    assert result.succeeded is False


def test_mock_sandbox_unsupported_language():
    result = asyncio.run(MockSandbox().execute("console.log(1)", language="javascript"))
    assert result.status == SandboxStatus.UNSUPPORTED
    assert "javascript" not in SUPPORTED_LANGUAGES


def test_mock_sandbox_never_uses_eval_or_exec():
    import inspect

    from src.sandbox import mock as mock_module

    source = inspect.getsource(mock_module)
    assert "eval(" not in source
    assert "exec(" not in source


def test_docker_sandbox_unavailable_when_docker_missing(monkeypatch):
    sandbox = DockerSandbox()
    monkeypatch.setattr(sandbox, "_is_docker_available", lambda: False)
    result = asyncio.run(sandbox.execute("print('hi')"))
    assert result.status == SandboxStatus.SANDBOX_UNAVAILABLE
    # Never falls back to running on the host -- no exception, no real execution.


def test_docker_sandbox_unsupported_language_before_docker_check(monkeypatch):
    sandbox = DockerSandbox()
    monkeypatch.setattr(sandbox, "_is_docker_available", lambda: True)
    result = asyncio.run(sandbox.execute("1 + 1", language="ruby"))
    assert result.status == SandboxStatus.UNSUPPORTED


def test_sandbox_result_schema():
    result = asyncio.run(MockSandbox().execute("print(1)"))
    assert isinstance(result, SandboxResult)
    for field in (
        "execution_id", "status", "stdout", "stderr", "exit_code",
        "duration_ms", "timed_out", "resource_limited", "language",
    ):
        assert hasattr(result, field)


def test_sandbox_output_truncation():
    sandbox = MockSandbox(output_limit=50)
    long_code = "print('x')\n" * 100
    result = asyncio.run(sandbox.execute(long_code))
    assert len(result.stdout) <= 50


def test_docker_command_never_bind_mounts_host_or_passes_env_secrets():
    from src.sandbox.docker_sandbox import build_docker_command

    cmd = build_docker_command(
        "test-container", "python:3.11-slim", "256m", "0.5", 64, ["python3", "-"],
    )
    assert "--rm" in cmd
    assert "--network" in cmd and "none" in cmd
    assert "--read-only" in cmd
    assert "--pids-limit" in cmd
    assert "--user" in cmd and "1000:1000" in cmd
    assert "--cap-drop" in cmd and "ALL" in cmd
    # No bind mount (-v) of the host filesystem, and no env vars/secrets passed.
    assert "-v" not in cmd
    assert "--volume" not in cmd
    assert "-e" not in cmd
    assert "--env" not in cmd
    assert "--env-file" not in cmd
    assert "/var/run/docker.sock" not in " ".join(cmd)
