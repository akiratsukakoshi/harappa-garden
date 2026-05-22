#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
import csv
import datetime
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.invoice_processor.drive_client import DriveClient
from apps.invoice_processor.pdf_analyzer import PDFAnalyzer
from apps.invoice_processor.rule_engine import RuleEngine
from apps.invoice_processor.utils import is_valid_extension
from modules.freee_client import FreeeClient
from modules.utils import setup_logger, ensure_directory

logger = setup_logger("InvoiceProcessor")

def init_env():
    load_dotenv()
    # Configuration
    config = {
        "DRIVE_INBOX_ID": os.getenv("DRIVE_INBOX_ID"),
        "DRIVE_PROCESSED_ID": os.getenv("DRIVE_PROCESSED_ID"),
        "DRIVE_ERROR_ID": os.getenv("DRIVE_ERROR_ID"),
        "TEMP_DIR": "data/invoice_processor/temp",
        "REVIEW_DIR": "data/invoice_processor/review"
    }
    ensure_directory(config["TEMP_DIR"])
    ensure_directory(config["REVIEW_DIR"])

    if not all([config["DRIVE_INBOX_ID"], config["DRIVE_PROCESSED_ID"], config["DRIVE_ERROR_ID"]]):
        logger.error("Drive Folder IDs are not set in .env")
        print("Please set DRIVE_INBOX_ID, DRIVE_PROCESSED_ID, and DRIVE_ERROR_ID in .env")
        sys.exit(1)
    
    return config

