#!/usr/bin/env bash
# Run gcp-dash locally with Podman. Usage: scripts/run-podman.sh [path/to/key.json] [gcp-project-id]
# LOG_LEVEL and GCP_DEBUG are passed through to the container when set in your shell.
set -euo pipefail
KEY="${1:-}"
PROJECT="${2:-${GCP_PROJECT:-}}"
IMAGE="${IMAGE:-localhost/gcp-dash:dev}"

args=(--rm -it --name gcp-dash -p 8080:8080 --cpus 1 --memory 512m)
if [[ -n "$KEY" ]]; then
  args+=(-v "$(realpath "$KEY"):/var/secrets/gcp/key.json:ro,Z"
         -e GOOGLE_APPLICATION_CREDENTIALS=/var/secrets/gcp/key.json)
fi
[[ -n "$PROJECT" ]] && args+=(-e "GCP_PROJECT=$PROJECT")
[[ -n "${LOG_LEVEL:-}" ]] && args+=(-e "LOG_LEVEL=$LOG_LEVEL")
[[ -n "${GCP_DEBUG:-}" ]] && args+=(-e "GCP_DEBUG=$GCP_DEBUG")

exec podman run "${args[@]}" "$IMAGE"
