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
COPY --chown=1001:0 scripts/get-spiffe-token.py /opt/app-root/src/
RUN pip install --no-cache-dir --no-deps . && \
    pip install google-api-python-client spiffe --no-cache-dir

# Add GCloud CLI
ADD container_root/ /
USER 0
RUN ARCH=$(uname -m) && if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then sed -i 's/x86_64/aarch64/g' /etc/yum.repos.d/google-cloud-sdk.repo; fi
RUN microdnf update -y || microdnf update --disablerepo="rhel-10*" -y; \
    microdnf install -y libxcrypt-compat || microdnf install --disablerepo="rhel-10*" -y libxcrypt-compat; \
    export CLOUDSDK_SKIP_PY_COMPILATION=1; \
    microdnf install -y google-cloud-cli || microdnf install --disablerepo="rhel-10*" -y google-cloud-cli; \
    microdnf clean all && \
    rm -rf /var/cache/dnf && \
    chown -R 1001:0 /opt/app-root/src && \
    chmod -R g+rw /opt/app-root/src

ENV PORT=8080 \
    GCP_CACHE_TTL_SECONDS=60 \
    CONTROLS_ENABLED=true

EXPOSE 8080
USER 1001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz/live', timeout=2)"

CMD ["sh", "-c", "exec uvicorn gcp_dash.main:app --host 0.0.0.0 --port ${PORT}"]
