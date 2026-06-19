#!/usr/bin/env bash
# scribe-poll.sh — ローカル WSL の cron。Discord「録音スイープして」の手動依頼を拾って実行する(S54)
#
# 背景:
#   Plaud はローカル WSL の MCP トークンでのみ読める。VPS の bot は Plaud に到達できないので、
#   「録音スイープして」を検知すると VPS に依頼マーカー(requested.flag)を置くだけ。
#   本 poller がそのマーカーを ~10 分間隔で拾い、run-local.sh(実スイープ + soil/board push)を回す。
#
# cron(ローカル WSL の crontab):
#   */10 * * * * /home/tukapontas/harappa-garden/garden/services/scribe/scribe-poll.sh >> /tmp/scribe-poll.log 2>&1
#
# べき等/排他:
#   - マーカーは test -f && mv(.taken)で atomic に取り出す(二重起動でも 1 回だけ実行)。
#   - run-local.sh 自体が launcher の lock + processed.jsonl のべき等で守られている。

set -uo pipefail

SSH_HOST="${SOIL_SYNC_SSH_HOST:-harappa}"
MARKER="/home/vps-harappa/garden/inbox/scribe/requested.flag"
RUN_LOCAL="/home/tukapontas/harappa-garden/garden/services/scribe/run-local.sh"

# マーカーがあれば atomic に取り出す(取れたら今回が実行担当)
if ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_HOST" \
     "test -f '$MARKER' && mv '$MARKER' '${MARKER}.taken'" 2>/dev/null; then
  echo "[scribe-poll] $(date '+%F %T') 依頼マーカー検知 → スイープ実行"
  bash "$RUN_LOCAL"
  rc=$?
  echo "[scribe-poll] run-local.sh exit=${rc}"
  # 取り出したマーカーの後始末(成功・失敗にかかわらず消す。失敗時は run-local が Discord に通知)
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_HOST" "rm -f '${MARKER}.taken'" 2>/dev/null || true
else
  : # 依頼なし(通常の空振り。ログを汚さないため無出力)
fi
