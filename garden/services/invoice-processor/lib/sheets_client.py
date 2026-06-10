"""sheets_client — 請求書レビュー用 Google Sheets クライアント。

expense-processor の S38 案A と同じ方式: ガクチョ所有の既存ワークブックに毎月新規タブを
書き込み、ガクチョが直接編集 → from-sheet で読み戻して register に渡す。

差分:
- 認証は SA でなく user OAuth(lib/user_google.py)。ガクチョ所有ワークブックを
  自分の権限で読むので SA 共有の手順が不要
- 列は invoice review CSV(register 互換 18 列 + スタッフ照合 3 列)
- ハイライト: MISMATCH 行 = 黄色 / リスト外(スタッフでない請求元)行 = 薄い青

ワークブック: env `INVOICE_REVIEW_SHEET_ID`(ガクチョが 1 回作成 → ID を .env へ)。
タブ: `{YYYYMM}`。既存同名タブは作り直す(working CSV が常に正本)。
列の並べ替えはしないこと(読み戻しは列位置でマップ)。
"""
import os

import gspread

from .user_google import load_credentials

# review CSV のキー(processor.py の headers と一致)→ シート上の日本語見出し。位置固定。
COLUMNS = [
    ("file_id", "file_id"),
    ("file_name", "ファイル名"),
    ("date", "取引日"),
    ("payee", "支払先"),
    ("", "✓"),
    ("partner_code", "取引先コード"),
    ("partner_id", "取引先ID"),
    ("description", "内容"),
    ("section_name", "部門"),
    ("section_id", "部門ID"),
    ("account_item_name", "勘定科目"),
    ("invoice_number", "インボイス番号"),
    ("amount", "金額"),
    ("document_total", "請求書総額"),
    ("calculated_total", "明細合計"),
    ("diff", "差分"),
    ("warning", "警告"),
    ("tax_code", "税区分"),
    ("staff_slug", "スタッフ"),
    ("staff_contract", "契約区分"),
    ("group", "グループ"),
]
CSV_KEYS = [k for k, _ in COLUMNS]
JP_HEADERS = [j for _, j in COLUMNS]
ACCOUNT_ITEM_COL = CSV_KEYS.index("account_item_name")
SECTION_NAME_COL = CSV_KEYS.index("section_name")
WARNING_COL = CSV_KEYS.index("warning")
GROUP_COL = CSV_KEYS.index("group")


def _spreadsheet(review_id=None):
    review_id = review_id or os.getenv("INVOICE_REVIEW_SHEET_ID")
    if not review_id:
        raise RuntimeError(
            "INVOICE_REVIEW_SHEET_ID が未設定です。レビュー用ワークブックを作成して "
            ".env に ID を記入してください(user OAuth で読むので共有操作は不要)。"
        )
    gc = gspread.authorize(load_credentials())
    return gc.open_by_key(review_id)


def write_tab(rows, tab_name, categories, sections=None, review_id=None):
    """review CSV の行(dict のリスト)を `{tab_name}` タブに書き出す。

    categories: 勘定科目プルダウンの選択肢 / sections: 部門プルダウンの選択肢(任意)
    戻り値: (sheet_url, gid)
    """
    sh = _spreadsheet(review_id)

    try:
        old = sh.worksheet(tab_name)
        sh.del_worksheet(old)
    except gspread.exceptions.WorksheetNotFound:
        pass

    n = len(rows)
    ws = sh.add_worksheet(tab_name, rows=max(n + 5, 10), cols=len(COLUMNS) + 1)

    values = [JP_HEADERS]
    mismatch_rows = []   # 0 始まり(ヘッダ除く)
    outside_rows = []    # リスト外(スタッフでない請求元)
    for i, r in enumerate(rows):
        values.append([str(r.get(k, "") if r.get(k) is not None else "") for k in CSV_KEYS])
        if str(r.get("warning", "")).strip():
            mismatch_rows.append(i)
        elif str(r.get("group", "")) == "リスト外":
            outside_rows.append(i)
    ws.update(range_name="A1", values=values)

    requests = [
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
    if sections:
        requests.append({"setDataValidation": {
            "range": {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": n + 1,
                      "startColumnIndex": SECTION_NAME_COL, "endColumnIndex": SECTION_NAME_COL + 1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST",
                              "values": [{"userEnteredValue": s} for s in sections]},
                "showCustomUi": True,
                "strict": False,
            },
        }})
    # リスト外行 = 薄い青(どれがスタッフ請求でないか一目で分かるように)
    for idx in outside_rows:
        requests.append({"repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": idx + 1, "endRowIndex": idx + 2,
                      "startColumnIndex": 0, "endColumnIndex": len(COLUMNS)},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.88, "green": 0.94, "blue": 1.0},
            }},
            "fields": "userEnteredFormat.backgroundColor",
        }})
    # MISMATCH 等の警告行 = 薄い黄色(要確認が最優先で目立つ)
    for idx in mismatch_rows:
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
    """`{tab_name}` タブを読み戻して review CSV 行(dict のリスト)を返す。

    1 行目はヘッダとして捨て、列位置で CSV キーにマップ(列の並べ替えは非対応)。
    空行と金額が空/0 の行(= ガクチョが削除した行)はスキップ。
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
        amt = rec.get("amount", "").replace(",", "").replace("¥", "").strip()
        if not amt or amt == "0":
            continue
        rows.append(rec)
    return rows
