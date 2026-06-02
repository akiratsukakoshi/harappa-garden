#!/usr/bin/env bash
# push-to-vps.sh — repo garden/soil/ → VPS garden-mirror/garden/soil/
#
# 用途: Claude セッション終了時 / commit 前に実行。Claude が repo で
#       編集した構造ファイル(staff / business 等)を VPS に反映。
#       LiveSync が VPS → vault も反映するため、vault は手当不要。
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

echo "[soil-sync] push: ${REPO_SOIL} -> ${SSH_HOST}:${VPS_SOIL}"
if [[ -n "${DRY_RUN}" ]]; then
  echo "[soil-sync] DRY RUN (no files will be modified)"
fi

rsync -avh ${DRY_RUN} \
  -e "ssh" \
  "${REPO_SOIL}" \
  "${SSH_HOST}:${VPS_SOIL}"

echo "[soil-sync] push done"
