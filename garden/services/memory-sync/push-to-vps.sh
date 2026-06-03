#!/usr/bin/env bash
# push-to-vps.sh — repo garden/memory/ → VPS garden-mirror/garden/memory/
#
# 用途: Claude セッション終了時 / commit 前に実行(memory wiki を編集した時)。
#       Claude が repo で編集した wiki/*.md / index.md / README.md を VPS に反映。
#       LiveSync が VPS → vault も自動同期するため、vault は手当不要。
#       raw/*.md は VPS 専属正本のため同期しない。
#
# ADR: docs/decisions/2026-06-03-memory-source-of-truth.md

set -euo pipefail

SSH_HOST="${MEMORY_SYNC_SSH_HOST:-harappa}"
VPS_MEMORY="/home/vps-harappa/garden-mirror/garden/memory/"
REPO_MEMORY="/home/tukapontas/harappa-garden/garden/memory/"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="--dry-run"
fi

echo "[memory-sync] push: ${REPO_MEMORY} -> ${SSH_HOST}:${VPS_MEMORY}"
echo "[memory-sync] excluding raw/*.md (VPS-only, git-ignored)"
if [[ -n "${DRY_RUN}" ]]; then
  echo "[memory-sync] DRY RUN (no files will be modified)"
fi

rsync -avh ${DRY_RUN} \
  -e "ssh" \
  --exclude='*/raw/*.md' \
  "${REPO_MEMORY}" \
  "${SSH_HOST}:${VPS_MEMORY}"

echo "[memory-sync] push done"
