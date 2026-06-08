#!/usr/bin/env python3
"""expense-processor — 個人経費の抽出 → Freee 登録(HMC apps/expense_processor/processor.py 移植)

Garden 化のための差分(業務知識は継承、起動と承認だけ Garden に変える):
- import パス: modules.* / apps.invoice_processor.* → lib.*(同 service 内に集約)
- データ dir をサービス相対の絶対パスに(cron で cwd 非依存)
- ⭐ tax_code を `EXPENSE_TAX_CODE` env で明示指定(HMC は既定 1 = 課税売上 で経費を
  登録していた誤りを正す。値は `processor.py taxes` で Freee の実コードを確認して設定)
- `taxes` サブコマンドを追加(get_taxes() の一覧表示。tax_code 確定用)

使い方:
    python processor.py taxes              # Freee の tax_code 一覧を表示(EXPENSE_TAX_CODE 確定用)
    python processor.py extract            # input → 中間 CSV(working/）
    python processor.py upload <csv> --dry-run   # 登録内容を確認
    python processor.py upload <csv>             # Freee に本登録 + アーカイブ
"""
import os
import sys
import argparse
import csv
import datetime
import json
import logging
import google.generativeai as genai
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from lib.freee_client import FreeeClient
from lib.utils import setup_logger, ensure_directory
from lib.drive_client import DriveClient

logger = setup_logger("ExpenseProcessor")

load_dotenv()

# Configuration — サービス相対の絶対パス(cron 実行で cwd に依存しない)
# dir 構成は SKILL / 種(SSOT)に合わせて service ルート直下に置く(input/ working/ proceeded/)。
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(_BASE_DIR, "input")
WORKING_DIR = os.path.join(_BASE_DIR, "working")
PROCEEDED_DIR = os.path.join(_BASE_DIR, "proceeded")
ARCHIVE_FORMAT = "%Y%m%d"

# Drive Configuration
DRIVE_FOLDER_ID = os.getenv("EXPENSE_DRIVE_FOLDER_ID")

# Gemini model — HMC 移植時の 'gemini-2.0-flash' は提供終了(404)だったため現行安定版に更新。
# 将来また退役しても env で差し替えられるよう定数化(コード変更不要)。
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# S38 タイムアウト対策(S37 で 77 件[画像16 + CSV61行]が 5 分タイムアウトに当たった):
# - CSV 明細の費目分類は 1 行 1 Gemini 呼び出しだと行数分の往復になる → 複数行を 1
#   プロンプトでまとめて分類(バッチ化)。1 リクエストの行数は CLASSIFY_BATCH_SIZE で上限。
# - レシート画像 OCR は 1 枚 1 リクエスト(画像はバッチ不可)なので、並列度を上げて圧縮する。
CLASSIFY_BATCH_SIZE = int(os.getenv("EXPENSE_CLASSIFY_BATCH_SIZE", "40"))
IMAGE_OCR_WORKERS = int(os.getenv("EXPENSE_IMAGE_OCR_WORKERS", "4"))

# ⭐ 経費の消費税区分(課税仕入)。`processor.py taxes` で実コードを確認して .env に設定する。
# 未設定だと post_deal が HMC 既定の 1(課税売上 10%)に落ちるため、upload 時に明示警告する。
_RAW_TAX_CODE = os.getenv("EXPENSE_TAX_CODE")
EXPENSE_TAX_CODE = int(_RAW_TAX_CODE) if _RAW_TAX_CODE and _RAW_TAX_CODE.strip() else None

# Target Categories
CATEGORIES = [
    "旅費交通費",
    "原材料",
    "消耗品費",
    "通信費",
    "会議費"
]

