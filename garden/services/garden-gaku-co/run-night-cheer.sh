#!/usr/bin/env bash
# garden-gaku-co — 夜の一言 cron ラッパー。.env を読んで night_cheer.py を実行する。
# launcher と同じく、cron は .bashrc を読まないので CLAUDE_BIN はフルパスを .env に置く。
#
# crontab 例(VPS, JST。night-review 22:30 の後に回す):
#   40 22 * * *  /home/vps-harappa/garden/services/garden-gaku-co/run-night-cheer.sh \
#       >> /home/vps-harappa/garden/log/night-cheer.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"

set -a
. ./.env
set +a

echo "==== night-cheer $(date -Is) ===="
python3 night_cheer.py
