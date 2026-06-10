#!/usr/bin/env bash
# 番人(Watcher)起動ラッパー — cron 10 分毎(S39 新設)
#   */10 * * * * /home/vps-harappa/garden/services/watcher/run-watcher.sh >> /home/vps-harappa/garden/log/watcher.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"

# Discord 認証は garden-gaku-co の .env を共用(DISCORD_BOT_TOKEN / DISCORD_MASTER_CHANNEL_ID)
set -a
. ../garden-gaku-co/.env
set +a

python3 log_watcher.py
