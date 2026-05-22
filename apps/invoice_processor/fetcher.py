#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import tempfile
import time
import pty

# --- Configuration ---
GOG_CMD = os.path.expanduser("~/.local/bin/gog")
# Search query: Fetch emails that have attachment and are NOT yet processed or fetched
GMAIL_SEARCH_QUERY = 'has:attachment -label:処理済 -label:Invoice_Fetched'
# Target Google Drive Folder ID (harappa-invoices/inbox)
# NOTE: This should ideally come from main.py config or env, but keeping default here for now.
# We will allow overriding/passing via arguments in future.
DEFAULT_DRIVE_INBOX_ID = os.environ.get("DRIVE_INBOX_ID", "1F-jJ_NfwyyrpARY5ZFerlRuO2GUIQAZe")

# Labels
LABEL_PROCESSED = "処理済"
LABEL_FETCHED = "Invoice_Fetched"
LABEL_PENDING = "Invoice_Pending"

# Account alias used in gogcli
GOG_ACCOUNT = "me"

# --- Filtering Rules ---
FILTER_SUBJECT_KEYWORDS = ["請求書", "invoice", "領収書", "利用明細", "bill", "payment", "精算", "費用"]
FILTER_SENDERS = [] 
FILTER_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".zip", ".lzh"]

KEYRING_PASSWORD = os.environ.get("GOG_KEYRING_PASSWORD")

