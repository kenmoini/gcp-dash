#!/usr/bin/env bash
# Run gcp-dash locally with Podman. Usage: scripts/run-podman.sh [path/to/key.json] [gcp-project-id]
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

exec podman run "${args[@]}" "$IMAGE"
