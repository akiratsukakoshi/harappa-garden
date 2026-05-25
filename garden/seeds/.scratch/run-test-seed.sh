#!/bin/bash
# 試作:最小ランチャー(セッション9, 2026-05-25)
#
# 目的: cron → claude -p → ログ生成 のエンドツーエンドが成り立つか確認する最小実装。
# 設計判断はしていない(frontmatter パースなし、種名ハードコード、ログ形式は仮)。
# 本実装(garden/seeds/.scratch から本番ランチャーへの育て方)はセッション10 以降で議論する。
#
# 同期先: VPS の /home/vps-harappa/garden/seeds/.scratch/run-test-seed.sh
#         (harappa-garden 側が正本、VPS は手動コピー。将来は LiveSync で自動同期)
#
# 動作確認(2026-05-25 セッション9):
#   直接実行 → exit 0、ログファイル生成、claude -p の応答キャプチャ OK
#   cron 経由 → 同上(発火時刻 14:21:01、6秒で完走)

set -u

SEED_NAME="test-seed"
TS=$(date +%Y-%m-%dT%H-%M-%S)
LOG_DIR="$HOME/garden/seeds/.log"
LOG_FILE="$LOG_DIR/${TS}-${SEED_NAME}.log"
CLAUDE="$HOME/.npm-global/bin/claude"

mkdir -p "$LOG_DIR"

{
  echo "=== seed: $SEED_NAME ==="
  echo "=== started_at: $(date -Iseconds) ==="
  echo "=== host: $(hostname) ==="
  echo "=== claude_version: $($CLAUDE --version 2>&1) ==="
  echo "--- claude -p output ---"
  $CLAUDE -p "Reply with the current Japan time in ISO 8601 (YYYY-MM-DDTHH:MM:SS+09:00), then on a new line 'OK'. Nothing else." 2>&1
  EC=$?
  echo ""
  echo "--- end ---"
  echo "=== exit_code: $EC ==="
  echo "=== finished_at: $(date -Iseconds) ==="
} > "$LOG_FILE" 2>&1

exit $EC