class ExpenseClassifier:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. AI classification will be disabled.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(GEMINI_MODEL)

    def classify(self, details: str, amount: int) -> str:
        if not self.model:
            return "消耗品費" # Default fallback

        prompt = f"""
        あなたは会計の専門家です。以下の支出内容と金額に基づき、最も適切な勘定科目をリストから1つ選択してください。

        リスト: {', '.join(CATEGORIES)}

        支出内容: {details}
        金額: {amount}円

        回答は勘定科目名のみを出力してください。それ以外の文字は含めないでください。
        """

        max_retries = 3
        base_wait = 2

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                classified = response.text.strip()
                if classified in CATEGORIES:
                    return classified

                for fat in CATEGORIES:
                    if fat in classified:
                        return fat
                return "消耗品費"
            except Exception as e:
                if "429" in str(e):
                    wait_time = base_wait * (2 ** attempt)
                    logger.warning(f"AI Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"AI Classification failed: {e}")
                    return "消耗品費"

        logger.error("AI Classification failed after retries.")
        return "消耗品費"

    def classify_batch(self, items: list) -> list:
        """複数行の費目を 1 リクエストでまとめて分類する(S38 バッチ化)。

        items: [{"details": str, "amount": int}, ...]
        返り値: items と同じ並び・同じ長さの費目名リスト。
        バッチが失敗(API エラー / 行数不一致 / JSON 不正)したときは、その範囲だけ
        1 行ずつ classify() にフォールバックする(黙って全部 消耗品費 にしない)。
        """
        if not items:
            return []
        if not self.model:
            return ["消耗品費"] * len(items)
        results: list = []
        for start in range(0, len(items), CLASSIFY_BATCH_SIZE):
            results.extend(self._classify_chunk(items[start:start + CLASSIFY_BATCH_SIZE]))
        return results

    def _classify_chunk(self, chunk: list) -> list:
        listing = "\n".join(
            f"{i + 1}. 内容: {it['details']} / 金額: {it['amount']}円"
            for i, it in enumerate(chunk)
        )
        prompt = f"""あなたは会計の専門家です。以下の各支出について、最も適切な勘定科目をリストから1つずつ選んでください。

リスト: {', '.join(CATEGORIES)}

支出一覧:
{listing}

回答は JSON 配列のみ。各要素は {{"n": 行番号(1始まり), "account_item": 勘定科目名}}。
リスト外の科目は使わない。全行を漏れなく含める。Markdown コードブロックは不要。
例: [{{"n": 1, "account_item": "消耗品費"}}, {{"n": 2, "account_item": "旅費交通費"}}]
"""
        max_retries = 3
        base_wait = 2

        def _fallback():
            logger.warning("Batch classify: 1行ずつにフォールバックします。")
            return [self.classify(it["details"], it["amount"]) for it in chunk]

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                elif text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                data = json.loads(text.strip())

                by_n = {}
                for entry in data:
                    n = int(entry["n"])
                    cat = str(entry.get("account_item", "")).strip()
                    if cat not in CATEGORIES:
                        cat = next((c for c in CATEGORIES if c in cat), "消耗品費")
                    by_n[n] = cat

                # 全行が揃っているか検証。1 つでも欠ければ黙って通さずフォールバック。
                if all((i + 1) in by_n for i in range(len(chunk))):
                    return [by_n[i + 1] for i in range(len(chunk))]
                logger.warning(
                    f"Batch classify: 行数不一致(期待 {len(chunk)} / 取得 {len(by_n)})。"
                )
                return _fallback()
            except Exception as e:
                if "429" in str(e):
                    wait_time = base_wait * (2 ** attempt)
                    logger.warning(f"AI Rate limit hit (batch). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Batch classify failed: {e}")
                    return _fallback()

        logger.error("Batch classify failed after retries.")
        return _fallback()

class CSVParser:
    def __init__(self):
        pass

    def parse(self, file_path: str) -> list:
        """
        Detect format and parse CSV. Returns list of dicts with standard keys:
        occurance_date, details, amount
        """
        # Try reading first few lines to detect format
        try:
            # First try UTF-8 (PayPay)
            with open(file_path, 'r', encoding='utf-8') as f:
                header_line = f.readline().strip()

            if "利用日/キャンセル日" in header_line:
                return self._parse_paypay(file_path)
        except UnicodeDecodeError:
            pass # Likely Shift-JIS

        # Try Shift-JIS (Aeon/Cosmo)
        try:
            with open(file_path, 'r', encoding='shift_jis') as f:
                 # Read first 10 lines to find header
                 lines = [f.readline() for _ in range(10)]
                 full_content = "".join(lines)
                 if "コスモ・ザ・カード" in full_content or "ご利用カード" in full_content:
                     return self._parse_aeon(file_path)
        except UnicodeDecodeError:
            pass

        logger.error(f"Unknown format: {file_path}")
        return []

    def _parse_paypay(self, file_path):
        results = []
        skip_keywords = ["チャージ", "回収事務手数料", "遅延損害金"]
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("利用日/キャンセル日"): continue

                details = row["利用店名・商品名"]
                if any(kw in details for kw in skip_keywords): continue

                try:
                    occ_date = datetime.datetime.strptime(row["利用日/キャンセル日"], "%Y/%m/%d").date()
                except ValueError:
                    logger.warning(f"Invalid date format in PayPay CSV: {row}")
                    continue

                amount = int(row["利用金額"]) if row["利用金額"] else 0
                if amount == 0: continue

                results.append({
                    "occurrence_date": occ_date,
                    "details": details,
                    "amount": amount,
                    "source": "PayPayCard"
                })
        return results

    def _parse_aeon(self, file_path):
        results = []
        # Header is usually around line 8, but `csv.DictReader` needs clean start.
        # We'll read lines, find header, then parse.
        with open(file_path, 'r', encoding='shift_jis') as f:
            lines = f.readlines()

        header_index = -1
        for i, line in enumerate(lines):
            if "ご利用日,利用者区分,ご利用先" in line:
                header_index = i
                break

        if header_index == -1:
            logger.error("Could not find Aeon CSV header.")
            return []

        # Parse from header_index
        # Use DictReader on the sliced lines
        from io import StringIO
        csv_content = "".join(lines[header_index:])
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
             if not row.get("ご利用日"): continue

             # Skip header/footer noise lines that might have "ご利用日" as value or similar junk
             raw_date = row["ご利用日"]
             if not raw_date.isdigit():
                 continue

             # Date 251116 -> 2025/11/16
             try:
                 occ_date = datetime.datetime.strptime(raw_date, "%y%m%d").date()
             except ValueError:
                 # logger.warning(f"Invalid date format in Aeon CSV: {raw_date}")
                 # Silently skip noise
                 continue

             amount_str = row.get("ご利用金額", "0").replace(',', '')
             if not amount_str or not amount_str.strip():
                 continue

             try:
                 amount = int(amount_str)
             except ValueError:
                 continue

             if amount == 0: continue

             results.append({
                 "occurrence_date": occ_date,
                 "details": row["ご利用先"],
                 "amount": amount,
                 "source": "AeonCard"
             })
        return results


class ImageParser:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
        else:
            self.model = None

    def parse(self, file_path: str) -> list:
        if not self.model:
            logger.warning("GEMINI_API_KEY missing. Cannot parse images.")
            return []

        logger.info(f"Parsing image with AI: {os.path.basename(file_path)}")

        try:
            # Prepare image
            with open(file_path, "rb") as f:
                image_data = f.read()

            mime_type = "image/jpeg"
            if file_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif file_path.lower().endswith(".webp"):
                mime_type = "image/webp"
            elif file_path.lower().endswith(".heic"):
                mime_type = "image/heic"

            prompt = """
            このレシート/領収書画像から以下の情報を抽出し、JSON形式で出力してください。

            必要な項目:
            - occurrence_date (YYYY-MM-DD形式。日付が不明な場合はnull)
            - amount (税込金額、整数。不明な場合は0)
            - details (店名、購入品目など。簡潔に)
            - account_item (勘定科目。以下から選択: 旅費交通費, 原材料, 消耗品費, 通信費, 会議費。不明な場合は"消耗品費")

            レスポンスはJSONのみとしてください。Markdownコードブロックは不要です。
            例: {"occurrence_date": "2025-10-01", "amount": 1200, "details": "セブンイレブン おにぎり", "account_item": "消耗品費"}
            """

            response = None
            max_retries = 3
            base_wait = 2

            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        [
                            {"mime_type": mime_type, "data": image_data},
                            prompt
                        ]
                    )
                    break
                except Exception as e:
                    if "429" in str(e):
                        wait_time = base_wait * (2 ** attempt)
                        logger.warning(f"AI Rate limit hit (Image). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e

            if not response:
                return []

            text = response.text.strip()
            # Clean up cleanup json markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            # Validation
            occ_date = None
            if data.get("occurrence_date"):
                try:
                    occ_date = datetime.datetime.strptime(data["occurrence_date"], "%Y-%m-%d").date()
                except ValueError:
                    pass

            results = [{
                "occurrence_date": occ_date,
                "details": data.get("details", "Unknown"),
                "amount": int(data.get("amount", 0)),
                "account_item": data.get("account_item", "消耗品費"),
                "source": "ReceiptImage"
            }]
            return results

        except Exception as e:
            logger.error(f"Image parsing failed for {file_path}: {e}")
            return []

def normalize_date(date_str):
    """Ensure date string is YYYY-MM-DD for Freee API"""
    if not date_str: return None
    date_str = date_str.strip()

    formats = ["%Y-%m-%d", "%Y/%m/%d"]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str

def get_month_end(date_obj):
    # Get last day of the month for date_obj
    # Logic: 1st of next month - 1 day
    if not date_obj:
        return datetime.date.today() # Fallback
    next_month = date_obj.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)

