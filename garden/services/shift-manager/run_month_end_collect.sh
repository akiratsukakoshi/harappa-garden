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

# 1. 集計実行(既存タブガード付き — generate_working_hours.py が --force-regenerate 無しで
#    既存タブ + 放サボ列にデータあり を検出したら exit 1。本スクリプトもそこで止める)
echo "[1/2] generate_working_hours.py --month $MONTH"
.venv/bin/python generate_working_hours.py --month "$MONTH"

# 2. コドモン CSV 取り込み(パス解決は import_kodomon.py:resolve_csv_path に一任。
#    YYYY-MM.csv / YYYYMM.csv / *YYYY-MM*.csv / *YYYYMM*.csv / 単一CSV の順で自動検出)
echo "[2/2] import_kodomon.py --month $MONTH(CSV パスは自動解決)"
if .venv/bin/python import_kodomon.py --month "$MONTH"; then
  echo "  → import_kodomon.py 完了"
else
  rc=$?
  # exit 1 = CSV 未配置 / exit 2 = タブ未生成。どちらも警告で続行(集計タブ自体は出来てる)
  echo "  ⚠️ import_kodomon.py 失敗 (rc=$rc) → 放サボ列は手入力のままです"
fi

echo "==== run_month_end_collect.sh done $(date -Is) ===="
