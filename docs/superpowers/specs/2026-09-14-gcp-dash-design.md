# gcp-dash Design


### Context

`/Users/kenmoini/Development/gcp-dash` is empty. The app is a demo/teaching tool: run it in Podman or on Kubernetes/OpenShift, watch what the platform sees, break the health probes to show how the orchestrator reacts, and browse a GCP project's resources from the same UI.

### Decisions (from brainstorming)

| Topic | Decision |
|---|---|
| GCP access | Python client libraries via Application Default Credentials (service-account JSON key mounted as a Secret). No `gcloud` binary in the image. |
| GCP resources shown | Project metadata, Compute Engine instances, Cloud Storage buckets, VPC networks, subnetworks, firewall rules. (No GKE.) |
| Container controls | Independent liveness and readiness toggles, CPU load toggle (N worker processes), crash/exit with chosen exit code. |
| Web stack | FastAPI + Jinja2 + HTMX, server-rendered. |
| GCP fetch strategy | Per-resource in-memory TTL cache (default 60 s) with "last fetched" timestamp and Refresh button. |
| Deployment | Kubernetes manifests (kustomize) + OpenShift Route overlay. Podman run script for local. |

### Pages and endpoints

| Path | Method | Purpose |
|---|---|---|
| `/` | GET | Runtime page: container info panel (auto-refresh every 5 s) + controls panel |
| `/gcp` | GET | GCP page: six panels, each lazily loaded via HTMX |
| `/partials/runtime` | GET | HTML fragment: runtime info |
| `/partials/controls` | GET | HTML fragment: controls with current state |
| `/partials/gcp/{kind}` | GET | HTML fragment for `project|instances|buckets|networks|subnetworks|firewalls`; `?refresh=1` forces reload |
| `/healthz/live` | GET | 200 `{"status":"ok"}` or 503 when liveness disabled |
| `/healthz/ready` | GET | 200 or 503 when readiness disabled |
| `/controls/liveness` | POST form `enabled` | Toggle liveness. Returns controls fragment if `HX-Request`, else JSON state |
| `/controls/readiness` | POST form `enabled` | Same for readiness |
| `/controls/cpu` | POST form `enabled`, `workers` | Start/stop CPU burner processes |
| `/controls/crash` | POST form `exit_code` | Responds 202 then `os._exit(exit_code)` after 0.5 s |
| `/api/state` | GET | JSON: live, ready, uptime, cpu load status |
| `/api/runtime` | GET | JSON: full runtime info |
| `/api/gcp/{kind}` | GET | JSON `{kind, fetched_at, error, items}`; `?refresh=true` forces |
| `/api/gcp/refresh` | POST | Invalidate all cached GCP data, 204 |

### Runtime detection rules

- `runtime`: `podman` if `/run/.containerenv` exists; `docker` if `/.dockerenv` exists; else value of `$container` env if set; else scan `/proc/self/cgroup` for `crio`, `containerd`, `docker`, `kubepods`; else `none`.
- `orchestrator`: `kubernetes` if `$KUBERNETES_SERVICE_HOST` set or `/var/run/secrets/kubernetes.io/serviceaccount/namespace` exists; else `none`.
- Pod identity from Downward-API env vars; namespace falls back to the serviceaccount namespace file.
- Limits: cgroup v2 `cpu.max`, `memory.max`, `memory.current`; fallback cgroup v1 `cpu/cpu.cfs_quota_us`, `cpu/cpu.cfs_period_us`, `memory/memory.limit_in_bytes`, `memory/memory.usage_in_bytes`. `max` or negative → unlimited (`None`).
- Also: hostname, `/etc/os-release` PRETTY_NAME, Python version, uid/gid/pid, `os.cpu_count()`, 1-minute load average, uptime since app start.

### GCP IAM/API requirements (documented in README)

APIs: `compute.googleapis.com`, `storage.googleapis.com`, `cloudresourcemanager.googleapis.com`. Role: `roles/viewer` on the project (covers `compute.*.list`, `storage.buckets.list`, `resourcemanager.projects.get`).

### File structure

```
gcp-dash/
├── pyproject.toml, uv.lock, requirements.txt (exported), .gitignore, .containerignore
├── Containerfile
├── README.md
├── docs/superpowers/{specs,plans}/2026-09-14-gcp-dash-*.md
├── scripts/run-podman.sh
├── deploy/
│   ├── kubernetes/  kustomization.yaml, namespace.yaml, configmap.yaml, secret.example.yaml, deployment.yaml, service.yaml
│   └── openshift/   kustomization.yaml, route.yaml
├── src/gcp_dash/
│   ├── __init__.py          __version__
│   ├── main.py              create_app(); module-level `app`
│   ├── config.py            Settings dataclass, from_env()
│   ├── deps.py              FastAPI dependency accessors for app.state
│   ├── state.py             RuntimeState (live/ready flags, started_at)
│   ├── runtime_info.py      collect(root, env) -> RuntimeInfo
│   ├── cpu_load.py          CpuLoad (spawned busy-loop workers)
│   ├── templating.py        Jinja2Templates instance, is_htmx(request)
│   ├── gcp/
│   │   ├── models.py        dataclasses: Project, Instance, Bucket, Network, Subnetwork, FirewallRule
│   │   ├── provider.py      GcpProvider Protocol, GcpError, LiveGcpProvider, pure mapping fns
│   │   ├── cache.py         TTLCache, CacheEntry
│   │   └── service.py       GcpService (kind -> cached provider call)
│   ├── routers/
│   │   ├── health.py  controls.py  runtime.py  gcp.py  pages.py
│   ├── templates/
│   │   ├── base.html, index.html, gcp.html
│   │   └── partials/ runtime.html, controls.html, gcp_project.html, gcp_instances.html,
│   │                 gcp_buckets.html, gcp_networks.html, gcp_subnetworks.html, gcp_firewalls.html, gcp_error.html
│   └── static/ htmx.min.js, style.css
└── tests/
    ├── conftest.py (FakeGcpProvider, app/client fixtures)
    ├── test_config.py test_state.py test_health.py test_controls.py test_runtime_info.py
    ├── test_cpu_load.py test_cache.py test_provider_mapping.py test_gcp_service.py test_gcp_api.py test_pages.py
```

### Testing strategy

- Unit tests for pure logic (`runtime_info`, `cache`, provider mapping functions, `Settings`).
- Router tests with `fastapi.testclient.TestClient` against `create_app(settings, gcp_provider=FakeGcpProvider())`.
- Crash endpoint is testable because `create_app` stores the exit function on `app.state.exit_fn`; tests replace it with a recorder.
- No test ever contacts GCP. `LiveGcpProvider` is exercised only by the manual smoke test in Task 9/10.