def process_extract(args):
    ensure_directory(WORKING_DIR)
    ensure_directory(INPUT_DIR)

    # Sync from Google Drive if configured
    drive_client = None
    if DRIVE_FOLDER_ID:
        drive_client = DriveClient()
        if drive_client.service:
            logger.info("Syncing files from Google Drive...")
            # Find or create 'input' folder in Drive
            drive_files = drive_client.list_files_in_folder(DRIVE_FOLDER_ID)
            input_folder_id = None
            for df in drive_files:
                if df['name'] == 'input' and df['mimeType'] == 'application/vnd.google-apps.folder':
                    input_folder_id = df['id']
                    break

            if not input_folder_id:
                logger.info("Creating 'input' folder in Google Drive...")
                file_metadata = {
                    'name': 'input',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [DRIVE_FOLDER_ID]
                }
                folder = drive_client.service.files().create(body=file_metadata, fields='id').execute()
                input_folder_id = folder.get('id')

            # Download files from 'input' folder
            drive_input_files = drive_client.list_files_in_folder(input_folder_id)
            for dif in drive_input_files:
                if dif['mimeType'] == 'application/vnd.google-apps.folder':
                    continue
                local_path = os.path.join(INPUT_DIR, dif['name'])
                logger.info(f"Downloading {dif['name']} from Drive...")
                drive_client.download_file(dif['id'], local_path)

    # Supported Extensions
    exts = ('.csv', '.jpg', '.jpeg', '.png', '.webp', '.heic')
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(exts)]

    if not files:
        logger.info("No supported files found in input directory.")
        return

    csv_parser = CSVParser()
    image_parser = ImageParser()
    classifier = ExpenseClassifier()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = os.path.join(WORKING_DIR, f"expenses_{timestamp}.csv")

    csv_files = [f for f in files if f.lower().endswith('.csv')]
    image_files = [f for f in files if not f.lower().endswith('.csv')]

    # S38: 抽出した明細を 1 本のリストに集約 → 最後に CSV 化。
    # 大量月でも extract がタイムアウトしないよう、CSV 費目分類はバッチ・画像 OCR は並列。
    parsed_items = []

    # --- CSV 明細: 全ファイルをパース → 費目をまとめてバッチ分類 ---
    for filename in csv_files:
        logger.info(f"Parsing CSV {filename}...")
        parsed_items.extend(csv_parser.parse(os.path.join(INPUT_DIR, filename)))

    to_classify = [it for it in parsed_items if "account_item" not in it]
    if to_classify:
        logger.info(
            f"Batch-classifying {len(to_classify)} CSV rows "
            f"(batch size {CLASSIFY_BATCH_SIZE})..."
        )
        cats = classifier.classify_batch(to_classify)
        for it, cat in zip(to_classify, cats):
            it["account_item"] = cat

    # --- レシート画像: 1 枚 1 リクエスト(バッチ不可)を並列 OCR ---
    #   image_parser.parse は内部で例外を握って [] を返すので、pool でも安全に回せる。
    if image_files:
        logger.info(f"OCR {len(image_files)} images with {IMAGE_OCR_WORKERS} workers...")
        with ThreadPoolExecutor(max_workers=IMAGE_OCR_WORKERS) as pool:
            for parsed in pool.map(
                lambda fn: image_parser.parse(os.path.join(INPUT_DIR, fn)),
                image_files,
            ):
                parsed_items.extend(parsed)

    # --- 抽出結果を最終行に整形 ---
    final_rows = []
    for item in parsed_items:
        occ_date = item["occurrence_date"]
        reg_date_str = ""
        occ_date_str = ""

        if occ_date:
            reg_date = get_month_end(occ_date)
            occ_date_str = occ_date.strftime("%Y-%m-%d")
            reg_date_str = reg_date.strftime("%Y-%m-%d")
        else:
            # 日付不明(画像抽出失敗等)は要確認フラグを付ける
            item["details"] = f"[要確認:日付不明] {item['details']}"

        final_rows.append({
            "occurrence_date": occ_date_str,
            "registration_date": reg_date_str,
            "account_item": item.get("account_item", "消耗品費"),
            "details": item["details"],
            "amount": item["amount"],
            "department": None,  # User to fill
            "description": f"[{item['source']}]",
            "status": "unpaid"
        })

    # Write to CSV
    headers = ["occurrence_date", "registration_date", "account_item", "details", "amount", "department", "description", "status"]

    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(final_rows)

    logger.info(f"Extraction complete. Saved to: {output_csv}")
    print(f"Please review and edit: {output_csv}")

