#!/usr/bin/env bash
# garden-gaku-co — board/pending/ approved 検知 → 配信/shell 実行(cron 1分毎、セッション21)。
#   * * * * *  /home/vps-harappa/garden/services/garden-gaku-co/run-send-pending.sh
set -euo pipefail
cd "$(dirname "$0")"

LOG=/home/vps-harappa/garden/log/send-pending.log
mkdir -p "$(dirname "$LOG")"

# 番人(watcher)用ハートビート: cron が生きている証跡(S39)
touch "$(dirname "$LOG")/.heartbeat-send-pending"

# .env を読み込む(send_pending.py 側でも load_env() するが、明示しておく)
set -a
. ./.env
set +a

./venv/bin/python send_pending.py >> "$LOG" 2>&1
