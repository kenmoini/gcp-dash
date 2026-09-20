# gcp-dash

Container runtime dashboard with health-probe controls and a GCP resource viewer. Runs on Red Hat UBI 10.

## What it does

- Shows how and where the container is running. Lets you flip its liveness and readiness probes, burn CPU, or crash it on demand.
- Shows Compute Engine VMs, Cloud Storage buckets, and VPC networking from a GCP project. Uses the Python client libraries.

## Endpoints

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

## Run locally

```bash
uv sync --python 3.12
uv run --python 3.12 uvicorn gcp_dash.main:app --reload --port 8080
```

The app listens on `http://localhost:8080`.

## Build the container

```bash
podman build --format docker -t localhost/gcp-dash:dev .
```

`--format docker` is required. The default OCI image format silently drops the `HEALTHCHECK` instruction. The runtime panel and the demo below rely on that instruction.

## Run with Podman

```bash
scripts/run-podman.sh [key.json] [project-id]
```

`scripts/run-podman.sh [key.json] [project-id]` mounts the key at `/var/secrets/gcp/key.json`. It sets `GOOGLE_APPLICATION_CREDENTIALS` to that path. If you omit the project-id argument, it sets `GCP_PROJECT` from `$GCP_PROJECT` instead. Both arguments are optional. If you do not supply a key, the GCP panels show an error banner instead of data.

Inside Podman the runtime panel reports `runtime: podman`, UID `1001`, and the `--cpus`/`--memory` limits the container was started with.

### Healthcheck flip demo

With the container running, disable liveness and watch the container healthcheck flip:

```bash
curl -s -X POST -d enabled=false localhost:8080/controls/liveness
sleep 35
podman inspect --format '{{.State.Health.Status}}' gcp-dash
```

After about 30 seconds `podman inspect` reports `unhealthy`. Re-enable liveness (`enabled=true`) and it returns to `healthy`.

## GCP setup

Create a service account with read-only access to the project you want to browse:

```bash
PROJECT=my-project
gcloud services enable compute.googleapis.com storage.googleapis.com cloudresourcemanager.googleapis.com --project "$PROJECT"
gcloud iam service-accounts create gcp-dash --project "$PROJECT"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member "serviceAccount:gcp-dash@${PROJECT}.iam.gserviceaccount.com" --role roles/viewer
gcloud iam service-accounts keys create key.json \
  --iam-account "gcp-dash@${PROJECT}.iam.gserviceaccount.com" --project "$PROJECT"
```

`roles/viewer` covers `compute.*.list`, `storage.buckets.list`, and `resourcemanager.projects.get`, which is everything the GCP page reads.

## Deploy to Kubernetes/OpenShift

The manifests live in `deploy/kubernetes` (base) and `deploy/openshift` (adds a Route on top of the Kubernetes base).

1. Push an image built from this repo to a registry, then edit the `images:` entry in `deploy/kubernetes/kustomization.yaml` to point `newName` at your registry instead of `quay.io/kenmoini/gcp-dash`.
2. Set `GCP_PROJECT` in `deploy/kubernetes/configmap.yaml` to the GCP project the service account can read.
3. Create the GCP key secret, either from the example file or directly from `kubectl`:

   ```bash
   cp deploy/kubernetes/secret.example.yaml deploy/kubernetes/secret.yaml
   # edit secret.yaml to paste in your key.json, then add it to kustomization.yaml resources
   ```

   or, without editing any file:

   ```bash
   kubectl create namespace gcp-dash
   kubectl create secret generic gcp-dash-sa-key --from-file=key.json -n gcp-dash
   ```

   The secret is optional: the Deployment mounts it with `optional: true`, so the app still starts without it (the GCP panels just show an error banner).

4. Apply the manifests:

   ```bash
   kubectl apply -k deploy/kubernetes
   # or, on OpenShift, for the Route as well:
   oc apply -k deploy/openshift
   ```

## Demo script

With the app deployed and a shell open on the cluster:

- **Readiness off.** Run `curl -X POST -d enabled=false <route>/controls/readiness`. Watch `kubectl get endpoints gcp-dash -w`. The pod drops out of the Service's endpoint list. It stays out until you re-enable readiness.
- **Liveness off.** Run `curl -X POST -d enabled=false <route>/controls/liveness`. Watch `kubectl get pods -w`. After about 15 seconds (3 failed probes at a 5-second period), the kubelet restarts the container.
- **CPU load.** Run `curl -X POST -d enabled=true -d workers=1 <route>/controls/cpu`. Watch `kubectl top pod`. CPU usage climbs toward the container's limit.
- **Crash.** Run `curl -X POST -d exit_code=1 <route>/controls/crash`. Watch `kubectl get pods -w`. The pod's restart count goes up by one.

