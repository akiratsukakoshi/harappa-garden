#!/usr/bin/env bash
# pull-from-vps.sh — VPS garden-mirror/garden/memory/ → repo garden/memory/
#
# 用途: Claude セッション開始時に実行(memory wiki を参照する作業がある時)。
#       ingest-raw 種(03:30)/ bot が VPS で更新した wiki/*.md と index.md を repo に取り込む。
#       raw/*.md は機密 + .gitignore 除外のため同期しない(VPS 専属正本)。
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

echo "[memory-sync] pull: ${SSH_HOST}:${VPS_MEMORY} -> ${REPO_MEMORY}"
echo "[memory-sync] excluding raw/*.md (VPS-only, git-ignored)"
if [[ -n "${DRY_RUN}" ]]; then
  echo "[memory-sync] DRY RUN (no files will be modified)"
fi

rsync -avh ${DRY_RUN} \
  -e "ssh" \
  --exclude='*/raw/*.md' \
  "${SSH_HOST}:${VPS_MEMORY}" \
  "${REPO_MEMORY}"

echo "[memory-sync] pull done"
