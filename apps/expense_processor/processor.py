#!/usr/bin/env python3
import os
import sys
import argparse
import csv
import datetime
import json
import logging
import google.generativeai as genai
import time
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.freee_client import FreeeClient
from modules.utils import setup_logger, ensure_directory
from apps.invoice_processor.drive_client import DriveClient

logger = setup_logger("ExpenseProcessor")

load_dotenv()

# Configuration
INPUT_DIR = "data/expense_processor/input"
WORKING_DIR = "data/expense_processor/working"
PROCEEDED_DIR = "data/expense_processor/proceeded"
ARCHIVE_FORMAT = "%Y%m%d"

# Drive Configuration
DRIVE_FOLDER_ID = os.getenv("EXPENSE_DRIVE_FOLDER_ID")

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
            self.model = genai.GenerativeModel('gemini-2.0-flash')

    import time
    
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
            self.model = genai.GenerativeModel('gemini-2.0-flash')
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
    
    # Already correct?
    # Simple check, or let strptime validate
    
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
    
    final_rows = []
    
    for filename in files:
        filepath = os.path.join(INPUT_DIR, filename)
        logger.info(f"Processing {filename}...")
        
        # Rate limit protection
        time.sleep(2)
        
        parsed_data = []
        if filename.lower().endswith('.csv'):
            parsed_data = csv_parser.parse(filepath)
            # For CSV, we usually don't get account_item from parser (unless specific logic inside parser?)
            # CSVParser returns details/amount/date.
            # We need to classify them.
            for item in parsed_data:
                # AI Classification for CSV items
                # Check if 'account_item' is already in item (unlikely for CSV parser result)
                 if "account_item" not in item:
                     item["account_item"] = classifier.classify(item["details"], item["amount"])

        else:
            # Image
            parsed_data = image_parser.parse(filepath)
            # Image parser already returns account_item from AI.
        
        for item in parsed_data:
            occ_date = item["occurrence_date"]
            # reg_date logic
            reg_date_str = ""
            occ_date_str = ""
            
            if occ_date:
                reg_date = get_month_end(occ_date)
                occ_date_str = occ_date.strftime("%Y-%m-%d")
                reg_date_str = reg_date.strftime("%Y-%m-%d")
            else:
                # Handle missing date (e.g. image parse fail)
                # Mark as review needed
                item["details"] = f"[要確認:日付不明] {item['details']}"
            
            final_rows.append({
                "occurrence_date": occ_date_str,
                "registration_date": reg_date_str,
                "account_item": item.get("account_item", "消耗品費"),
                "details": item["details"],
                "amount": item["amount"],
                "department": None, # User to fill
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
        return

    freee = FreeeClient()
    
    # Cache account items
    account_items_map = {} # name -> id
    # We only need the 5 categories? No, we should fetch all and match by name.
    # Actually FreeeClient has get_account_items(name_hook).
    # But for bulk processing, better to fetch all once.
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

    logger.info(f"Uploading {len(rows)} deals from {csv_path}...")

    # For archiving: get original filenames if possible?

    for i, row in enumerate(rows):
        if not row.get("account_item"):
            logger.warning(f"Row {i+1}: Missing account_item. Skipping.")
            continue
            
        acct_name = row["account_item"]
        acct_id = None
        # Try exact match first
        if acct_name in account_items_map:
             acct_id = account_items_map[acct_name]
        else:
             # Fallback: fuzzy search or log error
             logger.error(f"Row {i+1}: Account Item '{acct_name}' not found.")
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
            logger.info(f"[DRY RUN] Register: Issue={occ_date}, Due={reg_date}, Amt={amount}, Acct={acct_name}, Dept={dept_name}, Desc={desc}")
        else:
            resp = freee.post_deal(
                date=occ_date,
                amount=amount,
                description=desc,
                account_item_id=acct_id,
                section_id=sect_id,
                type="expense",
                due_date=reg_date,
                payments=[] # Explicitly empty for Unpaid (status: unpaid)
            )
            if resp and "deal" in resp:
                logger.info(f"Registered: {desc} ({amount}JPY)")
            else:
                logger.error(f"Failed to register row {i+1}")
                
    if not args.dry_run:
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
                    # We only want to move files that were just processed locally
                    # For simplicity, we move EVERYTHING in the input folder to processed/date
                    # as process_extract downloads everything and process_upload archives everything locally.
                    for dif in drive_input_files:
                        if dif['mimeType'] == 'application/vnd.google-apps.folder':
                            continue
                        logger.info(f"Moving Drive file {dif['name']} to processed/{archive_date}...")
                        drive_client.move_file(dif['id'], input_folder_id, date_folder_id)

        logger.info("All operations completed successfully.")

def main():
    parser = argparse.ArgumentParser(description="Expense Processor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    p_extract = subparsers.add_parser("extract")
    
    p_upload = subparsers.add_parser("upload")
    p_upload.add_argument("file", help="Path to intermediate CSV")
    p_upload.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    if args.command == "extract":
        process_extract(args)
    elif args.command == "upload":
        process_upload(args)

if __name__ == "__main__":
    main()
