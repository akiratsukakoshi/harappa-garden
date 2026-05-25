#!/bin/bash
# NPM の内部 DB(data/database.sqlite)と LetsEncrypt 証明書一式を tar.gz 化
# → ローカルの vps/proxy-manager/backups/ に取得する
#
# 実行: ./vps/proxy-manager/export.sh
# 前提: ~/.ssh/config に harappa エントリ
# 出力: vps/proxy-manager/backups/npm-backup-YYYYMMDD-HHMMSS.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_NAME="npm-backup-${TIMESTAMP}.tar.gz"
REMOTE_TMP="/tmp/${ARCHIVE_NAME}"
LOCAL_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}"

mkdir -p "${BACKUP_DIR}"

echo "[1/4] VPS で tar.gz 作成中..."
# data と letsencrypt のオーナーが root のため、alpine コンテナを root で起動して tar
# 出力ファイルは vps-harappa(uid 1000) 所有に変更してから scp 取得
ssh harappa "docker run --rm \
  -v /home/vps-harappa/proxy-manager:/src:ro \
  -v /tmp:/out \
  alpine sh -c 'cd /src && tar -czf /out/${ARCHIVE_NAME} data letsencrypt && chown 1000:1000 /out/${ARCHIVE_NAME}'"

echo "[2/4] ローカルに転送中..."
scp "harappa:${REMOTE_TMP}" "${LOCAL_PATH}"

echo "[3/4] VPS の一時ファイルを削除..."
ssh harappa "rm -f ${REMOTE_TMP}"

echo "[4/4] サイズ確認..."
ls -lh "${LOCAL_PATH}"

# 古い backup を整理(直近 10 個を残す)
echo "[整理] 古い backup を削除(直近 10 個を保持)..."
cd "${BACKUP_DIR}"
ls -t npm-backup-*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -v

echo "✅ 完了: ${LOCAL_PATH}"
