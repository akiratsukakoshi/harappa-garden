#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""シフトカレンダー(Monthly UI Sheet = プログラムカレンダー新)の読み取り。

正本: shift_manager の `config_ids.monthly_ui_id`(当月稼働の正本、S21 SKILL 参照)。
タブ = `YYYY-MM`。ヘッダー(1行目)は 2026-06 時点で:
  A日付 / B曜日 / C運営スケジュール / D会場 / Eカテゴリ / F活動内容 / G時間
  / H企画者 / I現場責任者 / J応急衛生 / Kスタッフ
列はヘッダー名で解決する(列の並び替えに強い。ヘッダー名変更には config 修正で追従)。

認証は shift-manager の service account を読み取り専用 scope で流用。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re

import gspread
from google.oauth2 import service_account

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SA = "/home/vps-harappa/garden/services/shift-manager/secrets/credentials.json"
_DEFAULT_IDS = "/home/vps-harappa/garden/services/shift-manager/config/config_ids.json"

# ヘッダー名 → 行 dict のキー
HEADER_MAP = {
    "日付": "date_raw",
    "曜日": "weekday",
    "運営スケジュール": "ops_schedule",
    "会場": "venue",
    "カテゴリ": "category",
    "活動内容": "activity",
    "時間": "time",
    "企画者": "planner",
    "現場責任者": "lead",
    "応急衛生": "first_aid",
    "スタッフ": "staff",
}


def _sa_file() -> str:
    return os.environ.get("GOOGLE_SA_FILE", _DEFAULT_SA)


def _calendar_id() -> str:
    cid = os.environ.get("SHIFT_CALENDAR_SHEET_ID")
    if cid:
        return cid
    ids_path = os.environ.get("SHIFT_CONFIG_IDS", _DEFAULT_IDS)
    with open(ids_path, encoding="utf-8") as f:
        return json.load(f)["monthly_ui_id"]


def _workbook():
    creds = service_account.Credentials.from_service_account_file(
        _sa_file(), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return gspread.authorize(creds).open_by_key(_calendar_id())


def _parse_date(raw: str, year: int):
    m = re.match(r"(\d{1,2})月(\d{1,2})日", (raw or "").strip())
    if not m:
        return None
    try:
        return dt.date(year, int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def read_month(month: str) -> list[dict]:
    """`YYYY-MM` タブの行 → イベント dict のリスト(カテゴリ or 活動内容があるもののみ)。"""
    wb = _workbook()
    try:
        ws = wb.worksheet(month)
    except gspread.exceptions.WorksheetNotFound:
        return []
    values = ws.get_values()
    if not values:
        return []
    header = values[0]
    keys = [HEADER_MAP.get(h.strip()) for h in header]
    year = int(month.split("-")[0])
    events = []
    for raw_row in values[1:]:
        row = {}
        for k, v in zip(keys, raw_row):
            if k:
                row[k] = v.strip()
        date = _parse_date(row.get("date_raw", ""), year)
        if date is None:
            continue
        if not (row.get("category") or row.get("activity")):
            continue  # 予定なしの日
        row["date"] = date
        events.append(row)
    return events


def events_between(start: dt.date, end: dt.date) -> list[dict]:
    """期間 [start, end](両端含む)のイベント。月跨ぎはタブ 2 枚読む。"""
    months = sorted({start.strftime("%Y-%m"), end.strftime("%Y-%m")})
    events = []
    for m in months:
        events.extend(read_month(m))
    return sorted(
        [e for e in events if start <= e["date"] <= end],
        key=lambda e: (e["date"], e.get("time", "")),
    )


WEEKDAY_JP = "月火水木金土日"


def date_jp(d: dt.date) -> str:
    return f"{d.month}/{d.day}({WEEKDAY_JP[d.weekday()]})"


def needs_planning_mtg(event: dict) -> bool:
    """企画MTGリマインドの対象か(おやこ学部・こども学部のみ、自由デー除く)。"""
    cat = event.get("category", "")
    text = cat + event.get("activity", "")
    if "自由" in text:
        return False
    return ("おやこ" in cat) or ("こども" in cat)