def cmd_extract(args, config):
    """
    Extract data from PDF/Images in Drive Inbox and save to CSV.
    """
    drive = DriveClient()
    if not drive.service:
        logger.error("Failed to initialize Google Drive Client.")
        return

    analyzer = PDFAnalyzer()
    freee = FreeeClient() # Needed for rule engine (partner list)
    rule_engine = RuleEngine(freee) 

    logger.info(f"Checking folder {config['DRIVE_INBOX_ID']}...")
    files = drive.list_files_in_folder(config['DRIVE_INBOX_ID'])
    
    if not files:
        logger.info("No files found.")
        return

    logger.info(f"Found {len(files)} files.")
    
    # Prepare CSV output
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"invoice_review_{timestamp}.csv"
    csv_path = os.path.join(config["REVIEW_DIR"], csv_filename)
    
    # Define CSV Headers
    # Define CSV Headers (Reordered per user request)
    # Define CSV Headers (Reordered per user request)
    # Define CSV Headers (Reordered per user request)
    headers = [
        "file_id", "file_name", "date", "payee", "", "partner_code", "partner_id",
        "description", "section_name", "section_id", "account_item_name", "invoice_number",
        "amount", "document_total", "calculated_total", "diff", "warning", "tax_code"
    ]
    
    extracted_data = []

    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        if not is_valid_extension(file_name):
            logger.info(f"Skipping {file_name} (unsupported extension)")
            continue

        logger.info(f"Processing {file_name}...")
        local_path = os.path.join(config["TEMP_DIR"], file_name)

        # Download
        if not drive.download_file(file_id, local_path):
            logger.error("Failed to download file.")
            continue

        # Prepare section candidates for AI
        section_candidates = list(rule_engine.sections.keys())

        # Analyze
        result = analyzer.analyze(local_path, section_candidates=section_candidates)
        if not result:
            logger.error("Failed to analyze file.")
            if os.path.exists(local_path):
                os.remove(local_path)
            continue
            
        # Get items (Multi-row support)
        # result already normalized in analyzer. items should exist.
        items = result.get('items', [])
        
        # Payment Integrity Check
        document_total = result.get("document_total") or 0 # Extracted Gross Total (Truth)
        calculated_total = sum(item.get("amount") or 0 for item in items)
        diff = calculated_total - document_total
        warning_msg = ""
        
        # Compensation Logic (Tax & Rounding)
        if diff != 0:
            logger.info(f"Integrity Mismatch: Doc={document_total}, Calc={calculated_total}, Diff={diff}")
            
            # Scenario 1: All items likely tax-exclusive (Diff ~ -10% of Calc or Doc)
            # Check if calc * 1.1 matches document
            # allow small margin for rounding
            if abs(int(calculated_total * 1.1) - document_total) <= 5: 
                 logger.info("Correction: Items seem to be Tax-Exclusive. Adding 10% tax to all items.")
                 for item in items:
                     item["amount"] = int((item.get("amount") or 0) * 1.1)
                 # Recalculate
                 calculated_total = sum(item["amount"] for item in items)
                 diff = calculated_total - document_total
            
            # Scenario 2: Rounding Error or Slight Mismatch
            # If mismatch is small (e.g. within 5 yen), adjust the largest item
            if abs(diff) <= 5 and items:
                 logger.info(f"Correction: Adjusting rounding error of {diff} JPY.")
                 # Find largest item to absorb diff
                 largest_item = max(items, key=lambda x: x.get("amount") or 0)
                 # If diff is positive (Calc > Doc), we subtract from item. 
                 # If diff is negative (Calc < Doc), we add to item.
                 # Actually, we need to subtract Diff from Calculated to match Doc.
                 # So item should be item - Diff.
                 if "amount" not in largest_item or largest_item["amount"] is None:
                     largest_item["amount"] = 0
                 largest_item["amount"] -= diff
                 
                 # Recalculate
                 calculated_total = sum(item["amount"] for item in items)
                 diff = calculated_total - document_total

            # Scenario 3: Significant Mismatch -> Warning
            if diff != 0:
                 warning_msg = "MISMATCH"
                 logger.warning(f"Final Mismatch: {diff}")
        
        # Override Date if provided
        transaction_date = args.date if args.date else result.get("date")

        # Common Logic per File
        raw_payee = result.get("payee") or ""
        main_desc = result.get("description") or ""
        
        # Construct Full Text for Partner Search
        # payee + main_desc + all item descriptions
        full_text_list = [main_desc]
        for item in items:
            d = item.get("description")
            if d: full_text_list.append(d)
        full_text = " ".join(full_text_list)
        
        # Normalize Payee with Enhanced Matching
        normalized_payee = rule_engine.normalize_payee(raw_payee, extra_text=full_text)
        
        # Resolve Partner
        partner_info = rule_engine.resolve_partner_id(normalized_payee)
        partner_id = partner_info.get("id")
        partner_code = partner_info.get("code")

        # Process each item
        for item in items:
            item_desc = item.get("description") or ""
            item_amount = item.get("amount") or 0
            
            # If item section is null, use top level guess or AI guess
            item_section_name = item.get("section_name")
            
            # Guess Section (Priority: Rule > AI Item > AI Top Level)
            # Combine logic: Check rule for item description first
            section_info = rule_engine.guess_section(item_desc)
            
            if not section_info["section_id"]:
                 # Try AI Item section
                 if item_section_name and item_section_name in rule_engine.sections:
                      section_info["section_name"] = item_section_name
                      section_info["section_id"] = rule_engine.sections[item_section_name]
                 else:
                      # Try Top level AI section (fallback)
                      top_section = result.get("section_name")
                      if top_section and top_section in rule_engine.sections:
                          section_info["section_name"] = top_section
                          section_info["section_id"] = rule_engine.sections[top_section]

            # Infer Category (Account Item)
            # Use normalized payee + item description
            inferred = rule_engine.infer_category(normalized_payee, item_desc)
            
            # Resolve Tax Name for display
            tax_val = inferred.get("tax_code", 189)
            tax_name = rule_engine.get_tax_code_name(tax_val)
            tax_display = f"{tax_val}: {tax_name}"

            # Construct Row
            row = {
                "file_id": file_id,
                "file_name": file_name,
                "date": transaction_date,
                "payee": normalized_payee,
                "": "", # Empty column
                "partner_code": partner_code if partner_code else "",
                "partner_id": partner_id if partner_id else "",
                "description": item_desc,
                "section_name": section_info.get("section_name", ""),
                "section_id": section_info.get("section_id", ""),
                "account_item_name": inferred.get("account_item_name", "外注費"),
                "invoice_number": result.get("invoice_number", ""),
                "amount": item_amount,
                "document_total": document_total,
                "calculated_total": calculated_total,
                "diff": diff,
                "warning": warning_msg,
                "tax_code": tax_display
            }
            extracted_data.append(row)


        # Cleanup temp file
        if os.path.exists(local_path):
            os.remove(local_path)

    # Write CSV
    if extracted_data:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(extracted_data)
        logger.info(f"Extraction complete. Saved to {csv_path}")
        print(f"\nExample CSV saved to: {csv_path}")
        print("Please open this file, review/edit values, then run 'register' command.")
    else:
        logger.info("No data extracted.")


from apps.invoice_processor.fetcher import fetch_invoices, run_gog, LABEL_PROCESSED, LABEL_FETCHED

# ... (Previous imports)

def cmd_fetch(args, config):
    """
    Fetch invoices from Gmail to Drive Inbox.
    """
    fetch_invoices(drive_inbox_id=config["DRIVE_INBOX_ID"], date_from=config.get("FETCH_AFTER"))

# ... (cmd_extract is mostly ok, but we need to preserve metadata if we download/re-upload or if we map file_id)
# Extract generates CSV. CSV has file_id.
# Register reads CSV. Uses file_id to move file.
# We also need file_id to GET file metadata (description) to find thread_id.

