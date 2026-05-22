#!/usr/bin/env python3
"""register_payroll.py - 稼働時間シートからAD列=「給与」のスタッフ分を人事労務freeeに勤怠登録する

worktimeシートの日別稼働時間を読み取り、人事労務freeeの work_records API でPUT登録する。
人事労務freee側で時給×時間の給与計算が自動で行われる。

Usage:
    python apps/shift_manager/logic/register_payroll.py --month 2026-05 [--dry-run]
"""

import sys
import os
import json
import re
import argparse
from datetime import datetime, timedelta
from typing import Optional

import gspread
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from modules.utils import setup_logger
from modules.freee_hr_client import FreeeHRClient

logger = setup_logger("RegisterPayroll")

CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TARGET_PAYMENT_TYPE = "給与"
DEFAULT_CLOCK_IN = "09:00"  # デフォルト出勤時刻（実際の開始時刻が不明なため）
TZ_SUFFIX = "+09:00"


def auth_gspread():
    try:
        with open(CREDENTIALS_PATH) as f:
            d = json.load(f)
            if d.get("type") == "service_account":
                return service_account.Credentials.from_service_account_file(
                    CREDENTIALS_PATH, scopes=SCOPES
                )
    except Exception:
        pass
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def parse_time_str(s: str) -> Optional[int]:
    """セル表示文字列から分数に変換。'5:45' → 345, '0:00' → 0, '' → None"""
    if not s or not s.strip():
        return None
    s = s.strip()
    if s in ("写真", "調理", "開催"):
        return None
    m = re.match(r"^(\d+):(\d{1,2})$", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


def load_hr_employee_map(gc, config) -> dict:
    """DB_Master_Nicknames から 正式名称 → HR_Employee_ID の辞書を作成"""
    sh = gc.open_by_key(config["backend_db_id"])
    ws = sh.worksheet("DB_Master_Nicknames")
    data = ws.get_all_values()
    if not data or len(data[0]) < 6:
        logger.warning("DB_Master_Nicknames に HR_Employee_ID列(F列)がありません")
        return {}
    mapping = {}
    for row in data[1:]:
        if len(row) < 6:
            continue
        name = row[1].strip()
        emp_id = row[5].strip()
        if name and emp_id:
            try:
                mapping[name] = int(emp_id)
            except ValueError:
                continue
    return mapping


def find_date_columns(header_row: list, target_ym: str) -> list:
    """ヘッダー行 (row 2) から日付列の (col_index, date_str YYYY-MM-DD) のリストを返す。"""
    year, month = map(int, target_ym.split("-"))
    date_cols = []
    for i, cell in enumerate(header_row):
        m = re.match(r"^(\d{1,2})/(\d{1,2})$", cell.strip())
        if m:
            mm, dd = int(m.group(1)), int(m.group(2))
            # 月をまたぐ場合の判定: 対象月と一致しない月はスキップ
            if mm != month:
                continue
            date_str = f"{year:04d}-{mm:02d}-{dd:02d}"
            date_cols.append((i, date_str))
    return date_cols


def find_payment_type_col(header_row: list, cat_label_row: list, data_rows: list) -> Optional[int]:
    """区分列のインデックスを探す。新フォーマットは header="区分"、旧フォーマットは値から推測。"""
    try:
        return header_row.index("区分")
    except ValueError:
        pass
    valid = {"給与", "業務委託", "追加"}
    for col_idx in range(len(header_row) - 1, -1, -1):
        for row in data_rows:
            if col_idx < len(row) and row[col_idx].strip() in valid:
                return col_idx
    return None


def register(target_ym: str, dry_run: bool = False, force: bool = False) -> bool:
    """指定月のworktimeから「給与」スタッフを抽出し、HR勤怠登録する。

    Args:
        target_ym: 対象月 (YYYY-MM)
        dry_run: 実際のAPI呼び出しをスキップ
        force: 既存勤怠データがあっても上書きする

    Returns:
        全行成功時 True
    """
    gc_auth = auth_gspread()
    gc = gspread.authorize(gc_auth)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    hr_emp_map = load_hr_employee_map(gc, config)
    logger.info(f"HR_Employee_ID登録 {len(hr_emp_map)} 名")

    wt_sh = gc.open_by_key(config["working_hours_id"])
    try:
        ws = wt_sh.worksheet(f"{target_ym}_稼働時間")
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"シート '{target_ym}_稼働時間' が見つかりません")
        return False

    data = ws.get_all_values()
    if len(data) < 4:
        logger.error("シートにデータがありません")
        return False

    header_row = data[1]
    cat_label_row = data[2]
    staff_rows = data[3:]

    # 日付列の特定
    date_cols = find_date_columns(header_row, target_ym)
    logger.info(f"検出日付列: {len(date_cols)} 日 — {[d for _, d in date_cols]}")

    # 区分列の特定
    payment_type_idx = find_payment_type_col(header_row, cat_label_row, staff_rows)
    if payment_type_idx is None:
        logger.error("区分列が見つかりません")
        return False

    # HRクライアント初期化
    hr = FreeeHRClient() if not dry_run else None

    # 「給与」スタッフを抽出して登録
    tasks = []  # (staff_name, emp_id, date, minutes)
    skipped_no_empid = []
    for row in staff_rows:
        if not row or not row[0].strip():
            continue
        if len(row) <= payment_type_idx:
            continue
        if row[payment_type_idx].strip() != TARGET_PAYMENT_TYPE:
            continue

        staff_name = row[0].strip()
        emp_id = hr_emp_map.get(staff_name)
        if not emp_id:
            skipped_no_empid.append(staff_name)
            continue

        for col_idx, date_str in date_cols:
            if col_idx >= len(row):
                continue
            minutes = parse_time_str(row[col_idx])
            if minutes is None or minutes <= 0:
                continue
            tasks.append((staff_name, emp_id, date_str, minutes))

    if not tasks:
        logger.warning(f"登録対象が見つかりません（給与スタッフ {len([r for r in staff_rows if len(r)>payment_type_idx and r[payment_type_idx].strip()==TARGET_PAYMENT_TYPE])} 名）")
        return True

    # サマリ表示
    print(f"\n=== 人事労務freee 勤怠登録 {'(DRY RUN)' if dry_run else ''} ===")
    print(f"対象月: {target_ym}, 登録件数: {len(tasks)}")
    print()
    for name, emp_id, date, mins in tasks:
        h, m = mins // 60, mins % 60
        print(f"  {name} (emp={emp_id})  {date}  {h}:{m:02d} ({mins}分)")
    print()

    if skipped_no_empid:
        print(f"⚠ HR_Employee_ID未登録のスキップ: {skipped_no_empid}")
        print()

    if dry_run:
        print("[DRY RUN] 実際の登録は行いません。--dry-run を外すと登録します。")
        return True

    # 実登録
    success_count = 0
    error_count = 0
    for name, emp_id, date, minutes in tasks:
        # 既存データ取得
        existing = hr.get_work_record(emp_id, date)
        existing_clock_in = existing.get("clock_in_at") if existing else None
        if existing_clock_in and not force:
            print(f"  SKIP: {name} {date} は既に勤怠登録あり（--force で上書き可能）")
            continue

        # clock_in/clock_out を計算 (09:00 を基準に minutes ぶん勤務)
        clock_in_dt = datetime.fromisoformat(f"{date}T{DEFAULT_CLOCK_IN}:00")
        clock_out_dt = clock_in_dt + timedelta(minutes=minutes)
        clock_in_at = clock_in_dt.strftime("%Y-%m-%dT%H:%M:%S") + TZ_SUFFIX
        clock_out_at = clock_out_dt.strftime("%Y-%m-%dT%H:%M:%S") + TZ_SUFFIX

        body = {
            "company_id": hr.company_id,
            "clock_in_at": clock_in_at,
            "clock_out_at": clock_out_at,
            "day_pattern": "normal_work",
            "use_default_work_pattern": False,
            "break_records": [],
        }
        result = hr.put_work_record(emp_id, date, body)
        if result is None:
            error_count += 1
            print(f"  FAILED: {name} {date}")
        else:
            success_count += 1
            print(f"  OK: {name} {date} {clock_in_at[11:16]}-{clock_out_at[11:16]}")

    print(f"\n=== 完了 — 成功 {success_count} 件 / 失敗 {error_count} 件 ===")
    return error_count == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="稼働時間シートから「給与」スタッフ分を人事労務freeeに勤怠登録する"
    )
    parser.add_argument("--month", required=True, help="対象月 YYYY-MM")
    parser.add_argument("--dry-run", action="store_true", help="実APIを叩かず登録予定だけ表示")
    parser.add_argument("--force", action="store_true", help="既存の勤怠データがあっても上書き")
    args = parser.parse_args()

    ok = register(args.month, dry_run=args.dry_run, force=args.force)
    sys.exit(0 if ok else 1)