def process_upload(args):
    csv_path = args.file
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return 1

    # ⭐ tax_code 警告: 経費は課税仕入。EXPENSE_TAX_CODE 未設定だと HMC 既定の
    # 1(課税売上 10%)で登録され会計上の誤りになるため、本登録前に強く警告する。
    if EXPENSE_TAX_CODE is None:
        logger.warning(
            "EXPENSE_TAX_CODE が未設定です。経費は本来「課税仕入」ですが、"
            "未設定のままだと Freee 既定の tax_code=1(課税売上 10%)で登録されます。"
            "`python processor.py taxes` で課税仕入のコードを確認し .env に設定してください。"
        )
    else:
        logger.info(f"Using EXPENSE_TAX_CODE={EXPENSE_TAX_CODE} (課税仕入)")

    freee = FreeeClient()

    # Cache account items
    account_items_map = {} # name -> id
    all_items = freee.get_account_items()
    if all_items:
        for item in all_items:
            account_items_map[item['name']] = item['id']

    # Cache sections
    sections_map = {}
    all_sections = freee.get_sections()
    if all_sections:
        for sect in all_sections:
            sections_map[sect['name']] = sect['id']

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or [
            "occurrence_date", "registration_date", "account_item",
            "details", "amount", "department", "description", "status"
        ]

    logger.info(f"Uploading {len(rows)} deals from {csv_path}...")

    failed_rows = []   # list of (row_dict, reason) — 未登録のまま残す対象
    registered = 0

    for i, row in enumerate(rows):
        rownum = i + 1
        # 1 行の異常で全体を止めない(各行を try で包む)
        try:
            acct_name = (row.get("account_item") or "").strip()
            if not acct_name:
                logger.error(f"Row {rownum}: account_item が空。未登録に退避。")
                failed_rows.append((row, "account_item が空"))
                continue

            if acct_name in account_items_map:
                acct_id = account_items_map[acct_name]
            else:
                logger.error(f"Row {rownum}: 勘定科目 '{acct_name}' が Freee に無い。未登録に退避。")
                failed_rows.append((row, f"勘定科目 '{acct_name}' が Freee に無い"))
                continue

            sect_id = None
            dept_name = row.get("department")
            if dept_name and dept_name in sections_map:
                sect_id = sections_map[dept_name]

            desc = f"{row['details']} {row['description']}"
            amount = int(row["amount"])

            occ_date = normalize_date(row["occurrence_date"])
            reg_date = normalize_date(row["registration_date"])

            if args.dry_run:
                logger.info(f"[DRY RUN] Register: Issue={occ_date}, Due={reg_date}, Amt={amount}, Acct={acct_name}, Dept={dept_name}, Tax={EXPENSE_TAX_CODE}, Desc={desc}")
            else:
                resp = freee.post_deal(
                    date=occ_date,
                    amount=amount,
                    description=desc,
                    account_item_id=acct_id,
                    section_id=sect_id,
                    tax_code=EXPENSE_TAX_CODE,   # ⭐ 課税仕入(未設定なら post_deal 側で 1 にフォールバック)
                    type="expense",
                    due_date=reg_date,
                    payments=[] # Explicitly empty for Unpaid (status: unpaid)
                )
                if resp and "deal" in resp:
                    registered += 1
                    logger.info(f"Registered: {desc} ({amount}JPY)")
                else:
                    logger.error(f"Failed to register row {rownum}(直前の API エラー参照)")
                    failed_rows.append((row, "Freee post_deal 失敗(直前の API エラー参照)"))
        except Exception as e:
            logger.error(f"Row {rownum}: 処理中に例外 {type(e).__name__}: {e}。未登録に退避。")
            failed_rows.append((row, f"例外 {type(e).__name__}: {e}"))

    if args.dry_run:
        return len(failed_rows)

    # --- 失敗行を working に退避 + アラーム(exit 非0 + ==NOTIFY== で AI / cron が認識)---
    if failed_rows:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ensure_directory(WORKING_DIR)
        failed_csv = os.path.join(WORKING_DIR, f"FAILED_{ts}.csv")
        with open(failed_csv, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r, _ in failed_rows:
                w.writerow(r)
        detail = "\n".join(
            f"  - {r.get('occurrence_date','?')} {str(r.get('details',''))[:24]} ¥{r.get('amount','?')} → {reason}"
            for r, reason in failed_rows
        )
        # ==NOTIFY== ブロックは send_pending / morning-briefing / Discord ガクコ が拾える共通アラーム形式
        print(
            "\n==NOTIFY==\n"
            f"❌ 経費 upload: {len(rows)}件中 {len(failed_rows)}件 登録失敗(成功 {registered}件)。\n"
            f"未登録分を退避しました(再処理用): {failed_csv}\n"
            f"失敗理由:\n{detail}\n"
            f"→ 修正して再アップ: processor.py upload {failed_csv}\n"
            "==END==\n"
        )
        logger.error(f"UPLOAD PARTIAL FAILURE: {len(failed_rows)}/{len(rows)} 失敗 → 退避 {failed_csv}")

    # --- アーカイブ: 登録成功が 1 件以上の時だけ ---
    # (全滅時は input / 処理 CSV をそのまま残し、再試行できるようにする。
    #  FAILED_*.csv は working/ 直下で、下のアーカイブ対象[input + csv_path]に含まれないため必ず残る)
    if registered == 0:
        logger.error("登録成功 0 件。アーカイブをスキップ(input / CSV を残して再試行可能に)。")
        return len(failed_rows)

    if True:
        # Archive Input Files
        archive_date = datetime.datetime.now().strftime(ARCHIVE_FORMAT)
        archive_path = os.path.join(PROCEEDED_DIR, archive_date)
        ensure_directory(archive_path)

        # Re-list input files to be sure (images + csv)
        exts = ('.csv', '.jpg', '.jpeg', '.png', '.webp', '.heic')
        input_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(exts)]

        # Move Input files
        for f in input_files:
            src = os.path.join(INPUT_DIR, f)
            dst = os.path.join(archive_path, f)
            try:
                os.rename(src, dst)
                logger.info(f"Archived input file: {f}")
            except Exception as e:
                logger.error(f"Failed to archive {f}: {e}")

        # Move Working CSV (Processing file)
        csv_filename = os.path.basename(csv_path)
        dst_csv = os.path.join(archive_path, csv_filename)
        try:
             os.rename(csv_path, dst_csv)
             logger.info(f"Archived working file: {csv_filename}")
        except Exception as e:
             logger.error(f"Failed to archive {csv_filename}: {e}")

        # Archive on Google Drive if configured
        if DRIVE_FOLDER_ID:
            drive_client = DriveClient()
            if drive_client.service:
                logger.info("Archiving files on Google Drive...")
                # Find or create 'processed' folder
                drive_files = drive_client.list_files_in_folder(DRIVE_FOLDER_ID)
                processed_root_id = None
                input_folder_id = None
                for df in drive_files:
                    if df['name'] == 'processed' and df['mimeType'] == 'application/vnd.google-apps.folder':
                        processed_root_id = df['id']
                    if df['name'] == 'input' and df['mimeType'] == 'application/vnd.google-apps.folder':
                        input_folder_id = df['id']

                if not processed_root_id:
                    file_metadata = {
                        'name': 'processed',
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [DRIVE_FOLDER_ID]
                    }
                    folder = drive_client.service.files().create(body=file_metadata, fields='id').execute()
                    processed_root_id = folder.get('id')

                if input_folder_id:
                    # Create date folder inside processed
                    date_folder_id = None
                    date_files = drive_client.list_files_in_folder(processed_root_id)
                    for df in date_files:
                        if df['name'] == archive_date and df['mimeType'] == 'application/vnd.google-apps.folder':
                            date_folder_id = df['id']
                            break

                    if not date_folder_id:
                        file_metadata = {
                            'name': archive_date,
                            'mimeType': 'application/vnd.google-apps.folder',
                            'parents': [processed_root_id]
                        }
                        folder = drive_client.service.files().create(body=file_metadata, fields='id').execute()
                        date_folder_id = folder.get('id')

                    # Move files from input to processed/date
                    drive_input_files = drive_client.list_files_in_folder(input_folder_id)
                    for dif in drive_input_files:
                        if dif['mimeType'] == 'application/vnd.google-apps.folder':
                            continue
                        logger.info(f"Moving Drive file {dif['name']} to processed/{archive_date}...")
                        drive_client.move_file(dif['id'], input_folder_id, date_folder_id)

        if failed_rows:
            logger.warning(f"Completed with failures: 成功 {registered}件 / 失敗 {len(failed_rows)}件(上の ==NOTIFY== 参照)。")
        else:
            logger.info("All operations completed successfully.")

    return len(failed_rows)

