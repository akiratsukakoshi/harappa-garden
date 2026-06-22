#!/usr/bin/env bash
# scribe-poll.sh — ローカル WSL の cron。2役を兼ねる(S54 起草 / S56 で日次キャッチアップ追加):
#   (A) Discord「録音スイープして」の手動依頼マーカーを拾って実行する。
#   (B) 日次キャッチアップ: 1日1回(07:30 以降の最初の tick で)日次スイープを回す。
#
# 背景:
#   Plaud はローカル WSL の MCP トークンでのみ読める。VPS の bot は Plaud に到達できないので、
#   「録音スイープして」を検知すると VPS に依頼マーカー(requested.flag)を置くだけ。
#   本 poller がそのマーカーを ~10 分間隔で拾い、run-local.sh(実スイープ + soil/board push)を回す。
#
#   ★日次キャッチアップの理由(S56): WSL は固定時刻(旧 07:30 cron)に起きていないことが多く、
#   日次 cron は一度も発火しなかった(S54 で install 以来 scribe-sweep.log が空)。WSL が起きて
#   いる間だけ走る本 poll に「今日まだ日次していなければ回す」を載せ、固定時刻 cron は廃止した。
#   = ガクチョが朝 WSL を起こした直後(or 07:30 以降の最初の tick)に日次が走る。
#
# cron(ローカル WSL の crontab、これ 1 本だけ。07:30 の日次 cron は廃止):
#   */10 * * * * /home/tukapontas/harappa-garden/garden/services/scribe/scribe-poll.sh >> /tmp/scribe-poll.log 2>&1
#
# べき等/排他:
#   - マーカーは test -f && mv(.taken)で atomic に取り出す(二重起動でも 1 回だけ実行)。
#   - 日次は last-daily-sweep マーカー(YYYY-MM-DD)で1日1回に制限。
#   - run-local.sh 自体が launcher の lock + processed.jsonl のべき等で守られている
#     (日次と手動が同 tick で重なっても launcher lock で 2 重起動しない)。

set -uo pipefail

SSH_HOST="${SOIL_SYNC_SSH_HOST:-harappa}"
MARKER="/home/vps-harappa/garden/inbox/scribe/requested.flag"
RUN_LOCAL="/home/tukapontas/harappa-garden/garden/services/scribe/run-local.sh"
DAILY_MARKER="/home/tukapontas/harappa-garden/garden/services/scribe/state/last-daily-sweep"
DAILY_AFTER="0730"   # この時刻(HHMM)以降に 1 日 1 回

# ── (B) 日次キャッチアップ ──────────────────────────────
today="$(date +%F)"
now_hm="$(date +%H%M)"
last_daily="$(cat "$DAILY_MARKER" 2>/dev/null || echo "")"
# 10# で強制10進(0830 等の先頭ゼロを8進と誤解釈させない)
if [ "$last_daily" != "$today" ] && [ "$((10#$now_hm))" -ge "$((10#$DAILY_AFTER))" ]; then
  echo "[scribe-poll] $(date '+%F %T') 日次キャッチアップ → スイープ実行(last=${last_daily:-none})"
  # 先にマーカーをクレーム = スイープ(数分)実行中に後続 tick が再入しない(thundering herd 防止)。
  mkdir -p "$(dirname "$DAILY_MARKER")"
  echo "$today" > "$DAILY_MARKER"
  bash "$RUN_LOCAL"
  drc=$?
  echo "[scribe-poll] daily run-local.sh exit=${drc}"
  if [ "$drc" -ne 0 ]; then
    # 失敗したらマーカーを取り消し、次 tick(10分後)で再試行する。
    rm -f "$DAILY_MARKER"
    echo "[scribe-poll] daily 失敗 → マーカー取消(次 tick で再試行)"
  fi
fi

# ── (A) 手動依頼マーカー ────────────────────────────────
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
