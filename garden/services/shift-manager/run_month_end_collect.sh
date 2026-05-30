#!/usr/bin/env bash
# run_month_end_collect.sh — 集計実行(承認)経路の wrapper(セッション21)
#
# 役割: month-end-working-hours-prep board の「集計実行(承認)」が[x]+approvedされた時に
#       send_pending.py から呼ばれる。
#       1. generate_working_hours.py で稼働シートタブを生成
#       2. コドモン CSV が garden-mirror/garden/inbox/kodomon/YYYY-MM.csv に存在すれば import_kodomon.py で放サボ反映
#
# 引数: $1 = 対象月 YYYY-MM
# 使い方(month-end-prep の execute_command に書く):
#   /home/vps-harappa/garden/services/shift-manager/run_month_end_collect.sh 2026-05
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 YYYY-MM" >&2
  exit 1
fi

MONTH=$1
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# .env 読み込み(Freee client 等)
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

echo "==== run_month_end_collect.sh start: month=$MONTH $(date -Is) ===="

# 1. 集計実行
echo "[1/2] generate_working_hours.py --month $MONTH"
.venv/bin/python generate_working_hours.py --month "$MONTH"

# 2. コドモン CSV あれば取り込み
CSV="/home/vps-harappa/garden-mirror/garden/inbox/kodomon/${MONTH}.csv"
if [ -f "$CSV" ]; then
  echo "[2/2] コドモン CSV 検出 → import_kodomon.py 実行"
  .venv/bin/python import_kodomon.py --month "$MONTH" --csv "$CSV"
else
  echo "[2/2] コドモン CSV なし($CSV) → 放サボ列は手入力のままです"
fi

echo "==== run_month_end_collect.sh done $(date -Is) ===="