def process_to_sheet(args):
    """working CSV → レビュー用 Sheets タブ(S38 案A)。ガクチョが直接編集する面。

    件数が多い月に、Discord チャットの往復ではなく Sheets で一括編集できるようにする。
    タブは `{YYYYMM}`。費目はプルダウン(5分類)、要確認行は黄色。
    """
    from lib import sheets_client
    csv_path = args.file
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return 1
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        logger.info("CSV にデータ行がありません。シートは作りません。")
        print("EMPTY: no rows")
        return 0
    tab = args.tab or datetime.datetime.now().strftime("%Y%m")
    url, gid = sheets_client.write_tab(rows, tab, CATEGORIES)
    logger.info(f"Wrote {len(rows)} rows to review tab {tab}: {url}")
    # 呼び出し側(bot / 種)が拾える機械可読な行
    print(f"REVIEW_SHEET_URL: {url}")
    print(f"REVIEW_TAB: {tab}")
    print(f"REVIEW_ROWS: {len(rows)}")
    return 0


def process_from_sheet(args):
    """レビュー用 Sheets タブ → working CSV に書き戻す(S38 案A)。upload の入力に使う。

    金額が空/0 の行(= ガクチョが削除した行)はスキップ。元の extract CSV は残し、
    レビュー後の新 CSV を別名で出す(取り違え防止)。
    """
    from lib import sheets_client
    tab = args.tab
    rows = sheets_client.read_tab(tab)
    if not rows:
        logger.error(f"タブ {tab} に有効な行がありません(全削除 or タブ無し)。")
        print("EMPTY: no rows after review")
        return 1
    ensure_directory(WORKING_DIR)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(WORKING_DIR, f"expenses_{tab}_reviewed_{ts}.csv")
    headers = sheets_client.CSV_KEYS
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in headers})
    logger.info(f"Read {len(rows)} reviewed rows from tab {tab} → {out}")
    print(f"REVIEWED_CSV: {out}")
    print(f"REVIEWED_ROWS: {len(rows)}")
    return 0


