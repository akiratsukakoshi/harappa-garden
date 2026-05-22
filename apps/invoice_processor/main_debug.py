# Debug copy
import sys
import shutil
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.invoice_processor.drive_client import DriveClient
from apps.invoice_processor.pdf_analyzer import PDFAnalyzer
from apps.invoice_processor.rule_engine import RuleEngine
from apps.invoice_processor.utils import is_valid_extension
from modules.freee_client import FreeeClient
from modules.utils import setup_logger, ensure_directory

def main():
    load_dotenv()
    logger = setup_logger("InvoiceProcessor")
    
    # 1. Configuration
    DRIVE_INBOX_ID = os.getenv("DRIVE_INBOX_ID")
    DRIVE_PROCESSED_ID = os.getenv("DRIVE_PROCESSED_ID")
    DRIVE_ERROR_ID = os.getenv("DRIVE_ERROR_ID")
    TEMP_DIR = "data/invoice_processor/temp"
    ensure_directory(TEMP_DIR)

    if not all([DRIVE_INBOX_ID, DRIVE_PROCESSED_ID, DRIVE_ERROR_ID]):
        logger.error("Drive Folder IDs are not set in .env")
        print("Please set DRIVE_INBOX_ID, DRIVE_PROCESSED_ID, and DRIVE_ERROR_ID in .env")
        return

    # 2. Initialize Clients
    drive = DriveClient()
    if not drive.service:
        logger.error("Failed to initialize Google Drive Client.")
        return

    analyzer = PDFAnalyzer()
    freee = FreeeClient()
    rule_engine = RuleEngine(freee)

    # 3. Main Loop
    logger.info(f"Checking folder {DRIVE_INBOX_ID}...")
    files = drive.list_files_in_folder(DRIVE_INBOX_ID)
    
    if not files:
        logger.info("No files found.")
        return

    logger.info(f"Found {len(files)} files.")

    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        if not is_valid_extension(file_name):
            logger.info(f"Skipping {file_name} (unsupported extension)")
            continue

        logger.info(f"Processing {file_name}...")
        local_path = os.path.join(TEMP_DIR, file_name)

        # Download
        if not drive.download_file(file_id, local_path):
            logger.error("Failed to download file.")
            continue

        # Analyze
        result = analyzer.analyze(local_path)
        if not result or "amount" not in result:
            logger.error("Failed to analyze file or extract data.")
            # Move to error? Or just skip? Let's ask user or move to error.
            # For now, move to error.
            drive.move_file(file_id, DRIVE_INBOX_ID, DRIVE_ERROR_ID)
            continue

        # Rule Engine
        inferred = rule_engine.infer_category(result.get("payee"))
        
        # Merge inferred data
        result.update(inferred)

        # User Confirmation
        print("\n" + "="*30)
        print(f"File: {file_name}")
        print(f"Date: {result.get('date')}")
        print(f"Payee: {result.get('payee')}")
        print(f"Amount: {result.get('amount')}")
        print(f"Desc: {result.get('description')}")
        print(f"Acct: {result.get('account_item_name')}")
        print(f"Reg#: {result.get('invoice_number')}")
        print("="*30)
        
        choice = input("Register this deal? [y/n/edit]: ").strip().lower()
        
        if choice == 'edit':
             # Simple edit flow
             result['date'] = input(f"Date [{result.get('date')}]: ") or result.get('date')
             result['payee'] = input(f"Payee [{result.get('payee')}]: ") or result.get('payee')
             result['amount'] = input(f"Amount [{result.get('amount')}]: ") or result.get('amount')
             # Re-infer category if payee changed? Maybe later.
             result['account_item_name'] = input(f"Account [{result.get('account_item_name')}]: ") or result.get('account_item_name')
             choice = 'y'

        if choice == 'y':
            # Register to Freee
            # Need to resolve account_item_id which might still be just a name
            acct_name = result.get('account_item_name')
            acct_id = rule_engine.resolve_account_item_id(acct_name)
            
            if not acct_id:
                logger.error(f"Could not resolve Account Item ID for {acct_name}")
                # Fallback to defaults or fail?
                # For MVP, fail.
                drive.move_file(file_id, DRIVE_INBOX_ID, DRIVE_ERROR_ID)
                continue

            resp = freee.post_deal(
                date=result.get('date'),
                amount=result.get('amount'),
                description=f"{result.get('payee')} - {result.get('description')}",
                account_item_id=acct_id,
                type="expense"
            )
            
            if resp:
                logger.info("Registered successfully.")
                drive.move_file(file_id, DRIVE_INBOX_ID, DRIVE_PROCESSED_ID)
            else:
                logger.error("Failed to register to Freee.")
                drive.move_file(file_id, DRIVE_INBOX_ID, DRIVE_ERROR_ID)
                
        else:
            logger.info("Skipped by user.")
            # Do not move, keep in inbox? Or move to error?
            # Keeping in inbox is safer for "skip".

        # Cleanup temp file
        if os.path.exists(local_path):
            os.remove(local_path)

if __name__ == "__main__":
    main()
