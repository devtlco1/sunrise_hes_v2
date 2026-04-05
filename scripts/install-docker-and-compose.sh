#!/usr/bin/env bash
# For Ubuntu VPS images where `docker-compose-plugin` is missing from apt (e.g. restricted repos).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "==> apt update + docker.io + curl + git"
apt-get update
apt-get install -y ca-certificates curl git docker.io

echo "==> enable docker"
systemctl enable --now docker

ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64) DARCH="x86_64" ;;
  aarch64 | arm64) DARCH="aarch64" ;;
  *)
    echo "Unsupported architecture: ${ARCH}" >&2
    exit 1
    ;;
esac

PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"
echo "==> install docker compose plugin (${DARCH}) -> ${PLUGIN_DIR}"
mkdir -p "${PLUGIN_DIR}"
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${DARCH}" \
  -o "${PLUGIN_DIR}/docker-compose"
chmod +x "${PLUGIN_DIR}/docker-compose"

echo "==> versions"
docker --version
docker compose version
