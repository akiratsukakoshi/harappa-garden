#!/usr/bin/env bash
# run-local.sh — scribe をローカル WSL で実行する wrapper(S54)
#
# なぜローカルか:
#   Plaud MCP は OAuth トークン(~/.plaud/tokens-mcp.json)で自動更新され、
#   そのトークンを持つホスト(=ガクチョが認証済のローカル WSL)でのみ headless 到達できる。
#   refresh_token はローテートし得るため、トークン所有ホストは 1 つに固定する(VPS にコピーしない)。
#   → scribe(Plaud を読む)はローカル WSL が所有ホスト。日次 cron もローカルに置く。
#
# 流れ:
#   1) launcher で scribe/daily-recording-sweep を実行
#      → claude -p が Plaud MCP に到達し、soil(meetings)はローカル repo に、
#        board(digest)は scribe/outbox/ に書く(新規録音がある時のみ)
#   2) soil を VPS garden-mirror へ push(push-to-vps.sh)
#   3) outbox の board を VPS board/pending/ へ push(上書き可)→ push 成功後 outbox を空にする
#      (send_pending〔VPS cron〕が Discord master に配信)
#
# board の住所は VPS 一箇所(/home/vps-harappa/garden/board/pending/)。repo に board の
# コンテンツ用ディレクトリは持たない。ローカルの outbox は push までの一時置き場で、push 後は空。
# (S57: 旧設計は board/pending にローカルが溜まり VPS と食い違う --ignore-existing バグがあった)
#
# 使い方:
#   bash run-local.sh                # 日次本実行(cron 用)
#   bash run-local.sh --dry-run      # launcher dry-run(claude -p を呼ばない)
#   bash run-local.sh --no-push      # ローカル実行のみ(soil/board を VPS に送らない=検証用)
#
# 日次起動(S56〜): 固定時刻 cron は WSL 不在で空振りするため廃止。日次は scribe-poll.sh の
# キャッチアップ(07:30 以降・WSL が起きていれば 1 日 1 回)が回す。本スクリプトは poll / 手動から呼ばれる。

set -uo pipefail

REPO=/home/tukapontas/harappa-garden
SEED=scribe/daily-recording-sweep
SSH_HOST="${SOIL_SYNC_SSH_HOST:-harappa}"
VPS_BOARD="/home/vps-harappa/garden/board/pending/"
OUTBOX="${REPO}/garden/services/scribe/outbox/"
LOG_DIR="${REPO}/garden/services/scribe/log"
STATE_DIR="${REPO}/garden/services/scribe/state"

# --no-push を抜き取り、残りは launcher へ渡す
PUSH=1
LAUNCHER_ARGS=()
for a in "$@"; do
  if [ "$a" = "--no-push" ]; then PUSH=0; else LAUNCHER_ARGS+=("$a"); fi
done

mkdir -p "$OUTBOX" "$LOG_DIR" "$STATE_DIR"

# cron の PATH は最小で、nvm 配下の node / claude を見つけられない(S56 で実害確認)。
# nvm を読み込んで node+claude を PATH に載せる(対話シェルと同じ状態にする)。
if ! command -v claude >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1 || true
fi
# nvm.sh でも不足する場合の最終手段: nvm の最新 node bin を直接 PATH 前置
if ! command -v claude >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
  NODE_BIN="$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1 || true)"
  [ -n "$NODE_BIN" ] && export PATH="$NODE_BIN:$PATH"
fi

CLAUDE_PATH="$(command -v claude || true)"
if [ -z "$CLAUDE_PATH" ] || ! command -v node >/dev/null 2>&1; then
  echo "[scribe] ERROR: claude / node CLI が見つかりません(nvm 解決に失敗)" >&2
  exit 127
fi

export CLAUDE_BIN="$CLAUDE_PATH"
export GARDEN_LOG_ROOT="$LOG_DIR"
export GARDEN_STATE_FILE="${STATE_DIR}/launcher-state.json"
export GARDEN_LOCK_DIR=/tmp

cd "$REPO"
echo "[scribe] $(date '+%F %T') launcher 起動(claude=${CLAUDE_BIN})"
node garden/services/launcher/launcher.mjs --seed "$SEED" "${LAUNCHER_ARGS[@]}"
rc=$?
echo "[scribe] launcher exit=${rc}"

if [ "$PUSH" -eq 1 ] && [ "$rc" -eq 0 ]; then
  echo "[scribe] soil を VPS へ push"
  bash "${REPO}/garden/services/soil-sync/push-to-vps.sh" || echo "[scribe] WARN: soil push 失敗"

  if compgen -G "${OUTBOX}*.md" > /dev/null; then
    echo "[scribe] outbox の board を VPS board/pending/ へ push(上書き可)"
    # --ignore-existing は使わない: scribe が当日内に board を書き直したら VPS に反映させる
    #   (旧バグ: ignore-existing で更新が VPS に届かず食い違っていた)。notified_at を消すと
    #   send_pending が更新版で再通知する=新情報なので妥当。
    if rsync -avh -e ssh "${OUTBOX}"*.md "${SSH_HOST}:${VPS_BOARD}"; then
      # push 成功 → outbox を空にする(ローカルに board を溜めない=墓場を作らない)
      rm -f "${OUTBOX}"*.md
      echo "[scribe] outbox を空にした(push 済)"
    else
      echo "[scribe] WARN: board push 失敗(outbox は残す=次回再送)"
    fi
  else
    echo "[scribe] outbox に board なし(新規録音なし=push 省略)"
  fi
else
  echo "[scribe] push スキップ(--no-push もしくは launcher 失敗)"
fi

exit $rc
