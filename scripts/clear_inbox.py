import os
from dotenv import load_dotenv
from apps.invoice_processor.drive_client import DriveClient

def main():
    load_dotenv()
    inbox_id = os.getenv("DRIVE_INBOX_ID")
    processed_id = os.getenv("DRIVE_PROCESSED_ID")
    
    if not inbox_id or not processed_id:
        print("Error: DRIVE_INBOX_ID or DRIVE_PROCESSED_ID not found in .env")
        return

    client = DriveClient()
    files = client.list_files_in_folder(inbox_id)
    
    if not files:
        print("No files found in Inbox.")
        return
        
    print(f"Moving {len(files)} files from Inbox to Processed...")
    for f in files:
        print(f"Moving {f['name']} ({f['id']})...")
        success = client.move_file(f['id'], inbox_id, processed_id)
        if success:
            print("Success")
        else:
            print("Failed")

if __name__ == "__main__":
    main()
