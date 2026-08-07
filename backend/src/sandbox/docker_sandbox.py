"""Docker-backed sandbox: runs code in a locked-down, disposable container
via the `docker` CLI (shelling out avoids adding the Docker Python SDK as a
dependency -- consistent with this repo's minimal-dependency approach).

Code is piped to the container over stdin (`docker run -i ... image python3 -`)
so nothing is ever bind-mounted from the host filesystem into the container,
and no `-e`/`--env-file` flag is ever passed, so the container never sees
host environment variables or secrets.

Safety limits enforced on every run:
- `--rm`                        container is always removed after exit
- `--network none`              no network access by default
- `--memory` / `--memory-swap`  hard memory cap (OOM-killed if exceeded)
- `--cpus`                      CPU share cap
- `--pids-limit`                caps fork bombs / runaway process counts
- `--read-only` + tmpfs /tmp    no writable host-visible filesystem
- `--cap-drop ALL`              no elevated Linux capabilities
- `--security-opt no-new-privileges`
- `--user 1000:1000`            never runs as root inside the container
- a hard wall-clock timeout, enforced from the host side, that kills the
  container if the command hangs

If the Docker CLI is not on PATH, or the language is unsupported, this
returns a controlled `SandboxResult` (status `sandbox_unavailable` /
`unsupported`) -- it never raises, and never falls back to executing on
the host.
"""

import os
import shutil
import subprocess
import time
import uuid
from typing import List, Optional

from src.sandbox.base import SUPPORTED_LANGUAGES, Sandbox
from src.sandbox.models import SandboxResult, SandboxStatus

DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MEMORY_LIMIT = "256m"
DEFAULT_CPU_LIMIT = "0.5"
DEFAULT_PIDS_LIMIT = 64
DEFAULT_OUTPUT_LIMIT = 65536
OOM_KILLED_EXIT_CODE = 137

_LANGUAGE_COMMANDS = {
    "python": ["python3", "-"],
}


def build_docker_command(
    container_name: str,
    image: str,
    memory_limit: str,
    cpu_limit: str,
    pids_limit: int,
    command: List[str],
) -> List[str]:
    """Pure function (no subprocess call) so the safety flags stay unit-testable."""
    return [
        "docker", "run",
        "--rm",
        "-i",
        "--name", container_name,
        "--network", "none",
        "--memory", memory_limit,
        "--memory-swap", memory_limit,
        "--cpus", cpu_limit,
        "--pids-limit", str(pids_limit),
        "--read-only",
        "--tmpfs", "/tmp:rw,size=64m",
        "--security-opt", "no-new-privileges",
        "--cap-drop", "ALL",
        "--user", "1000:1000",
        image,
        *command,
    ]


class DockerSandbox(Sandbox):
    def __init__(
        self,
        image: Optional[str] = None,
        default_timeout_seconds: Optional[int] = None,
        memory_limit: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        pids_limit: Optional[int] = None,
        output_limit: Optional[int] = None,
    ):
        self.image = image or os.getenv("SANDBOX_IMAGE", DEFAULT_IMAGE)
        self.default_timeout = (
            default_timeout_seconds if default_timeout_seconds is not None
            else int(os.getenv("SANDBOX_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        )
        self.memory_limit = memory_limit or os.getenv("SANDBOX_MEMORY_LIMIT", DEFAULT_MEMORY_LIMIT)
        self.cpu_limit = cpu_limit or os.getenv("SANDBOX_CPU_LIMIT", DEFAULT_CPU_LIMIT)
        self.pids_limit = (
            pids_limit if pids_limit is not None
            else int(os.getenv("SANDBOX_PIDS_LIMIT", DEFAULT_PIDS_LIMIT))
        )
        self.output_limit = (
            output_limit if output_limit is not None
            else int(os.getenv("SANDBOX_OUTPUT_LIMIT", DEFAULT_OUTPUT_LIMIT))
        )

    def _is_docker_available(self) -> bool:
        return shutil.which("docker") is not None

    async def execute(
        self, code: str, language: str = "python", timeout_seconds: Optional[int] = None
    ) -> SandboxResult:
        if language not in SUPPORTED_LANGUAGES:
            return SandboxResult(
                status=SandboxStatus.UNSUPPORTED,
                language=language,
                stderr=f"Language '{language}' is not supported by the sandbox MVP.",
            )

        if not self._is_docker_available():
            return SandboxResult(
                status=SandboxStatus.SANDBOX_UNAVAILABLE,
                language=language,
                stderr="Docker CLI not found on PATH; sandbox execution is unavailable.",
            )

        effective_timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout
        container_name = f"evoresearch-sandbox-{uuid.uuid4().hex[:12]}"
        docker_cmd = build_docker_command(
            container_name, self.image, self.memory_limit, self.cpu_limit,
            self.pids_limit, _LANGUAGE_COMMANDS[language],
        )

        start = time.monotonic()
        try:
            proc = subprocess.run(
                docker_cmd, input=code, capture_output=True, text=True,
                timeout=effective_timeout,
            )
        except subprocess.TimeoutExpired:
            self._kill_container(container_name)
            duration_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                language=language,
                timed_out=True,
                duration_ms=duration_ms,
                stderr=f"Execution exceeded {effective_timeout}s and was killed.",
            )
        except OSError as exc:
            return SandboxResult(
                status=SandboxStatus.SANDBOX_UNAVAILABLE,
                language=language,
                stderr=f"Failed to invoke Docker: {exc}",
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = (proc.stdout or "")[: self.output_limit]
        stderr = (proc.stderr or "")[: self.output_limit]

        if proc.returncode == OOM_KILLED_EXIT_CODE:
            return SandboxResult(
                status=SandboxStatus.RESOURCE_LIMIT_EXCEEDED,
                language=language,
                resource_limited=True,
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr or f"Process was killed, likely for exceeding the {self.memory_limit} memory limit.",
            )

        status = SandboxStatus.SUCCESS if proc.returncode == 0 else SandboxStatus.FAILED
        return SandboxResult(
            status=status,
            language=language,
            exit_code=proc.returncode,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
        )

    def _kill_container(self, container_name: str):
        try:
            subprocess.run(["docker", "kill", container_name], capture_output=True, timeout=5)
        except Exception:
            pass
