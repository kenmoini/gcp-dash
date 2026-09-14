from pathlib import Path

from gcp_dash.runtime_info import collect, detect_orchestrator, detect_runtime, read_cgroup_limits


def _mk(root: Path, rel: str, content: str = "") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_detect_podman(tmp_path):
    _mk(tmp_path, "run/.containerenv")
    assert detect_runtime(tmp_path, {}) == "podman"


def test_detect_docker(tmp_path):
    _mk(tmp_path, ".dockerenv")
    assert detect_runtime(tmp_path, {}) == "docker"


def test_detect_from_container_env(tmp_path):
    assert detect_runtime(tmp_path, {"container": "oci"}) == "oci"


def test_detect_crio_from_cgroup(tmp_path):
    _mk(tmp_path, "proc/self/cgroup", "0::/kubepods.slice/kubepods-pod1.slice/crio-abc.scope\n")
    assert detect_runtime(tmp_path, {}) == "cri-o"


def test_detect_none(tmp_path):
    _mk(tmp_path, "proc/self/cgroup", "0::/\n")
    assert detect_runtime(tmp_path, {}) == "none"


def test_orchestrator_kubernetes_via_env(tmp_path):
    assert detect_orchestrator(tmp_path, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}) == "kubernetes"


def test_orchestrator_kubernetes_via_sa_file(tmp_path):
    _mk(tmp_path, "var/run/secrets/kubernetes.io/serviceaccount/namespace", "demo")
    assert detect_orchestrator(tmp_path, {}) == "kubernetes"


def test_orchestrator_none(tmp_path):
    assert detect_orchestrator(tmp_path, {}) == "none"


def test_cgroup_v2_limits(tmp_path):
    _mk(tmp_path, "sys/fs/cgroup/cpu.max", "50000 100000\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.max", "268435456\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.current", "1048576\n")
    cpu, mem, usage = read_cgroup_limits(tmp_path)
    assert cpu == 0.5
    assert mem == 268435456
    assert usage == 1048576


def test_cgroup_v2_unlimited(tmp_path):
    _mk(tmp_path, "sys/fs/cgroup/cpu.max", "max 100000\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.max", "max\n")
    cpu, mem, usage = read_cgroup_limits(tmp_path)
    assert cpu is None and mem is None and usage is None


def test_cgroup_v1_fallback(tmp_path):
    _mk(tmp_path, "sys/fs/cgroup/cpu/cpu.cfs_quota_us", "200000\n")
    _mk(tmp_path, "sys/fs/cgroup/cpu/cpu.cfs_period_us", "100000\n")
    _mk(tmp_path, "sys/fs/cgroup/memory/memory.limit_in_bytes", "536870912\n")
    _mk(tmp_path, "sys/fs/cgroup/memory/memory.usage_in_bytes", "4096\n")
    cpu, mem, usage = read_cgroup_limits(tmp_path)
    assert cpu == 2.0 and mem == 536870912 and usage == 4096


def test_collect_reads_pod_env_and_os_release(tmp_path):
    _mk(tmp_path, "etc/os-release", 'NAME="Red Hat Enterprise Linux"\nPRETTY_NAME="Red Hat Enterprise Linux 10.0"\n')
    _mk(tmp_path, "var/run/secrets/kubernetes.io/serviceaccount/namespace", "from-file")
    info = collect(
        tmp_path,
        {"POD_NAME": "web-1", "NODE_NAME": "node-a", "POD_IP": "10.1.2.3", "KUBERNETES_SERVICE_HOST": "x"},
    )
    assert info.orchestrator == "kubernetes"
    assert info.pod["name"] == "web-1"
    assert info.pod["namespace"] == "from-file"
    assert info.pod["node"] == "node-a"
    assert info.os_release == "Red Hat Enterprise Linux 10.0"
    assert info.python_version.startswith("3.")


def test_cgroup_v2_malformed_cpu_max(tmp_path):
    _mk(tmp_path, "sys/fs/cgroup/cpu.max", "garbage 100000\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.max", "268435456\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.current", "1048576\n")
    cpu, mem, usage = read_cgroup_limits(tmp_path)
    assert cpu is None
    assert mem == 268435456
    assert usage == 1048576


def test_cgroup_v2_zero_period(tmp_path):
    _mk(tmp_path, "sys/fs/cgroup/cpu.max", "50000 0\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.max", "268435456\n")
    _mk(tmp_path, "sys/fs/cgroup/memory.current", "1048576\n")
    cpu, mem, usage = read_cgroup_limits(tmp_path)
    assert cpu == 0.5
    assert mem == 268435456
    assert usage == 1048576


def test_api_runtime_endpoint(client):
    body = client.get("/api/runtime").json()
    assert "runtime" in body and "orchestrator" in body
    assert body["state"]["live"] is True