## Security

The control endpoints (`/controls/liveness`, `/controls/readiness`, `/controls/cpu`, `/controls/crash`) and the GCP pages are unauthenticated by design. Anyone who can reach the app can restart it, saturate its CPU, drain it from the Service, and read the project's inventory: instance names and IPs, firewall rules, and error text that can include the service-account email. There is no CSRF protection. Set `CONTROLS_ENABLED=false` on any shared cluster. `GCP_DEBUG=true` writes Google API request and response payloads (the project's resource inventory) to the container log; leave it off unless you are actively debugging. Do not expose the Route or Service on the public internet. Use a read-only service account (`roles/viewer`) scoped to a throwaway project, not a production one.

## Configuration

| Variable | Set by | Purpose |
|---|---|---|
| `PORT` | ConfigMap / user | Port uvicorn listens on (default `8080`). Changing it also requires updating the Deployment's `containerPort`, the liveness/readiness probes, and the image `HEALTHCHECK`, which all assume 8080. |
| `GCP_PROJECT` | ConfigMap | GCP project ID the GCP page queries |
| `GCP_CACHE_TTL_SECONDS` | ConfigMap | TTL for the per-resource GCP cache in seconds (default `60`) |
| `CONTROLS_ENABLED` | ConfigMap | Whether the controls panel/endpoints are active (default `true`) |
| `LOG_LEVEL` | ConfigMap | Root log level for the app's own messages: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default `INFO`) |
| `GCP_DEBUG` | ConfigMap | `true` logs every Google API and token request/response and adds tracebacks to failed GCP fetches (default `false`). See [Troubleshooting GCP errors](#troubleshooting-gcp-errors). |
| `GOOGLE_APPLICATION_CREDENTIALS` | Deployment env | Path to the service-account key (`/var/secrets/gcp/key.json`), used by the GCP client libraries |
| `POD_NAME` | Downward API | Pod name shown in the runtime panel |
| `POD_NAMESPACE` | Downward API | Pod namespace shown in the runtime panel (falls back to the serviceaccount namespace file if unset) |
| `NODE_NAME` | Downward API | Node the pod is scheduled on |
| `POD_IP` | Downward API | Pod IP address |
| `SERVICE_ACCOUNT` | Downward API | Kubernetes service account the pod runs as |

## Troubleshooting GCP errors

When a GCP panel shows an error banner, the container log has the detail the banner does not.

At the default `LOG_LEVEL=INFO` the app logs:

- one line at startup with the version, project, cache TTL, and logging settings;
- one line the first time credentials load: the credential class (`Credentials` from `google.oauth2.service_account`, `external_account`, `compute_engine`, ...), the service-account email, the quota project, whether `GOOGLE_APPLICATION_CREDENTIALS` is set, and which project was resolved and from where;
- one `INFO` line per successful fetch with item count and duration, and one `WARNING` per failed fetch with the exception class and message. With the default 60 s cache that is at most one line per resource type per minute.

For the full picture, turn on `GCP_DEBUG`. On a cluster you can do that without touching the manifests:

```bash
kubectl -n gcp-dash set env deployment/gcp-dash GCP_DEBUG=true
kubectl -n gcp-dash logs deployment/gcp-dash -c gcp-dash -f
```

Then refresh a panel. With `GCP_DEBUG=true` you get, in addition to the lines above:

- the full traceback for each failed fetch, including the original `google.auth` / `google.api_core` exception that the panel error was derived from;
- `google.auth.transport.requests` lines for every token request: the STS exchange (`sts.googleapis.com/v1/token`), service-account impersonation (`iamcredentials.googleapis.com/...:generateAccessToken`), OAuth refresh, and each Cloud Storage REST call, with the HTTP response body;
- `google.cloud.compute_v1...` and `google.cloud.resourcemanager_v3...` request/response pairs with the RPC name, URL, HTTP status, and payload;
- `urllib3` connection lines, useful when egress to `*.googleapis.com` is blocked by a NetworkPolicy or proxy.

Each of those lines ends with ` | {...}` JSON. The app redacts `Authorization` headers and token, assertion, and key fields before logging, and cuts payloads at 32 KiB. Turn debug off again when done:

```bash
kubectl -n gcp-dash set env deployment/gcp-dash GCP_DEBUG-
```

Locally, `GCP_DEBUG=true scripts/run-podman.sh key.json my-project` or `GCP_DEBUG=true uv run --python 3.12 uvicorn gcp_dash.main:app --port 8080` does the same.

## Tests

```bash
uv run --python 3.12 pytest -q
```