def cmd_register(args, config):
    """
    Read CSV and register to Freee.
    """
    csv_path = args.file
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return

    logger.info(f"Reading {csv_path}...")
    
    freee = FreeeClient()
    rule_engine = RuleEngine(freee) # For resolving account IDs
    drive = DriveClient()

    processed_files = set() # Track file_ids to move them later
    error_files = set()
    
    rows_to_process = []
    num_success = 0
    num_error = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows_to_process = list(reader)

    if not rows_to_process:
        logger.info("No rows in CSV.")
        return

    print(f"Found {len(rows_to_process)} rows to register.")
    if args.dry_run:
        print("[DRY RUN] No changes will be made to Freee or Drive.")

    for i, row in enumerate(rows_to_process):
        # ... (Validation logic same as before)
        # Validate required fields
        if not row.get("amount") or not row.get("date") or not row.get("account_item_name"):
            logger.warning(f"Row {i+1}: Missing required fields. Skipping.")
            error_files.add(row.get("file_id"))
            num_error += 1
            continue

        # Resolve IDs
        acct_name = row.get("account_item_name")
        acct_id = rule_engine.resolve_account_item_id(acct_name)
        if not acct_id:
             logger.error(f"Row {i+1}: Invalid Account Item '{acct_name}'. Skipping.")
             error_files.add(row.get("file_id"))
             num_error += 1
             continue
        
        sect_id = row.get("section_id")
        sect_name = row.get("section_name")
        if not sect_id and sect_name in rule_engine.sections:
            sect_id = rule_engine.sections[sect_name]
        
        part_id = row.get("partner_id")
        
        final_desc = row.get("description")
        if not part_id:
            final_desc = f"{row.get('payee')} - {final_desc}"

        # Register
        success = False
        if not args.dry_run:
            start_msg = f"Registering Row {i+1}: {row.get('date')} {row.get('amount')} {acct_name}..."
            print(start_msg, end="")
            
            resp = freee.post_deal(
                date=row.get("date"),
                amount=int(row.get("amount")),
                description=final_desc,
                account_item_id=acct_id,
                section_id=int(sect_id) if sect_id else None,
                partner_id=int(part_id) if part_id else None,
                tax_code=int(row.get("tax_code").split(':')[0]),
                type="expense"
            )
            
            if resp:
                print(" OK")
                processed_files.add(row.get("file_id"))
                success = True
                num_success += 1
            else:
                print(" FAILED")
                error_files.add(row.get("file_id"))
                num_error += 1
        else:
             print(f"[DRY RUN] Would register: {row.get('date')} {row.get('amount')}JPY {acct_name} (Sect:{sect_name})")
             processed_files.add(row.get("file_id")) 
             num_success += 1

        # Finalize Email Status (Only on success and not dry run)
        if success and not args.dry_run:
            fid = row.get("file_id")
            # Get Thread ID from filename (Primary method in current workflow)
            try:
                thread_id = None
                # Check if filename starts with thread_id_ (typically 16 chars hex)
                parts = row.get("file_name", "").split('_', 1)
                if len(parts) > 1 and len(parts[0]) >= 10: # Heuristic for Gmail thread ID
                     thread_id = parts[0]

                if thread_id:
                    print(f"  -> Updating Gmail Thread {thread_id} status...")
                    # Add Processed Label, Remove Fetched Label, Archive
                    run_gog([
                        "gmail", "thread", "modify", thread_id, 
                        "--add", LABEL_PROCESSED, 
                        "--remove", f"INBOX,{LABEL_FETCHED}"
                    ], json_output=False)
            except Exception as e:
                logger.warning(f"Failed to update email status for file {fid}: {e}")


    # Post-processing: Move files
    if not args.dry_run:
        # Move processed
        for fid in processed_files:
            if fid not in error_files: 
                try:
                    drive.move_file(fid, config["DRIVE_INBOX_ID"], config["DRIVE_PROCESSED_ID"])
                except Exception as e:
                    logger.warning(f"Failed to move file {fid}: {e}")

        # Move errors
        for fid in error_files:
             try:
                drive.move_file(fid, config["DRIVE_INBOX_ID"], config["DRIVE_ERROR_ID"])
             except Exception as e:
                logger.warning(f"Failed to move error file {fid}: {e}")

    # Summary and Exit
    print(f"\n--- Registration Summary ---")
    print(f"Total:   {len(rows_to_process)}")
    print(f"Success: {num_success}")
    print(f"Error:   {num_error}")
    
    if num_error > 0:
        logger.error(f"Registration finished with {num_error} errors.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Invoice Processor CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Fetch Command
    parser_fetch = subparsers.add_parser("fetch", help="Fetch invoices from Gmail")
    parser_fetch.add_argument("--after", help="Fetch emails after this date (YYYY/MM/DD or YYYY-MM-DD)")

    # Extract Command
    parser_extract = subparsers.add_parser("extract", help="Extract data from Inbox to CSV")
    parser_extract.add_argument("--date", help="Override transaction date (YYYY-MM-DD)")

    # Register Command
    parser_register = subparsers.add_parser("register", help="Register CSV data to Freee")
    parser_register.add_argument("--file", required=True, help="Path to CSV file")
    parser_register.add_argument("--dry-run", action="store_true", help="Dry run (no registration)")

    args = parser.parse_args()
    config = init_env()

    if args.command == "fetch":
        # Pass the after date if provided
        config["FETCH_AFTER"] = args.after
        cmd_fetch(args, config)
    elif args.command == "extract":
        cmd_extract(args, config)
    elif args.command == "register":
        cmd_register(args, config)

if __name__ == "__main__":
    main()
