#!/usr/bin/env python3
"""import_kodomon.py — コドモン勤怠 CSV を working_hours sheet の放サボセルに反映する

セッション21 (2026-05-30) で新規実装。

仕様:
  - 入力: コドモン「職員入退室エクスポート」CSV(Shift-JIS)
  - 出力: working_hours sheet の `YYYY-MM_稼働時間` タブの放サボイベント × 該当スタッフセル に業務時間を書き込み
  - 月次タブが存在しない場合: 警告で終了(先に generate_working_hours.py を実行する必要)

CSV 構造(コドモン職員入退室エクスポート):
  列: 職員コード, 氏名, グループ, 職員, 所属, 日付, 曜日, シフト, シフト出勤, シフト退勤,
      出勤, 休憩, 戻り, 退勤, 業務開始, 業務終了, 業務時間, 備考
  業務時間列(16, 0-based)が稼働時間(HH:MM 形式、空 = 出勤なし)

実行:
  .venv/bin/python import_kodomon.py --month 2026-05 --csv ../../../garden-mirror/garden/inbox/kodomon/2026-05.csv

呼び出し元:
  - run_month_end_collect.sh(月末 prep 種の集計実行から呼ばれる)
  - 手動(検証時)
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2 import service_account

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from lib.utils import setup_logger

logger = setup_logger("ImportKodomon")

CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "secrets", "credentials.json")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "config_ids.json")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# コドモン CSV 列インデックス(0-based、ヘッダ行を除く)
COL_NAME = 1   # 氏名
COL_DATE = 5   # 日付 (YYYY-MM-DD)
COL_WORK_TIME = 16  # 業務時間 (HH:MM)


def read_kodomon_csv(csv_path: str) -> dict:
    """CSV を読んで {正式名称: {日付YYYY-MM-DD: 業務時間HH:MM}} の辞書を返す。

    エンコーディングは Shift-JIS を最優先、失敗時 UTF-8 にフォールバック。
    """
    encodings = ["shift_jis", "cp932", "utf-8"]
    rows = None
    used_encoding = None
    for enc in encodings:
        try:
            with open(csv_path, encoding=enc) as f:
                rows = list(csv.reader(f))
            used_encoding = enc
            logger.info(f"CSV 読み込み成功: encoding={enc}, 行数={len(rows)}")
            break
        except UnicodeDecodeError:
            continue
    if rows is None:
        raise RuntimeError(f"CSV 読み込み失敗(エンコーディング不明): {csv_path}")

    if len(rows) < 2:
        raise RuntimeError("CSV に有効データなし")

    # 1行目はヘッダ
    header = rows[0]
    logger.info(f"ヘッダ: {header}")

    result = defaultdict(dict)
    skipped = 0
    for r in rows[1:]:
        if len(r) <= COL_WORK_TIME:
            skipped += 1
            continue
        name = r[COL_NAME].strip()
        date_str = r[COL_DATE].strip()
        work_time = r[COL_WORK_TIME].strip()
        if not name or not date_str or not work_time:
            continue
        # 業務時間が "00:00" や "0:00" の行はスキップ(出勤なし扱い)
        if work_time in ("0:00", "00:00", "0", ""):
            continue
        result[name][date_str] = work_time

    logger.info(f"取り込み対象スタッフ数: {len(result)} 名, スキップ行: {skipped}")
    return dict(result)


def normalize_name(name: str) -> str:
    """名前比較用に空白を除去 + 全角/半角空白を統一"""
    return re.sub(r"[\s　]+", "", name)


def import_to_sheet(month_str: str, kodomon_data: dict, db_sh_id: str = None) -> int:
    """working_hours sheet の {month_str}_稼働時間 タブの放サボセルに反映"""
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)

    # 名前マッピング(DB_Master_Nicknames から正式名称ベースのマッピングを取得)
    # コドモン氏名 → working_hours のスタッフ列(正式名称) の照合用
    db_sh = gc.open_by_key(cfg["backend_db_id"])
    try:
        nick_ws = db_sh.worksheet("DB_Master_Nicknames")
        nick_rows = nick_ws.get_all_values()
        # {正式名称(正規化): 正式名称(原形)} のマップ
        official_names = {}
        for row in nick_rows[1:]:
            if len(row) < 2 or not row[1].strip():
                continue
            official = row[1].strip()
            official_names[normalize_name(official)] = official
        logger.info(f"DB_Master_Nicknames: {len(official_names)} 名")
    except Exception as e:
        logger.warning(f"DB_Master_Nicknames 読み込み失敗(続行): {e}")
        official_names = {}

    # 稼働シート開く
    wh_sh = gc.open_by_key(cfg["working_hours_id"])
    sheet_title = f"{month_str}_稼働時間"
    try:
        ws = wh_sh.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"タブ未存在: {sheet_title} → 先に generate_working_hours.py を実行してください")
        return -1

    # 全データ取得
    raw = ws.get_all_values()
    if len(raw) < 4:
        logger.error("シート構造不正(行数不足)")
        return -1

    header_row = raw[1]    # 日付ヘッダ "5/7" 等
    cat_row = raw[2]       # カテゴリラベル "放サボ" 等
    # 4 行目以降がデータ(スタッフ × 列)

    # 放サボ列のインデックスを取得(複数あり得る = 月内に複数開催)
    saboru_cols = [i for i, label in enumerate(cat_row) if label.strip() == "放サボ"]
    if not saboru_cols:
        logger.warning("放サボ列が見つからない(月内に放サボ event なし or タブ未生成) → 終了")
        return 0
    logger.info(f"放サボ列: {len(saboru_cols)} 列 (列インデックス={saboru_cols})")

    # 各放サボ列の日付を header_row から取得
    # ヘッダ形式: "5/7" など
    saboru_dates = {}  # {col_index: "MM/DD"}
    for col_i in saboru_cols:
        header_label = header_row[col_i].strip()
        saboru_dates[col_i] = header_label
    logger.info(f"放サボ日付: {saboru_dates}")

    # スタッフ行(4 行目以降、col 0 = 正式名称)
    # コドモン氏名 → 正式名称 → 行インデックス のマッピング
    staff_row_map = {}
    for i, row in enumerate(raw[3:], start=3):
        if not row or not row[0].strip():
            continue
        official = row[0].strip()
        staff_row_map[normalize_name(official)] = i + 1  # gspread は 1-based 行
    logger.info(f"稼働シート上のスタッフ数: {len(staff_row_map)} 名")

    # コドモンデータを反映
    # コドモン日付 (YYYY-MM-DD) → 放サボ日付 (M/D) に変換して照合
    cells_to_update = []  # [(row, col, value), ...]
    unmatched_staff = set()
    unmatched_dates = set()

    for kodomon_name, date_to_time in kodomon_data.items():
        norm_kodomon = normalize_name(kodomon_name)
        # 名前照合: コドモン氏名 を 正式名称マップで照合
        if norm_kodomon not in staff_row_map:
            unmatched_staff.add(kodomon_name)
            continue
        sheet_row = staff_row_map[norm_kodomon]

        for date_str, work_time in date_to_time.items():
            # date_str = "2026-05-07" → "5/7"
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                short_date = f"{dt.month}/{dt.day}"
            except Exception:
                continue
            # 放サボ列に該当日があるか
            target_col = None
            for col_i, sab_date in saboru_dates.items():
                if sab_date == short_date:
                    target_col = col_i
                    break
            if target_col is None:
                unmatched_dates.add(f"{kodomon_name} {short_date}")
                continue
            # cell 更新リストに追加(gspread は 1-based 列)
            cells_to_update.append((sheet_row, target_col + 1, work_time))

    logger.info(f"反映予定セル: {len(cells_to_update)}")
    if unmatched_staff:
        logger.warning(f"スタッフ名照合失敗({len(unmatched_staff)} 名): {sorted(unmatched_staff)[:10]}")
    if unmatched_dates:
        logger.warning(f"放サボ日不一致({len(unmatched_dates)} 件): {sorted(unmatched_dates)[:10]}")

    # 一括更新(セル単位)
    if cells_to_update:
        batch_data = []
        for row, col, value in cells_to_update:
            cell_ref = gspread.utils.rowcol_to_a1(row, col)
            batch_data.append({"range": cell_ref, "values": [[value]]})
        ws.batch_update(batch_data, value_input_option="USER_ENTERED")
        logger.info(f"反映完了: {len(cells_to_update)} セル")
    else:
        logger.info("反映対象セルなし")

    return len(cells_to_update)


def resolve_csv_path(month: str, explicit_csv: Optional[str] = None) -> Optional[str]:
    """CSV パス解決(S24 柔軟化):

    優先順位:
      1. --csv で明示指定された path(存在チェック)
      2. inbox/kodomon/ 内で month に該当するファイル名パターン(複数許容):
         - `{YYYY-MM}.csv`           例: 2026-05.csv
         - `{YYYYMM}.csv`            例: 202605.csv
         - `*{YYYY-MM}*.csv`         例: kodomon-2026-05-export.csv
         - `*{YYYYMM}*.csv`          例: 202605_職員入退室.csv
      3. inbox/kodomon/ 内に CSV が 1 件だけなら、それを採用(運用簡略化)
    """
    import glob
    inbox = "/home/vps-harappa/garden-mirror/garden/inbox/kodomon"

    if explicit_csv:
        return explicit_csv if os.path.exists(explicit_csv) else None

    ym_hyphen = month             # 2026-05
    ym_compact = month.replace("-", "")  # 202605

    patterns = [
        f"{inbox}/{ym_hyphen}.csv",
        f"{inbox}/{ym_compact}.csv",
        f"{inbox}/*{ym_hyphen}*.csv",
        f"{inbox}/*{ym_compact}*.csv",
    ]
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            return sorted(matches)[-1]  # 同パターン複数ヒット時は名前順最後(=最新想定)

    # 最後の砦: inbox/kodomon/ 内に CSV が 1 件だけならそれ
    all_csvs = glob.glob(f"{inbox}/*.csv")
    if len(all_csvs) == 1:
        logger.warning(f"month 一致なし、フォルダ唯一の CSV を採用: {all_csvs[0]}")
        return all_csvs[0]

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="コドモン勤怠 CSV を稼働シートの放サボ列に反映")
    parser.add_argument("--month", required=True, help="対象月 YYYY-MM")
    parser.add_argument("--csv", required=False, help="コドモン CSV ファイルパス(省略時は inbox/kodomon/ から自動解決)")
    args = parser.parse_args()

    csv_path = resolve_csv_path(args.month, args.csv)
    if not csv_path:
        logger.error(f"CSV ファイルが見つかりません: month={args.month} / explicit_csv={args.csv}")
        logger.error(f"探索パス: /home/vps-harappa/garden-mirror/garden/inbox/kodomon/{{{args.month}.csv, {args.month.replace('-','')}.csv, *{args.month}*.csv, *{args.month.replace('-','')}*.csv}}")
        sys.exit(1)
    logger.info(f"CSV 採用: {csv_path}")

    kodomon_data = read_kodomon_csv(csv_path)
    n = import_to_sheet(args.month, kodomon_data)
    if n < 0:
        sys.exit(2)
    print(f"✓ コドモン CSV 取り込み完了: {n} セル反映 (月={args.month}, csv={os.path.basename(csv_path)})")
