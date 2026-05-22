#!/usr/bin/env python3
"""export_external_staff.py - 稼働時間シートからAD列=「追加」のスタッフ分をCSV出力する

invoice_processor の register コマンドにそのまま渡せる形式のCSVを生成する。
カテゴリ別金額 (W〜AB列) から、金額>0の部門ごとに行を展開する。
"""

import sys
import os
import json
import csv
import argparse
from datetime import date

import gspread
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from modules.utils import setup_logger
from modules.freee_client import FreeeClient

logger = setup_logger("ExportExternalStaff")

CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"
SECTION_MAPPING_PATH = "apps/shift_manager/section_mapping.json"
OUTPUT_DIR = "data/invoice_processor/review"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TARGET_PAYMENT_TYPE = "追加"
DEFAULT_TAX_CODE = "20: without_tax"  # 個人払いなので非課税扱い


def auth():
    """Service Account優先で認証。失敗時はOAuth Userへフォールバック。"""
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


def parse_amount(cell: str) -> int:
    """セルの金額文字列を整数に変換する。「¥36,958」「36958」「¥0」「」等に対応。"""
    if not cell:
        return 0
    s = cell.strip().replace("¥", "").replace(",", "")
    if not s or s == "-":
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def load_section_mapping() -> tuple:
    """section_mapping.jsonを読み込み (mapping, default_account_item) を返す"""
    with open(SECTION_MAPPING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mapping", {}), data.get("default_account_item", "外注費")


def export(target_ym: str, output_path: str = "") -> str:
    """指定月の稼働時間シートを読み、AD=「追加」スタッフのCSVを出力する。

    Args:
        target_ym: 対象月 (YYYY-MM)
        output_path: 出力先パス（省略時はOUTPUT_DIRに自動命名で出力）

    Returns:
        出力ファイルのパス
    """
    creds = auth()
    gc = gspread.authorize(creds)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    section_map, default_account = load_section_mapping()

    wt_sh = gc.open_by_key(config["working_hours_id"])
    try:
        ws = wt_sh.worksheet(f"{target_ym}_稼働時間")
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"シート '{target_ym}_稼働時間' が見つかりません。")
        return ""

    data = ws.get_all_values()
    if len(data) < 4:
        logger.error("シートにデータがありません。")
        return ""

    # ヘッダー行を解析して列インデックスを決定
    # 新フォーマット (generate_working_hours.py): header に「合計」「合計額」「区分」が存在
    # 旧フォーマット (4月以前の手動編集): row 3 に金額カテゴリ・合計、区分はAD列(値のみ)
    header = data[1]
    cat_label = data[2]

    # 1. 時間の「合計」列を探す（row 2 ヘッダー）
    try:
        total_hours_idx = header.index("合計")
    except ValueError:
        logger.error("ヘッダー行に「合計」列が見つかりません。シートのフォーマットを確認してください。")
        return ""

    # 2. 金額カテゴリの開始位置 = 合計の次の列
    amount_start_idx = total_hours_idx + 1

    # 3. 金額カテゴリ名を抽出
    # 新フォーマット: header に "○○額" がある
    # 旧フォーマット: row 3 (cat_label) に "○○" がある
    amount_cats = []
    total_amount_idx = None
    payment_type_idx = None

    for col_idx in range(amount_start_idx, len(header)):
        h = header[col_idx].strip() if col_idx < len(header) else ""
        c = cat_label[col_idx].strip() if col_idx < len(cat_label) else ""

        # 「合計額」または row3 の「合計」が出たら金額カテゴリ終了
        if h == "合計額" or (not h and c == "合計"):
            total_amount_idx = col_idx
            break
        # 「区分」が出たらここで終了（合計額なし）
        if h == "区分":
            payment_type_idx = col_idx
            break

        # カテゴリ名を取得 (header優先、なければrow 3)
        if h.endswith("額"):
            cat_name = h[:-1]
        elif c and c != "合計":
            cat_name = c
        elif h:
            cat_name = h
        else:
            # 空セル → カテゴリ列終了
            break
        amount_cats.append(cat_name)

    if not amount_cats:
        logger.error("金額カテゴリ列が検出できません。シートのフォーマットを確認してください。")
        return ""

    # 4. 区分(PaymentType)列を特定
    if payment_type_idx is None:
        # 新フォーマット: 合計額の次に「区分」
        if total_amount_idx is not None:
            search_start = total_amount_idx + 1
            for col_idx in range(search_start, len(header)):
                if header[col_idx].strip() == "区分":
                    payment_type_idx = col_idx
                    break
        # 旧フォーマット: AD列(index=29)固定で区分値が入っているはず → 最後の非空列の値を見る
        if payment_type_idx is None:
            # データ行から「給与/業務委託/追加」のいずれかが入っている列を探す
            valid_types = {"給与", "業務委託", "追加"}
            for col_idx in range(len(header) - 1, amount_start_idx, -1):
                for row in data[3:]:
                    if col_idx < len(row) and row[col_idx].strip() in valid_types:
                        payment_type_idx = col_idx
                        break
                if payment_type_idx is not None:
                    break

    if payment_type_idx is None:
        logger.error("区分(PaymentType)列が見つかりません。AD列に '給与/業務委託/追加' のいずれかが入力されていることを確認してください。")
        return ""

    logger.info(f"検出カテゴリ: {amount_cats}")
    logger.info(f"金額開始列: {amount_start_idx}, 区分列: {payment_type_idx}")

    # Freee partnersを取得（partner_id解決用）
    fc = FreeeClient()
    partners = fc.get_partners() or []
    name_to_partner_id = {p["name"]: p["id"] for p in partners if p.get("name")}

    # データ行を処理
    output_rows = []
    skipped_no_partner = []
    today = date.today()
    # 月末日付（請求日として使用）
    year, month = map(int, target_ym.split("-"))
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)
    from datetime import timedelta
    invoice_date = (last_day - timedelta(days=1)).strftime("%Y/%m/%d")

    n_target = 0
    file_counter = 0
    for staff_row in data[3:]:
        if not staff_row or not staff_row[0].strip():
            continue
        if len(staff_row) <= payment_type_idx:
            continue

        ptype = staff_row[payment_type_idx].strip()
        if ptype != TARGET_PAYMENT_TYPE:
            continue

        n_target += 1
        staff_name = staff_row[0].strip()
        partner_id = name_to_partner_id.get(staff_name, "")
        if not partner_id:
            skipped_no_partner.append(staff_name)

        # 各カテゴリで金額>0なら1行展開
        file_counter += 1
        file_id = f"{target_ym.replace('-', '')}_extra_{file_counter:03d}"
        for cat_idx, cat_name in enumerate(amount_cats):
            col_idx = amount_start_idx + cat_idx
            if col_idx >= len(staff_row):
                continue
            amount = parse_amount(staff_row[col_idx])
            if amount <= 0:
                continue

            section_name = section_map.get(cat_name, cat_name)
            output_rows.append({
                "file_id": file_id,
                "file_name": "",
                "date": invoice_date,
                "payee": staff_name,
                "": "OK",
                "partner_code": "",
                "partner_id": partner_id,
                "description": f"{target_ym} {cat_name} 稼働分",
                "section_name": section_name,
                "section_id": "",
                "account_item_name": default_account,
                "invoice_number": "",
                "amount": amount,
                "document_total": "",
                "calculated_total": "",
                "diff": "",
                "warning": "",
                "tax_code": DEFAULT_TAX_CODE,
            })

    if not output_rows:
        logger.warning(f"AD列='{TARGET_PAYMENT_TYPE}' の対象行がありません（処理対象スタッフ {n_target} 名）")
        return ""

    # 出力先パス決定
    if not output_path:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(
            OUTPUT_DIR,
            f"external_staff_{target_ym.replace('-', '')}.csv"
        )

    # CSV出力 (invoice_processor の register が期待するフォーマット)
    fieldnames = [
        "file_id", "file_name", "date", "payee", "",
        "partner_code", "partner_id", "description",
        "section_name", "section_id", "account_item_name",
        "invoice_number", "amount", "document_total", "calculated_total",
        "diff", "warning", "tax_code",
    ]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)

    logger.info(f"CSV出力完了: {output_path} ({len(output_rows)} 行 / {n_target} 名)")
    print(f"\n✓ CSV出力完了: {output_path}")
    print(f"  対象スタッフ: {n_target} 名 / 展開行数: {len(output_rows)} 行")
    if skipped_no_partner:
        print(f"\n⚠ Freeeに取引先登録のないスタッフ ({len(skipped_no_partner)} 名):")
        for n in skipped_no_partner:
            print(f"    - {n}  (partner_id 空欄で出力されています)")
        print("  Freeeで取引先を新規登録するか、CSVで partner_id を手入力してください。")

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="稼働時間シートからAD=「追加」スタッフのinvoice_processor向けCSVを出力する"
    )
    parser.add_argument("--month", required=True, help="対象月 YYYY-MM")
    parser.add_argument("--output", default="", help="出力先CSVパス（省略時は自動命名）")
    args = parser.parse_args()

    path = export(args.month, args.output)
    if not path:
        sys.exit(1)
