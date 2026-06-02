#!/usr/bin/env bash
# garden-gaku-co — 朝の口火 cron ラッパー。.env を読んで morning_greet.py を実行する。
#
# crontab 例(VPS, JST。morning-briefing 06:30 の完走を待つ 10 分バッファで 06:40):
#   40 6 * * *  /home/vps-harappa/garden/services/garden-gaku-co/run-morning-greet.sh \
#       >> /home/vps-harappa/garden/log/morning-greet.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"

set -a
. ./.env
set +a

echo "==== morning-greet $(date -Is) ===="
python3 morning_greet.py