def process_taxes(args):
    """Freee の tax_code 一覧を表示(EXPENSE_TAX_CODE 確定用)。"""
    freee = FreeeClient()
    taxes = freee.get_taxes()
    if not taxes:
        print("税区分が取得できませんでした(認証 or company_id を確認)。")
        return
    print(f"{'code':>6}  name")
    print("-" * 40)
    for t in taxes:
        # taxes API は code / name_ja などを返す
        code = t.get("code", t.get("id", "?"))
        name = t.get("name_ja") or t.get("name") or ""
        print(f"{str(code):>6}  {name}")
    print("\n→ 経費は「課税仕入(課対仕入 10%)」のコードを EXPENSE_TAX_CODE に設定してください。")

def main():
    parser = argparse.ArgumentParser(description="Expense Processor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_extract = subparsers.add_parser("extract")

    p_upload = subparsers.add_parser("upload")
    p_upload.add_argument("file", help="Path to intermediate CSV")
    p_upload.add_argument("--dry-run", action="store_true")

    p_to_sheet = subparsers.add_parser("to-sheet")
    p_to_sheet.add_argument("file", help="Path to intermediate CSV")
    p_to_sheet.add_argument("--tab", default=None, help="Tab name (default: YYYYMM now)")

    p_from_sheet = subparsers.add_parser("from-sheet")
    p_from_sheet.add_argument("tab", help="Tab name (YYYYMM) to read back")
    p_from_sheet.add_argument("--out", default=None, help="Output CSV path")

    p_taxes = subparsers.add_parser("taxes")

    args = parser.parse_args()

    if args.command == "extract":
        process_extract(args)
    elif args.command == "upload":
        n_failed = process_upload(args)
        if n_failed:
            # 失敗ありは exit 1(cron / Discord ガクコ / 呼び出し側 AI が検知できるように)
            sys.exit(1)
    elif args.command == "to-sheet":
        rc = process_to_sheet(args)
        if rc:
            sys.exit(rc)
    elif args.command == "from-sheet":
        rc = process_from_sheet(args)
        if rc:
            sys.exit(rc)
    elif args.command == "taxes":
        process_taxes(args)

if __name__ == "__main__":
    main()
