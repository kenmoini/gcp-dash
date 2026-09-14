# Pinned by tag (multi-arch index) so Dependabot can bump it; the tag is informational.
FROM registry.access.redhat.com/ubi10/python-312-minimal:1789347582

LABEL org.opencontainers.image.title="gcp-dash" \
      org.opencontainers.image.description="Container runtime dashboard with health-probe controls and a GCP resource viewer" \
      org.opencontainers.image.source="https://github.com/kenmoini/gcp-dash" \
      io.k8s.display-name="gcp-dash" \
      io.openshift.expose-services="8080:http"

# Image defaults: USER 1001, HOME=/opt/app-root/src, venv on PATH at /opt/app-root/bin
WORKDIR /opt/app-root/src

# Dependency layer: resolved straight from uv.lock so Dependabot updates flow into the image.
# uv is only needed to read the lockfile; it is removed again to keep the image lean.
COPY --chown=1001:0 pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv \
 && uv export --frozen --no-dev --no-emit-project --no-hashes -o /tmp/requirements.txt \
 && pip install --no-cache-dir -r /tmp/requirements.txt \
 && pip uninstall -y uv \
 && rm -f /tmp/requirements.txt

COPY --chown=1001:0 src ./src
RUN pip install --no-cache-dir --no-deps .

ENV PORT=8080 \
    GCP_CACHE_TTL_SECONDS=60 \
    CONTROLS_ENABLED=true

EXPOSE 8080
USER 1001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz/live', timeout=2)"

CMD ["sh", "-c", "exec uvicorn gcp_dash.main:app --host 0.0.0.0 --port ${PORT}"]