def run_gog(args, json_output=True):
    """Runs a gog command using PTY to handle password prompt, and returns the output."""
    if not KEYRING_PASSWORD:
        print("Error: GOG_KEYRING_PASSWORD environment variable is not set.")
        sys.exit(1)

    cmd = [GOG_CMD] + args + ["--account", GOG_ACCOUNT]
    if json_output:
        cmd.append("--json")
    
    try:
        master, slave = pty.openpty()
        process = subprocess.Popen(
            cmd, 
            stdin=slave, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        os.close(slave)
        os.write(master, (KEYRING_PASSWORD + "\n").encode())
        stdout, stderr = process.communicate()
        os.close(master)
        
        if process.returncode != 0:
            print(f"Command failed: {cmd}")
            print(f"Stderr: {stderr}")
            return None 

        result_stdout = stdout.strip()

        if json_output:
            json_start = result_stdout.find('{')
            json_list_start = result_stdout.find('[')
            start_index = -1
            if json_start != -1 and json_list_start != -1:
                start_index = min(json_start, json_list_start)
            elif json_start != -1:
                start_index = json_start
            elif json_list_start != -1:
                start_index = json_list_start
            
            if start_index != -1:
                json_str = result_stdout[start_index:]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            return json.loads(result_stdout) if result_stdout else None
            
        return result_stdout
    except Exception as e:
        print(f"Error running gog: {e}")
        return None

def is_target_email(msg_details, pending_lbl_id=None):
    payload = msg_details.get('payload', {})
    headers = payload.get('headers', [])
    label_ids = msg_details.get('labelIds', [])
    
    subject = ""
    sender = ""
    date = ""
    for h in headers:
        if h.get('name') == 'Subject': subject = h.get('value', '')
        if h.get('name') == 'From': sender = h.get('value', '')
        if h.get('name') == 'Date': date = h.get('value', '')
            
    print(f"  Confirming Email - Subject: {subject}, From: {sender}")

    # Return metadata along with result if True? 
    # Or just modify fetcher to extract these again. 
    # Let's simple return True/False here and extract in loop.
    
    # ... logic ...
    # 1. Check if manually tagged as Invoice_Pending
    if pending_lbl_id and pending_lbl_id in label_ids:
        print(f"    -> MATCH: Found '{LABEL_PENDING}' label. Skipping keyword check.")
        return True

    # 2. Keyword Check
    if FILTER_SUBJECT_KEYWORDS:
        if not any(k.lower() in subject.lower() for k in FILTER_SUBJECT_KEYWORDS):
            print(f"    -> SKIPPED: Subject mismatch.")
            return False

    return True

def get_label_id(name):
    """Fetches key-value map of {name: id} or returns specific id."""
    labels_resp = run_gog(["gmail", "labels", "list"])
    if not labels_resp: return None
    
    labels = labels_resp
    if isinstance(labels_resp, dict) and 'labels' in labels_resp:
        labels = labels_resp['labels']
        
    # labels is typically list of {id, name, ...}
    for l in labels:
        if isinstance(l, dict) and l.get('name', '').lower() == name.lower():
            return l.get('id')
    return None

def fetch_invoices(drive_inbox_id=None, date_from=None):
    if not drive_inbox_id:
        drive_inbox_id = DEFAULT_DRIVE_INBOX_ID

    print("--- Starting Invoice Fetch ---")
    
    # Resolve Pending Label ID
    pending_lbl_id = get_label_id(LABEL_PENDING)
    print(f"Label '{LABEL_PENDING}' ID: {pending_lbl_id}")

    query = GMAIL_SEARCH_QUERY
    if date_from:
        # Normalize date separators if needed, but Gmail supports / and - usually.
        # Just ensure it's not empty
        query += f" after:{date_from}"

    print(f"Searching: {query}")
    
    response = run_gog(["gmail", "search", query, "--max", "30"])
    if not response:
        print("No matching emails found (or error).")
        return

    uploaded_files = [] # Track uploaded files for summary

    thread_list = []
    if isinstance(response, dict):
        thread_list = response.get('threads', [])
    elif isinstance(response, list):
        thread_list = response

    if not thread_list:
        print("No threads found.")
        return

    print(f"Found {len(thread_list)} threads.")

    for thread_summary in thread_list:
        thread_id = thread_summary.get('id')
        print(f"\nProcessing Thread ID: {thread_id}")

        try:
            thread_details = run_gog(["gmail", "thread", "get", thread_id])
            if not thread_details or isinstance(thread_details, str):
                continue
            
            messages = thread_details.get('thread', {}).get('messages', [])
            if not messages: messages = thread_details.get('messages', [])

            for msg_details in messages:
                msg_id = msg_details.get('id')
                
                if not is_target_email(msg_details, pending_lbl_id):
                    continue

                attachments = []
                def find_attachments(parts):
                    for part in parts:
                        filename = part.get('filename')
                        if filename and part.get('body', {}).get('attachmentId'):
                            if FILTER_EXTENSIONS:
                                _, ext = os.path.splitext(filename)
                                if ext.lower() not in FILTER_EXTENSIONS:
                                    continue
                            attachments.append({
                                'filename': filename,
                                'attachmentId': part.get('body').get('attachmentId')
                            })
                        if part.get('parts'):
                            find_attachments(part.get('parts'))

                payload = msg_details.get('payload', {})
                if payload.get('parts'):
                    find_attachments(payload.get('parts'))
                
                if not attachments:
                    continue

                for att in attachments:
                    filename = att['filename']
                    att_id = att['attachmentId']
                    print(f"  - Found attachment: {filename}")

                    with tempfile.TemporaryDirectory() as temp_dir:
                        local_path = os.path.join(temp_dir, filename)
                        
                        # Download
                        run_gog(["gmail", "attachment", msg_id, att_id, "--out", local_path], json_output=False)

                        # Metadata JSON
                        metadata = {
                            "thread_id": thread_id,
                            "message_id": msg_id,
                            "original_filename": filename,
                            "fetched_at": time.time()
                        }
                        metadata_str = json.dumps(metadata)

                        # New strategy: Prepend thread_id to filename
                        # This avoids description limitation and auth issue
                        # Format: [thread_id]_original_filename.ext
                        # But note: thread_id is alphanumeric. Could contain unsafe chars? Usually base16/base64.
                        # Gmail thread IDs are hex string? e.g. 18df..., safe.
                        
                        new_filename = f"{thread_id}_{filename}"
                        
                        # Upload without description, using gog (user auth)
                        print(f"    Uploading to Drive as {new_filename}...")
                        run_gog([
                            "drive", "upload", local_path, 
                            "--name", new_filename,
                            "--parent", drive_inbox_id
                        ], json_output=False) 
                        print("    Upload success.")
                        
                        # Add to summary
                        # We need to get date/sender/subject here. 
                        # They are in msg_details payload headers.
                        p_headers = msg_details.get('payload', {}).get('headers', [])
                        f_date = ""
                        f_sender = ""
                        f_subject = ""
                        for h in p_headers:
                            if h.get('name') == 'Date': f_date = h.get('value', '')
                            if h.get('name') == 'From': f_sender = h.get('value', '')
                            if h.get('name') == 'Subject': f_subject = h.get('value', '')

                        uploaded_files.append({
                            "date": f_date, 
                            "sender": f_sender, 
                            "subject": f_subject,
                            "filename": filename
                        })


                # Mark Thread as Fetched (Intermediate State)
                # Ensure label exists first? gog usually creates it.
                print(f"  Applying label '{LABEL_FETCHED}'...")
                
                # Also remove Pending label if it exists
                run_gog(["gmail", "thread", "modify", thread_id, 
                         "--add", LABEL_FETCHED,
                         "--remove", LABEL_PENDING
                        ], json_output=False)
                
        except Exception as e:
            print(f"  Error processing thread {thread_id}: {e}")
            continue


    print("\n--- Fetch Complete ---")
    
    if uploaded_files:
        print("\n[Summary of Uploaded Files]")
        print(f"{'Date':<20} | {'Sender':<30} | {'Subject'}")
        print("-" * 100)
        for f in uploaded_files:
            # Truncate if too long
            sender = (f['sender'][:27] + '...') if len(f['sender']) > 30 else f['sender']
            subject = (f['subject'][:45] + '...') if len(f['subject']) > 48 else f['subject']
            print(f"{f['date']:<20} | {sender:<30} | {subject}")
    else:
        print("No new files uploaded.")

if __name__ == "__main__":
    fetch_invoices()
