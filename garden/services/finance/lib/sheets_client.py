#!/usr/bin/env python3
"""sheets_client — finance 区画のレビュー用 Google Sheets(汎用版)。

importer(売上記帳)と auditor(部門監査)が、件数の多い月でもガクチョが
**Sheets で一括編集**してから承認できるようにするための層。expense-processor の
sheets_client を、列スキーマを呼び出し側から渡せる汎用形に一般化したもの。

方式は expense / invoice と同じ:ガクチョ所有の既存ワークブックを SA に Editor 共有し、
毎月新規タブ(`{prefix}{YYYYMM}`)を書き込む。SA 所有の新規ファイルはガクチョの Drive に
出ない問題を、ガクチョ所有ワークブック + タブ追記で回避する。

- 認証: finance の service account(secrets/credentials.json)。Sheets + Drive スコープ。
- ワークブック: env `FINANCE_REVIEW_SHEET_ID`(ガクチョが1回作成 → SA に Editor 共有 → ID を .env へ)。
- ガクチョは「行の削除」「セルの編集」は自由。ただし **列の並べ替えはしない**(読み戻しは列位置でマップ)。
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


def _spreadsheet(review_id=None):
    review_id = review_id or os.getenv("FINANCE_REVIEW_SHEET_ID")
    if not review_id:
        raise RuntimeError(
            "FINANCE_REVIEW_SHEET_ID が未設定です。レビュー用シートを作成し SA "
            "(harappa-drive-bot@…)に Editor 共有して .env に ID を記入してください。"
        )
    creds = service_account.Credentials.from_service_account_file(
        _CREDENTIALS_PATH, scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(review_id)


def write_tab(rows, tab_name, columns, dropdown_key=None, dropdown_values=None,
              highlight_keys=None, review_id=None):
    """rows(dict のリスト)を `{tab_name}` タブに書き出す。

    columns: [(csv_key, jp_header), ...] 位置固定。読み戻しはこの順序でマップ。
    dropdown_key: プルダウンを付ける列の csv_key(例 "section_name")。None ならなし。
    dropdown_values: プルダウンの選択肢(例 部門名リスト)。
    highlight_keys: この csv_key 群のいずれかが空の行を薄黄でハイライト(要入力の目印)。
    既存同名タブは削除して作り直す(working CSV が正本なので冪等)。
    戻り値: (sheet_url, gid)
    """
    sh = _spreadsheet(review_id)
    csv_keys = [k for k, _ in columns]
    jp_headers = [j for _, j in columns]

    try:
        old = sh.worksheet(tab_name)
        sh.del_worksheet(old)
    except gspread.exceptions.WorksheetNotFound:
        pass

    n = len(rows)
    ws = sh.add_worksheet(tab_name, rows=max(n + 5, 10), cols=len(columns) + 1)

    values = [jp_headers]
    highlight_row_indices = []  # 0始まり(ヘッダ除く)
    for i, r in enumerate(rows):
        values.append([str(r.get(k, "") if r.get(k) is not None else "") for k in csv_keys])
        if highlight_keys and any(not str(r.get(k, "")).strip() for k in highlight_keys):
            highlight_row_indices.append(i)
    ws.update(range_name="A1", values=values)

    requests = [
        {"updateSheetProperties": {
            "properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        {"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": len(columns)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.73, "green": 0.85, "blue": 0.98},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat",
        }},
    ]
    if dropdown_key and dropdown_values and dropdown_key in csv_keys:
        col = csv_keys.index(dropdown_key)
        requests.append({"setDataValidation": {
            "range": {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": n + 1,
                      "startColumnIndex": col, "endColumnIndex": col + 1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST",
                              "values": [{"userEnteredValue": v} for v in dropdown_values]},
                "showCustomUi": True,
                "strict": False,
            },
        }})
    for idx in highlight_row_indices:
        requests.append({"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": idx + 1, "endRowIndex": idx + 2,
                      "startColumnIndex": 0, "endColumnIndex": len(columns)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.7},
            }},
            "fields": "userEnteredFormat.backgroundColor",
        }})

    sh.batch_update({"requests": requests})
    url = f"https://docs.google.com/spreadsheets/d/{sh.id}/edit#gid={ws.id}"
    return url, ws.id


def read_tab(tab_name, columns, review_id=None):
    """`{tab_name}` タブを読み戻して dict のリストを返す。

    columns: write_tab と同じ [(csv_key, jp_header), ...]。列位置で csv_key にマップ。
    1 行目(ヘッダ)は捨てる。全セル空の行はスキップ。
    値の妥当性(金額0・部門空など)の判定は呼び出し側に委ねる。
    """
    sh = _spreadsheet(review_id)
    ws = sh.worksheet(tab_name)
    raw = ws.get_all_values()
    csv_keys = [k for k, _ in columns]
    rows = []
    for r in raw[1:]:
        if not any(c.strip() for c in r):
            continue
        rec = {}
        for i, key in enumerate(csv_keys):
            rec[key] = r[i].strip() if i < len(r) else ""
        rows.append(rec)
    return rows
