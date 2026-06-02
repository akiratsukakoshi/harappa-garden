#!/usr/bin/env bash
# pull-from-vps.sh — VPS garden-mirror/garden/soil/ → repo garden/soil/
#
# 用途: Claude セッション開始時に実行。菌糸 / ガクコ が VPS で書いた
#       最新エントリ(log.md / index.md 等)を repo に取り込む。
#
# ADR: docs/decisions/2026-06-02-soil-source-of-truth.md

set -euo pipefail

SSH_HOST="${SOIL_SYNC_SSH_HOST:-harappa}"
VPS_SOIL="/home/vps-harappa/garden-mirror/garden/soil/"
REPO_SOIL="/home/tukapontas/harappa-garden/garden/soil/"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="--dry-run"
fi

echo "[soil-sync] pull: ${SSH_HOST}:${VPS_SOIL} -> ${REPO_SOIL}"
if [[ -n "${DRY_RUN}" ]]; then
  echo "[soil-sync] DRY RUN (no files will be modified)"
fi

rsync -avh ${DRY_RUN} \
  -e "ssh" \
  "${SSH_HOST}:${VPS_SOIL}" \
  "${REPO_SOIL}"

echo "[soil-sync] pull done"
