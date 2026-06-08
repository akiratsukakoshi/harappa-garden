#!/usr/bin/env python3
"""sheets_client — 経費レビュー用 Google Sheets クライアント(S38 案A)。

件数が多い月に、ガクチョが Discord チャットで「N件目を…」と往復する代わりに、
**Google Sheets で直接一括編集** できるようにするための層。

方式は shift_manager と同じ「ガクチョ所有の既存ワークブックを SA に共有 → 毎月新規タブを
書き込む」。SA 所有の新規ファイルはガクチョの Drive に出ない問題を、ガクチョ所有ワークブック
+ タブ追記で回避する。

- 認証: expense の service account(secrets/credentials.json)をそのまま流用。Sheets スコープを追加。
- ワークブック: env `EXPENSE_REVIEW_SHEET_ID`(ガクチョが1回作成 → SA に Editor 共有 → ID を .env へ)。
- タブ: `{YYYYMM}`。既存同名タブは作り直す(working CSV が常に正本)。

列は working CSV の 8 列と 1:1(位置固定)。読み戻しは列位置でマップするので、
ガクチョは「行の削除」「費目/金額/部門の編集」を自由にしてよいが、**列の並べ替えはしない**こと。
"""
import os

import gspread
from google.oauth2 import service_account

_SECRETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "secrets")
_CREDENTIALS_PATH = os.path.join(_SECRETS_DIR, "credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# working CSV のキー(processor.py の DictWriter headers と一致) → シート上の日本語見出し。
# 位置固定。読み戻しはこの順序で列を CSV キーにマップする。
COLUMNS = [
    ("occurrence_date", "発生日"),
    ("registration_date", "登録日(支払期日)"),
    ("account_item", "費目"),
    ("details", "内容"),
    ("amount", "金額"),
    ("department", "部門"),
    ("description", "摘要"),
    ("status", "状態"),
]
CSV_KEYS = [k for k, _ in COLUMNS]
JP_HEADERS = [j for _, j in COLUMNS]
ACCOUNT_ITEM_COL = CSV_KEYS.index("account_item")  # 費目列(0始まり)= データ検証の対象


def _spreadsheet(review_id=None):
    review_id = review_id or os.getenv("EXPENSE_REVIEW_SHEET_ID")
    if not review_id:
        raise RuntimeError(
            "EXPENSE_REVIEW_SHEET_ID が未設定です。レビュー用シートを作成し SA "
            "(harappa-drive-bot@…)に Editor 共有して .env に ID を記入してください。"
        )
    creds = service_account.Credentials.from_service_account_file(
        _CREDENTIALS_PATH, scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(review_id)


def write_tab(rows, tab_name, categories, review_id=None):
    """working CSV の行(dict のリスト)を `{tab_name}` タブに書き出す。

    rows: [{occurrence_date, registration_date, account_item, details, amount,
            department, description, status}, ...]
    既存同名タブは削除して作り直す(working CSV が正本なので冪等)。
    戻り値: (sheet_url, gid)
    """
    sh = _spreadsheet(review_id)

    # 既存同名タブを掃除
    try:
        old = sh.worksheet(tab_name)
        sh.del_worksheet(old)
    except gspread.exceptions.WorksheetNotFound:
        pass

    n = len(rows)
    ws = sh.add_worksheet(tab_name, rows=max(n + 5, 10), cols=len(COLUMNS) + 1)

    values = [JP_HEADERS]
    review_row_indices = []  # 0始まり(ヘッダ除く)。要確認行のハイライト用
    for i, r in enumerate(rows):
        values.append([str(r.get(k, "") if r.get(k) is not None else "") for k in CSV_KEYS])
        details = str(r.get("details", ""))
        if "[要確認" in details:
            review_row_indices.append(i)
    ws.update(range_name="A1", values=values)

    requests = [
        # ヘッダ固定 + 太字 + 背景
        {"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": len(COLUMNS)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.73, "green": 0.85, "blue": 0.98},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat",
        }},
        # 費目列にプルダウン(5分類)。strict=False = 範囲外も警告のみで許容(最終ガードは dry-run)
        {"setDataValidation": {
            "range": {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": n + 1,
                      "startColumnIndex": ACCOUNT_ITEM_COL, "endColumnIndex": ACCOUNT_ITEM_COL + 1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST",
                              "values": [{"userEnteredValue": c} for c in categories]},
                "showCustomUi": True,
                "strict": False,
            },
        }},
    ]
    # 要確認行を薄い黄色に
    for idx in review_row_indices:
        requests.append({"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": idx + 1, "endRowIndex": idx + 2,
                      "startColumnIndex": 0, "endColumnIndex": len(COLUMNS)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.7},
            }},
            "fields": "userEnteredFormat.backgroundColor",
        }})

    sh.batch_update({"requests": requests})

    url = f"https://docs.google.com/spreadsheets/d/{sh.id}/edit#gid={ws.id}"
    return url, ws.id


def read_tab(tab_name, review_id=None):
    """`{tab_name}` タブを読み戻して working CSV 行(dict のリスト)を返す。

    1 行目はヘッダとして捨てる。列位置で CSV キーにマップ(列の並べ替えは非対応)。
    空行(全セル空)はスキップ。金額が空/0 の行もスキップ(削除扱い)。
    """
    sh = _spreadsheet(review_id)
    ws = sh.worksheet(tab_name)
    raw = ws.get_all_values()
    rows = []
    for r in raw[1:]:
        if not any(c.strip() for c in r):
            continue
        rec = {}
        for i, key in enumerate(CSV_KEYS):
            rec[key] = r[i].strip() if i < len(r) else ""
        # 金額が空 or 0 の行は「削除された/無効」とみなしスキップ
        amt = rec.get("amount", "").replace(",", "").strip()
        if not amt or amt == "0":
            continue
        rows.append(rec)
    return rows
