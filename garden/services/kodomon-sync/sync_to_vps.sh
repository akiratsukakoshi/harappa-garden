#!/usr/bin/env bash
# kodomon-sync/sync_to_vps.sh — WSL 上の repo に置かれた kodomon CSV を VPS に同期する(S24)
#
# 役割:
#   ガクチョが /home/tukapontas/harappa-garden/garden/inbox/kodomon/ に CSV を置く
#   → 本スクリプトが rsync で VPS の /home/vps-harappa/garden-mirror/garden/inbox/kodomon/ に転送
#   → import_kodomon.py(VPS で run_month_end_collect.sh から呼ばれる)が拾って放サボ列に反映
#
# 経路 α: WSL cron */5 で動かす(暫定。本格は γ = Discord アップロード経路)
#
# 設置:
#   crontab -e で以下を追加:
#     */5 * * * * /home/tukapontas/harappa-garden/garden/services/kodomon-sync/sync_to_vps.sh >> /tmp/kodomon-sync.log 2>&1
#
# 実行(初回手動):
#   /home/tukapontas/harappa-garden/garden/services/kodomon-sync/sync_to_vps.sh

set -euo pipefail

SRC="/home/tukapontas/harappa-garden/garden/inbox/kodomon"
DEST_HOST="harappa"
DEST_PATH="/home/vps-harappa/garden-mirror/garden/inbox/kodomon"

JST_TS=$(TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S+09:00')

# CSV 不在なら何もしない(ノイズ抑制)
shopt -s nullglob
csvs=( "$SRC"/*.csv )
if [ ${#csvs[@]} -eq 0 ]; then
  exit 0
fi

echo "[${JST_TS}] kodomon-sync start: ${#csvs[@]} CSV(s) in src"

# rsync で同期(削除はしない、追加・更新のみ)
# --ignore-existing: 既に同名ファイルが VPS にあれば上書きしない
#   → ガクチョが古い CSV を再配置しても VPS 側の最新が守られる
#   → 上書きしたい場合は VPS 側の該当ファイルを先に消す
# rsync の --rsh で ssh 設定済みホスト(harappa)を利用
rsync -av --include='*.csv' --exclude='*' \
  "${SRC}/" "${DEST_HOST}:${DEST_PATH}/" \
  | grep -v '^building\|^sending\|^sent\|^total' || true

echo "[${JST_TS}] kodomon-sync done"
