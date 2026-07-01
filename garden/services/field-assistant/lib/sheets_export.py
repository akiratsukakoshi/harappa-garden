#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""名簿のスプレッドシート出力 + 月末クリア。

方式は expense S38 案A と同じ「ガクチョ所有ワークブックを SA に Editor 共有」。
- ワークブック: env `FIELD_ROSTER_SHEET_ID`(⭐ガクチョが 1 回作成 → SA に共有)
- タブ名: `MMDD`(例 `0613`)。同名タブは作り直し(冪等)。
- 月末 `clear_all` で README 以外の全タブを削除(スプシ増殖防止、ガクチョ要望 S42)。
"""
from __future__ import annotations

import os

import gspread
from google.oauth2 import service_account

from . import stores_lib

_DEFAULT_SA = "/home/vps-harappa/garden/services/shift-manager/secrets/credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 月末 clear_all の削除対象から除外するタブ。
# 振替チェックは毎月このタブに上書きするので月末掃除でも残す(A案・ガクチョ決定 S45)。
FURIKAE_TAB = "月謝振替チェック"
KEEP_TABS = {"README", "readme", FURIKAE_TAB}


def _workbook():
    sheet_id = os.environ.get("FIELD_ROSTER_SHEET_ID")
    if not sheet_id:
        raise RuntimeError(
            "FIELD_ROSTER_SHEET_ID が未設定です。名簿用ワークブックを作成し "
            "SA に Editor 共有して .env に ID を記入してください。"
        )
    sa = os.environ.get("GOOGLE_SA_FILE", _DEFAULT_SA)
    creds = service_account.Credentials.from_service_account_file(sa, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(sheet_id)


def write_roster_tab(rows: list[dict], tab_name: str) -> str:
    """名簿行をタブに書き出して URL を返す。既存同名タブは作り直す。"""
    sh = _workbook()
    try:
        sh.del_worksheet(sh.worksheet(tab_name))
    except gspread.exceptions.WorksheetNotFound:
        pass
    cols = stores_lib.ROSTER_COLUMNS
    ws = sh.add_worksheet(tab_name, rows=max(len(rows) + 5, 10), cols=len(cols))
    data = [cols] + [[str(r.get(c, "") or "") for c in cols] for r in rows]
    ws.update(data, "A1")
    ws.format("A1:Z1", {"textFormat": {"bold": True}})
    ws.freeze(rows=1)
    # アレルギー・留意事項が「なし」以外の行を黄色に(現場で見落とさないため)
    allergy_idx = cols.index("アレルギー・留意事項")
    for i, r in enumerate(rows, start=2):
        a = (r.get("アレルギー・留意事項") or "").strip()
        if a and a not in ("なし", "ナシ", "無し", "特になし"):
            ws.format(f"A{i}:{chr(ord('A') + len(cols) - 1)}{i}",
                      {"backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.6}})
    return f"https://docs.google.com/spreadsheets/d/{sh.id}/edit#gid={ws.id}"


FURIKAE_COLUMNS = ["顧客名", "契約中の月謝", "当月予約件数", "当月参加回数",
                   "うち月謝利用回数", "参加明細", "振替要否"]


def write_furikae_tab(rows: list[dict], month: str) -> str:
    """月謝振替チェックの全会員行を固定タブに書き出して URL を返す。

    タブ名は固定(FURIKAE_TAB)で毎月上書き。月末 clear_all の KEEP_TABS に
    含まれるため掃除では消えない(A案)。振替対象(振替要否 = 要)の行は黄色表示。
    """
    sh = _workbook()
    try:
        sh.del_worksheet(sh.worksheet(FURIKAE_TAB))
    except gspread.exceptions.WorksheetNotFound:
        pass
    cols = FURIKAE_COLUMNS
    # 1 行目に対象月見出し、2 行目にヘッダ、3 行目以降にデータ
    title = [f"{month} 月謝未消化チェック(月謝会員 {len(rows)}名)"] + [""] * (len(cols) - 1)
    ws = sh.add_worksheet(FURIKAE_TAB, rows=max(len(rows) + 6, 10), cols=len(cols))
    data = [title, cols] + [[str(r.get(c, "") or "") for c in cols] for r in rows]
    ws.update(data, "A1")
    ws.format("A1:Z2", {"textFormat": {"bold": True}})
    ws.freeze(rows=2)
    last_col = chr(ord("A") + len(cols) - 1)
    for i, r in enumerate(rows, start=3):
        if str(r.get("振替要否") or "").strip() in ("要", "○", "要振替"):
            ws.format(f"A{i}:{last_col}{i}",
                      {"backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.6}})
    return f"https://docs.google.com/spreadsheets/d/{sh.id}/edit#gid={ws.id}"


def clear_all() -> list[str]:
    """README 以外の全タブを削除(月末掃除)。戻り値 = 消したタブ名。"""
    sh = _workbook()
    sheets = sh.worksheets()
    removed = []
    survivors = [w for w in sheets if w.title in KEEP_TABS]
    if not survivors:
        # 全削除は不可(最低 1 タブ必要)なので placeholder を先に作る
        ph = sh.add_worksheet("README", rows=2, cols=1)
        ph.update([["名簿タブは月末に自動クリアされます(field_assistant)"]], "A1")
        survivors = [ph]
    for w in sheets:
        if w.title not in KEEP_TABS:
            sh.del_worksheet(w)
            removed.append(w.title)
    return removed
