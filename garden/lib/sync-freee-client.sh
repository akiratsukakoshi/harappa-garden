#!/usr/bin/env bash
# sync-freee-client.sh — 正本 garden/lib/freee_client.py を各 service の lib/ に配布(S39)
#
# 使い方:
#   ./sync-freee-client.sh           # 正本を各 service にコピー
#   ./sync-freee-client.sh --check   # コピーが正本とずれていないか検査(pre-commit から呼ばれる)
#
# 背景: service は VPS に個別 rsync される自己完結構造のため、import 共有でなく
#       「正本 + 機械コピー」方式を採用。編集は必ず garden/lib/freee_client.py で行う。
set -euo pipefail
cd "$(dirname "$0")"

CANON=freee_client.py
TARGETS=(
  ../services/expense-processor/lib/freee_client.py
  ../services/shift-manager/lib/freee_client.py
  ../services/invoice-processor/lib/freee_client.py
  ../services/finance/lib/freee_client.py
)

if [[ "${1:-}" == "--check" ]]; then
  rc=0
  for t in "${TARGETS[@]}"; do
    if [[ ! -f "$t" ]] || ! diff -q "$CANON" "$t" >/dev/null; then
      echo "DRIFT: $t が正本 garden/lib/freee_client.py とずれています"
      rc=1
    fi
  done
  [[ $rc -eq 0 ]] && echo "OK: freee_client コピーは全て正本と一致"
  exit $rc
fi

for t in "${TARGETS[@]}"; do
  cp "$CANON" "$t"
  echo "synced: $t"
done
echo "完了。VPS への反映は各 service の rsync デプロイで行うこと。"
