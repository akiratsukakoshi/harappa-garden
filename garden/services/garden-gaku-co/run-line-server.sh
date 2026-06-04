#!/usr/bin/env bash
# garden-gaku-co — 社内(core_team)LINE Webhook サーバのキープアライブ。
# cron で定期実行 + @reboot。プロセスが落ちていたら起こす(run-bot.sh と同方式)。
#   */2 * * * *  /home/vps-harappa/garden/services/garden-gaku-co/run-line-server.sh
#   @reboot      /home/vps-harappa/garden/services/garden-gaku-co/run-line-server.sh
set -euo pipefail
cd "$(dirname "$0")"
PIDFILE=.line-server.pid
LOG=/home/vps-harappa/garden/log/line-server.log
HOST="${LINE_SERVER_HOST:-127.0.0.1}"
PORT="${LINE_SERVER_PORT:-8011}"

# 既に動いていれば何もしない
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
  exit 0
fi

set -a
. ./.env
set +a

# LINE サーバ用 venv(bot とは分離)。無ければ requirements-line.txt から作る。
VENV="${LINE_VENV:-venv-line}"

echo "==== line-server start $(date -Is) ====" >> "$LOG"
nohup "./${VENV}/bin/python" -m uvicorn line.app:app --host "$HOST" --port "$PORT" >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "[run-line-server] started pid=$(cat "$PIDFILE") on ${HOST}:${PORT}"
