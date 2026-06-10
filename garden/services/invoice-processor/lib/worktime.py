"""worktime — 稼働時間シート(`{YYYY-MM}_稼働時間`)の読み取り。

invoice_processor の稼働突合(請求漏れ検出)用。シートは shift-manager の
generate_working_hours.py が生成するもので、ワークブック ID は shift-manager の
config_ids.json(working_hours_id)が SSOT。列検出ロジックは HMC
export_external_staff.py から継承(新旧フォーマット両対応)。

行の意味(区分列):
- 業務委託 … 請求書を出して支払う人 → 稼働があるのに請求書が無ければアラート対象
- 給与     … 人事労務 freee で払う人(請求書なし)
- 追加     … 外部スタッフ。稼働時間から自動 CSV(HMC export_external_staff 相当)で払う
"""
import json
import os

import gspread

from .utils import setup_logger
from .user_google import load_credentials

logger = setup_logger("Worktime")

_SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# services/ は repo・VPS とも横並びなので相対で届く
DEFAULT_SHIFT_CONFIG = os.path.normpath(
    os.path.join(_SERVICE_DIR, "..", "shift-manager", "config", "config_ids.json")
)


def _workbook_id():
    wb_id = os.environ.get("WORKING_HOURS_SHEET_ID")
    if wb_id:
        return wb_id
    config_path = os.environ.get("SHIFT_CONFIG_PATH", DEFAULT_SHIFT_CONFIG)
    with open(config_path) as f:
        config = json.load(f)
    wb_id = config.get("working_hours_id")
    if not wb_id:
        raise RuntimeError(
            f"working_hours_id が見つかりません({config_path})。"
            "WORKING_HOURS_SHEET_ID を .env に設定してください。"
        )
    return wb_id


def read_worked_staff(target_ym: str, creds=None):
    """`{target_ym}_稼働時間` シートを読み、スタッフ行のリストを返す。

    各要素: {name, payment_type, hours}
    シートが無い月(集計前 / 開催なし)は None を返す(空リストと区別する)。
    """
    creds = creds or load_credentials()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(_workbook_id())
    try:
        ws = sh.worksheet(f"{target_ym}_稼働時間")
    except gspread.exceptions.WorksheetNotFound:
        logger.warning(f"シート '{target_ym}_稼働時間' が見つかりません。")
        return None

    data = ws.get_all_values()
    if len(data) < 4:
        logger.warning(f"シート '{target_ym}_稼働時間' にデータ行がありません。")
        return []

    header = data[1]

    # 時間の「合計」列(HMC export_external_staff と同じ検出)
    try:
        total_hours_idx = header.index("合計")
    except ValueError:
        total_hours_idx = None
        logger.warning("ヘッダー行に「合計」列が見つかりません(hours は空で続行)。")

    # 区分列: 新フォーマットは header に「区分」。旧フォーマットはデータ値から探す。
    payment_type_idx = None
    for i, h in enumerate(header):
        if h.strip() == "区分":
            payment_type_idx = i
            break
    if payment_type_idx is None:
        valid_types = {"給与", "業務委託", "追加"}
        for col_idx in range(len(header) - 1, 0, -1):
            if any(
                col_idx < len(row) and row[col_idx].strip() in valid_types
                for row in data[3:]
            ):
                payment_type_idx = col_idx
                break
    if payment_type_idx is None:
        raise RuntimeError(
            f"'{target_ym}_稼働時間' の区分列が検出できません。シートのフォーマットを確認してください。"
        )

    rows = []
    for row in data[3:]:
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        ptype = row[payment_type_idx].strip() if payment_type_idx < len(row) else ""
        hours = ""
        if total_hours_idx is not None and total_hours_idx < len(row):
            hours = row[total_hours_idx].strip()
        rows.append({"name": name, "payment_type": ptype, "hours": hours})

    logger.info(f"Read {len(rows)} staff rows from '{target_ym}_稼働時間'")
    return rows
