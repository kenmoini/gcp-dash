from __future__ import annotations

import os
import platform
import socket
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

_CGROUP_HINTS = (("crio", "cri-o"), ("containerd", "containerd"), ("docker", "docker"), ("kubepods", "kubernetes"))
_SA_NAMESPACE = "var/run/secrets/kubernetes.io/serviceaccount/namespace"


@dataclass
class RuntimeInfo:
    hostname: str
    runtime: str
    orchestrator: str
    pod: dict[str, str | None]
    os_release: str
    python_version: str
    uid: int
    gid: int
    pid: int
    cpu_count: int | None
    cpu_limit: float | None
    memory_limit_bytes: int | None
    memory_usage_bytes: int | None
    load_average_1m: float | None
    env_hints: dict[str, str] = field(default_factory=dict)


def _read(root: Path, rel: str) -> str | None:
    p = root / rel
    try:
        return p.read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def detect_runtime(root: Path, env: Mapping[str, str]) -> str:
    if (root / "run/.containerenv").exists():
        return "podman"
    if (root / ".dockerenv").exists():
        return "docker"
    if env.get("container"):
        return env["container"]
    cgroup = _read(root, "proc/self/cgroup") or ""
    for needle, name in _CGROUP_HINTS:
        if needle in cgroup:
            return name
    return "none"


def detect_orchestrator(root: Path, env: Mapping[str, str]) -> str:
    if env.get("KUBERNETES_SERVICE_HOST") or (root / _SA_NAMESPACE).exists():
        return "kubernetes"
    return "none"


def _int_or_none(text: str | None) -> int | None:
    if text is None or text == "max":
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return None if value < 0 or value >= 2**62 else value


def read_cgroup_limits(root: Path) -> tuple[float | None, int | None, int | None]:
    """Return (cpu_limit_cores, memory_limit_bytes, memory_usage_bytes); None means unlimited/unknown."""
    cpu_max = _read(root, "sys/fs/cgroup/cpu.max")
    if cpu_max is not None:  # cgroup v2
        quota, _, period_str = cpu_max.partition(" ")
        quota_int = _int_or_none(quota)
        period_int = _int_or_none(period_str) or 100000
        cpu = None if quota_int is None else round(quota_int / period_int, 2)
        return (
            cpu,
            _int_or_none(_read(root, "sys/fs/cgroup/memory.max")),
            _int_or_none(_read(root, "sys/fs/cgroup/memory.current")),
        )
    quota = _int_or_none(_read(root, "sys/fs/cgroup/cpu/cpu.cfs_quota_us"))
    period = _int_or_none(_read(root, "sys/fs/cgroup/cpu/cpu.cfs_period_us")) or 100000
    cpu = None if quota is None or period == 0 else round(quota / period, 2)
    return (
        cpu,
        _int_or_none(_read(root, "sys/fs/cgroup/memory/memory.limit_in_bytes")),
        _int_or_none(_read(root, "sys/fs/cgroup/memory/memory.usage_in_bytes")),
    )


def _os_release(root: Path) -> str:
    text = _read(root, "etc/os-release") or ""
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return platform.platform()


def collect(root: Path = Path("/"), env: Mapping[str, str] | None = None) -> RuntimeInfo:
    env = os.environ if env is None else env
    cpu, mem, usage = read_cgroup_limits(root)
    try:
        load1 = round(os.getloadavg()[0], 2)
    except (OSError, AttributeError):
        load1 = None
    return RuntimeInfo(
        hostname=socket.gethostname(),
        runtime=detect_runtime(root, env),
        orchestrator=detect_orchestrator(root, env),
        pod={
            "name": env.get("POD_NAME"),
            "namespace": env.get("POD_NAMESPACE") or _read(root, _SA_NAMESPACE),
            "node": env.get("NODE_NAME"),
            "ip": env.get("POD_IP"),
            "service_account": env.get("SERVICE_ACCOUNT"),
        },
        os_release=_os_release(root),
        python_version=platform.python_version(),
        uid=os.getuid(),
        gid=os.getgid(),
        pid=os.getpid(),
        cpu_count=os.cpu_count(),
        cpu_limit=cpu,
        memory_limit_bytes=mem,
        memory_usage_bytes=usage,
        load_average_1m=load1,
        env_hints={k: v for k, v in env.items() if k in ("KUBERNETES_SERVICE_HOST", "container", "HOSTNAME")},
    )


def to_dict(info: RuntimeInfo) -> dict:
    return asdict(info)
