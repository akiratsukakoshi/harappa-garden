#!/usr/bin/env bash
# check-auth.sh — Claude Code OAuth トークンの自動リフレッシュ。
#
# Claude CLI のサブスク認証トークンは短命(約8〜24時間)。CLI をインタラクティブに
# 使うと内部でリフレッシュされるが、bot の -p ワンショットだけでは更新されない
# ケースがある。このスクリプトを cron で4時間おきに実行し、トークンが有効なうちに
# CLI を叩いてリフレッシュを促す。
#
# cron: 0 */4 * * *  /home/vps-harappa/garden/services/garden-gaku-co/check-auth.sh
#
# 通知は「自動リフレッシュが失敗した場合のみ」。成功時はログだけ。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && set -a && source "$SCRIPT_DIR/.env" && set +a

CREDS="$HOME/.claude/.credentials.json"
CLAUDE_BIN="${CLAUDE_BIN:-/home/vps-harappa/.npm-global/bin/claude}"
LOG="/home/vps-harappa/garden/log/check-auth.log"
WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

log() { echo "[$(date -Is)] $*" >> "$LOG"; }

if [ ! -f "$CREDS" ]; then
  log "ERROR: credentials file not found: $CREDS"
  exit 1
fi

# Step 1: トークン残り時間を確認
REMAINING=$(python3 - "$CREDS" <<'PYEOF'
import json, sys, datetime
with open(sys.argv[1]) as f:
    data = json.load(f)
oauth = data.get("claudeAiOauth", {})
exp = oauth.get("expiresAt", 0)
if not exp:
    print("no_token")
    sys.exit(0)
exp_dt = datetime.datetime.fromtimestamp(exp / 1000, tz=datetime.timezone.utc)
now = datetime.datetime.now(tz=datetime.timezone.utc)
hours = (exp_dt - now).total_seconds() / 3600
print(f"{hours:.1f}")
PYEOF
)

if [ "$REMAINING" = "no_token" ]; then
  log "ERROR: no OAuth token in credentials"
  exit 1
fi

log "token remaining: ${REMAINING}h"

# Step 2: CLI を叩いてリフレッシュを促す
# (トークンが有効なうちに使えば CLI が内部でリフレッシュする)
MTIME_BEFORE=$(stat --format="%Y" "$CREDS")
RESULT=$("$CLAUDE_BIN" -p "respond with only the word ok" --model haiku 2>&1 || true)

if echo "$RESULT" | grep -qi "authenticate\|401\|Invalid"; then
  # リフレッシュ失敗 — 通知が必要
  log "ERROR: auth failed, token may need manual re-login"

  if [ -n "$WEBHOOK_URL" ]; then
    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d '{"content":"🚨 Claude 認証トークンの自動リフレッシュに失敗しました。ガクコは応答できません。\nVPS で再認証してください:\n```\nssh harappa\n/home/vps-harappa/.npm-global/bin/claude login\n```\n→ `/login` → ブラウザ認証 → bot 再起動"}' \
      > /dev/null 2>&1
    log "notified Discord"
  fi
  exit 1
fi

# Step 3: リフレッシュ結果を確認
MTIME_AFTER=$(stat --format="%Y" "$CREDS")
NEW_REMAINING=$(python3 - "$CREDS" <<'PYEOF'
import json, sys, datetime
with open(sys.argv[1]) as f:
    data = json.load(f)
exp = data.get("claudeAiOauth", {}).get("expiresAt", 0)
if not exp:
    print("unknown")
    sys.exit(0)
exp_dt = datetime.datetime.fromtimestamp(exp / 1000, tz=datetime.timezone.utc)
now = datetime.datetime.now(tz=datetime.timezone.utc)
print(f"{(exp_dt - now).total_seconds() / 3600:.1f}")
PYEOF
)

if [ "$MTIME_BEFORE" != "$MTIME_AFTER" ]; then
  log "refreshed: ${REMAINING}h → ${NEW_REMAINING}h"
else
  log "token still valid (${NEW_REMAINING}h), no refresh needed"
fi
