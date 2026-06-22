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
#      → claude -p が Plaud MCP に到達し、soil(meetings)+ board(digest)をローカル repo に書く
#   2) soil を VPS garden-mirror へ push(push-to-vps.sh)
#   3) board/pending を VPS へ push(send_pending〔VPS cron〕が Discord master に配信)
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
LOCAL_BOARD="${REPO}/garden/board/pending/"
LOG_DIR="${REPO}/garden/services/scribe/log"
STATE_DIR="${REPO}/garden/services/scribe/state"

# --no-push を抜き取り、残りは launcher へ渡す
PUSH=1
LAUNCHER_ARGS=()
for a in "$@"; do
  if [ "$a" = "--no-push" ]; then PUSH=0; else LAUNCHER_ARGS+=("$a"); fi
done

mkdir -p "$LOCAL_BOARD" "$LOG_DIR" "$STATE_DIR"

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

  if compgen -G "${LOCAL_BOARD}*.md" > /dev/null; then
    echo "[scribe] board/pending を VPS へ push(additive)"
    # --ignore-existing: VPS に既にある board(send_pending が notified_at を追記済み)は上書きしない
    rsync -avh --ignore-existing -e ssh "${LOCAL_BOARD}" "${SSH_HOST}:${VPS_BOARD}" \
      || echo "[scribe] WARN: board push 失敗"
  else
    echo "[scribe] board/pending に新規なし(push 省略)"
  fi
else
  echo "[scribe] push スキップ(--no-push もしくは launcher 失敗)"
fi

exit $rc
