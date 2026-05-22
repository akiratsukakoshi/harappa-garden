#!/usr/bin/env python3
import os
import sys
import argparse
import json
import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apps.letter_opener.drive_client import DriveClient
from apps.letter_opener.ocr_analyzer import TaskAnalyzer
from modules.utils import setup_logger, ensure_directory
from apps.invoice_processor.utils import is_valid_extension  # Reuse existing utility for images

logger = setup_logger("LetterOpener_Main")

def init_env():
    load_dotenv()
    config = {
        "DRIVE_INBOX_ID": os.getenv("LETTER_DRIVE_INBOX_ID"),
        "DRIVE_PROCESSED_ID": os.getenv("LETTER_DRIVE_PROCESSED_ID"),
        "TEMP_DIR": "data/letter_opener/temp",
        "REVIEW_DIR": "data/letter_opener/review",
        "TASK_FILE": "/home/tukapontas/harappa-cockpit/tasks/letter_tasks.md"
    }
    ensure_directory(config["TEMP_DIR"])
    ensure_directory(config["REVIEW_DIR"])

    if not all([config["DRIVE_INBOX_ID"], config["DRIVE_PROCESSED_ID"]]):
        logger.warning("Drive Folder IDs (LETTER_DRIVE_INBOX_ID, LETTER_DRIVE_PROCESSED_ID) are not set in .env")
        print("Please set LETTER_DRIVE_INBOX_ID and LETTER_DRIVE_PROCESSED_ID in .env before using Drive integration.")
    
    return config

def cmd_extract(args, config):
    """
    Extract data from PDF/Images in Drive Inbox and save to JSON.
    """
    if not config["DRIVE_INBOX_ID"]:
        print("Error: LETTER_DRIVE_INBOX_ID missing.")
        return

    drive = DriveClient()
    if not drive.service:
        logger.error("Failed to initialize Google Drive Client.")
        return

    analyzer = TaskAnalyzer()

    logger.info(f"Checking folder {config['DRIVE_INBOX_ID']}...")
    files = drive.list_files_in_folder(config['DRIVE_INBOX_ID'])
    
    if not files:
        logger.info("No files found in Inbox.")
        print("InBox is empty. No files to process.")
        return

    print(f"Found {len(files)} files.")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"letter_review_{timestamp}.json"
    json_path = os.path.join(config["REVIEW_DIR"], json_filename)
    
    results = []

    for file in files:
        file_id = file['id']
        file_name = file['name']
        
        if not is_valid_extension(file_name):
            logger.info(f"Skipping {file_name} (unsupported extension)")
            continue

        print(f"Processing {file_name}...")
        local_path = os.path.join(config["TEMP_DIR"], file_name)

        if not drive.download_file(file_id, local_path):
            logger.error(f"Failed to download {file_name}.")
            continue

        data = analyzer.analyze(local_path)
        if not data:
            logger.error(f"Failed to analyze {file_name}.")
            if os.path.exists(local_path):
                os.remove(local_path)
            continue
            
        data["file_id"] = file_id
        data["file_name"] = file_name
        
        results.append(data)

        if os.path.exists(local_path):
            os.remove(local_path)

    if results:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nExtraction complete. Saved to: {json_path}")
        print("==== EXTRACTED DATA SUMMARY ====")
        for r in results:
            print(f"- {r.get('task_id')}: [{r.get('task_type')}] {r.get('task_content')} (DUE: {r.get('deadline')}) / Source: {r.get('file_name')}")
        print("================================")
    else:
        print("No valid data extracted.")

def cmd_register(args, config):
    """
    Read reviewed JSON and write to Markdown tasks, then move files.
    """
    json_path = args.file
    if not os.path.exists(json_path):
        logger.error(f"File not found: {json_path}")
        print(f"Error: {json_path} not found.")
        return

    logger.info(f"Reading {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    if not tasks:
        print("No tasks found in JSON.")
        return

    drive = DriveClient()
    processed_files = []
    error_files = []

    # 1. Update Markdown
    task_lines = []
    for t in tasks:
        task_id = t.get("task_id", "LTR-XXXX")
        t_type = t.get("task_type", "手続き")
        content = t.get("task_content", "")
        deadline = t.get("deadline", "未定")
        task_str = f"- [ ] {task_id} [{t_type}] {content} (〆切: {deadline})"
        task_lines.append(task_str)

    try:
        with open(config["TASK_FILE"], 'a', encoding='utf-8') as mf:
            mf.write("\n" + "\n".join(task_lines) + "\n")
        print(f"Successfully appended {len(task_lines)} tasks to {config['TASK_FILE']}")
    except Exception as e:
        logger.error(f"Failed to write to markdown: {e}")
        print(f"Failed to write tasks to file: {e}")
        return

    # 2. Move Files in Drive
    if not args.dry_run:
        print("Moving processed files in Drive...")
        for t in tasks:
            fid = t.get("file_id")
            fname = t.get("file_name")
            if fid:
                try:
                    # Move logic relies on proper parent removal which is handled in drive_client
                    success = drive.move_file(fid, config["DRIVE_INBOX_ID"], config["DRIVE_PROCESSED_ID"])
                    if success:
                        processed_files.append(fname)
                        # Optionally rename file. The current drive_client lacks rename function,
                        # but we can just leave it as is or add update request for name.
                    else:
                        error_files.append(fname)
                except Exception as e:
                    logger.warning(f"Error moving {fname}: {e}")
                    error_files.append(fname)

        if processed_files:
            print(f"Moved {len(processed_files)} files to Processed folder.")
        if error_files:
            print(f"Errors computing {len(error_files)} files: {error_files}")
    else:
        print("[DRY RUN] Would move the following files to Processed Drive:")
        for t in tasks:
            print(f" - {t.get('file_name')} ({t.get('file_id')})")


def main():
    parser = argparse.ArgumentParser(description="Letter Opener CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Extract Command
    parser_extract = subparsers.add_parser("extract", help="Extract data from Inbox to JSON")

    # Register Command
    parser_register = subparsers.add_parser("register", help="Register JSON data to tasks and move Google Drive files")
    parser_register.add_argument("--file", required=True, help="Path to JSON file generated by extract")
    parser_register.add_argument("--dry-run", action="store_true", help="Dry run (no Drive move)")

    args = parser.parse_args()
    config = init_env()

    if args.command == "extract":
        cmd_extract(args, config)
    elif args.command == "register":
        cmd_register(args, config)

if __name__ == "__main__":
    main()
