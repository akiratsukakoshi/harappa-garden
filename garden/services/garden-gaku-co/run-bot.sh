#!/usr/bin/env bash
# garden-gaku-co — 会話 bot キープアライブ(sudo/systemd 不要)。
# cron が定期実行 + @reboot。プロセスが落ちていたら起こす。
#   */2 * * * *  /home/vps-harappa/garden/services/garden-gaku-co/run-bot.sh
#   @reboot      /home/vps-harappa/garden/services/garden-gaku-co/run-bot.sh
set -euo pipefail
cd "$(dirname "$0")"
PIDFILE=.bot.pid
LOG=/home/vps-harappa/garden/log/bot.log

# 既に動いていれば何もしない
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
  exit 0
fi

set -a
. ./.env
set +a

echo "==== bot start $(date -Is) ====" >> "$LOG"
nohup ./venv/bin/python bot.py >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "[run-bot] started pid=$(cat "$PIDFILE")"
