import os
import sys
import json
import subprocess
import datetime
import re
from typing import List, Dict, Any

# Adjust path to find modules if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# Configuration Paths
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../../data/email_organizer/config.json')
MAIL_TASK_PATH = os.path.join(os.path.dirname(__file__), '../../tasks/mail_task.md')
GOG_CMD = os.path.expanduser("~/.local/bin/gog")

# Load Configuration
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"archive_rules": {"senders": [], "subjects": []}, "ignore_rules": {"senders": []}, "task_rules": {}}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# gogcli Wrapper
def run_gog(args, json_output=True):
    env = os.environ.copy()
    if "GOG_KEYRING_PASSWORD" not in env:
        # Fallback or error warning
        pass

    cmd = [GOG_CMD] + args
    if json_output:
        cmd.append("--json")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
        if json_output:
            return json.loads(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running gog: {e}")
        print(f"Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError:
        return None

# LLM Analysis
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from dotenv import load_dotenv
    # Load .env from project root
    load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
except ImportError:
    pass

def init_genai():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True

def analyze_email_with_llm(email_data):
    if not HAS_GENAI or not init_genai():
        return None

    model = genai.GenerativeModel("gemini-1.5-flash")
    
    subject = email_data.get('subject', '')
    sender = email_data.get('from', '')
    snippet = email_data.get('snippet', '')
    body_preview = snippet # In a real implementation, we'd fetch the full body. For now, snippet is okay-ish.

    prompt = f"""
    Analyze the following email metadata and extract task information.
    
    Email:
    From: {sender}
    Subject: {subject}
    Snippet: {body_preview}

    Task:
    1. Determine if this email requires a reply ("reply") or just checking/review ("check"). If neither (e.g. newsletter), return "ignore".
    2. Summarize the task in Japanese (max 40 chars).
    3. Suggest a deadline (YYYY-MM-DD) based on content. If none, return null.

    Output JSON format:
    {{
        "action": "reply" | "check" | "ignore",
        "summary": "...",
        "deadline": "YYYY-MM-DD" | null
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        print(f"GenAI Error: {e}")
        return None

def analyze_email_content(email_data):
    """
    Returns dict: {
        "category": "task" | "newsletter" | "other",
        "action": "reply" | "check" | "archive" | None,
        "summary": str,
        "deadline": str (YYYY-MM-DD or None)
    }
    """
    # 1. Try LLM
    llm_result = analyze_email_with_llm(email_data)
    if llm_result:
        action = llm_result.get("action")
        if action in ["reply", "check"]:
            return {
                "category": "task",
                "action": action,
                "summary": llm_result.get("summary", email_data.get('subject')),
                "deadline": llm_result.get("deadline")
            }
        elif action == "ignore":
             return { # Treat as uncertain/other if LLM says ignore, but let heuristic double check or just return other
                "category": "other",
                "action": None,
                "summary": email_data.get('subject'),
                "deadline": None
            }

    # 2. Heuristics fallback
    subject = email_data.get('subject', '')
    snippet = email_data.get('snippet', '')
    
    is_reply = any(k in subject or k in snippet for k in ["返信", "回答", "連絡", "reply"])
    is_check = any(k in subject or k in snippet for k in ["確認", "check", "review"])
    
    category = "other"
    action = None
    
    if is_reply:
        category = "task"
        action = "reply"
    elif is_check:
        category = "task"
        action = "check"
    
    return {
        "category": category,
        "action": action,
        "summary": subject,
        "deadline": None
    }

def main():

    print("Email Organizer v2 - Scanning Inbox...")
    config = load_config()
    
    # 1. Fetch Unread (Threads)
    # Note: 'gog gmail search' returns a list of thread objects usually, 
    # but let's verify if it returns a list of IDs or objects.
    # Previous experience: it returned threads list inside a wrapper or direct list?
    # Let's inspect raw output.
    threads = run_gog(["gmail", "search", "label:UNREAD label:INBOX", "--max", "30"])
    
    if not threads:
        print("No unread emails found.")
        return

    # DEBUG: Print type and first element
    # print(f"DEBUG: threads type: {type(threads)}")
    # if isinstance(threads, list) and len(threads) > 0:
    #     print(f"DEBUG: first element: {threads[0]}")
    if isinstance(threads, dict):
        # print(f"DEBUG: dict keys: {threads.keys()}")
        # If it returns {'threads': [...]}, we need to extract it.
        if 'threads' in threads:
            threads = threads['threads']
        else:
            # Maybe resultSizeEstimate only? No threads?
            threads = []

    if not isinstance(threads, list):
        print(f"Unexpected threads format: {type(threads)}")
        return

    plan = {
        "auto_archive": [],
        "propose_archive": [],
        "propose_task": [],
        "mark_invoice": [],
        "unknown": []
    }

    archive_senders = config['archive_rules'].get('senders', [])
    archive_subjects = config['archive_rules'].get('subjects', [])
    ignore_senders = config.get('ignore_rules', {}).get('senders', [])

    for thread in threads:
        thread_id = thread['id']
        subject = thread.get('subject', '(No Subject)')
        sender = thread.get('from', '(Unknown)')
        snippet = thread.get('snippet', '')

        # Ignore Check
        is_ignored = False
        for k in ignore_senders:
            if k.lower() in sender.lower():
                is_ignored = True
                break
        
        if is_ignored:
            # Treat as task candidate (try to analyze) or unknown, but NEVER auto-archive
            # For now, let's fall through to analysis
            pass
        else:
            # Auto Archive Check
            is_auto_archive = False
            # Check Sender
            for k in archive_senders:
                if k.lower() in sender.lower():
                    is_auto_archive = True
                    break
            # Check Subject
            if not is_auto_archive:
                for k in archive_subjects:
                    if k in subject:
                        is_auto_archive = True
                        break
            
            if is_auto_archive:
                plan["auto_archive"].append(thread)
                continue

        # Analysis
        analysis = analyze_email_content(thread)
        if analysis["category"] == "task":
            plan["propose_task"].append({"thread": thread, "analysis": analysis})
        elif analysis["category"] == "newsletter": # If LLM identified it
            plan["propose_archive"].append(thread)
        else:
            # Fallback: treat as potential archive if it looks like one, else unknown
            # For now, put everything else in unknown/review
            plan["unknown"].append(thread)

    # 3. Present Plan
    print("\n=== [1] Auto-Archive Candidates (Based on Config) ===")
    for item in plan["auto_archive"]:
        print(f"[ARCHIVE] {item['subject']} ({item['from']})")

    print("\n=== [2] Task Candidates (Action Required) ===")
    for item in plan["propose_task"]:
        act = item['analysis']['action']
        label = "要返信" if act == "reply" else "要確認"
        print(f"[TASK:{label}] {item['thread']['subject']} ({item['thread']['from']})")

    print("\n=== [3] Review / Uncertain ===")
    for item in plan["unknown"]:
        print(f"[?] {item['subject']} ({item['from']})")
        print(f"    Snippet: {item.get('snippet', '')[:50]}...")

    # 4. Interaction
    print("\nCommands:")
    print("  y: Execute Plan (Archive [1], Create Tasks for [2], Skip [3])")
    print("  i: Interactive Mode (Review [3] to add to archive rules or tasks)")
    print("  v: View [v] Invoice Pending items") # Just helper, main action is inside 'i'
    print("  q: Quit")
    print("  q: Quit")
    
    choice = input("\nEnter choice [y/i/q]: ").strip().lower()

    if choice == 'q':
        return

    if choice == 'i':
        # Interactive Review of Unknowns
        new_archive_senders = []
        print("\n--- Reviewing Unknown Items (Enter 'q' to stop review) ---")
        
        for item in plan["unknown"]:
            print(f"\nSubject: {item['subject']}")
            print(f"From: {item['from']}")
            print(f"Snippet: {item.get('snippet', '')}")
            act = input("Action? (a: Archive / t: Task / v: Invoice / s: Skip / q: Quit) [s]: ").strip().lower()
            
            if act == 'q':
                break

            if act == 'a':
                # Add to auto_archive list and learn sender
                plan["auto_archive"].append(item)
                
                sender_email_match = re.search(r'<(.+?)>', item['from'])
                if sender_email_match:
                    keyword = sender_email_match.group(1)
                else:
                    keyword = item['from']
                
                print(f"  -> Planning to learn rule: Sender contains '{keyword}'")
                new_archive_senders.append(keyword)
                
            elif act == 't':
                # Add to task list
                # Infer type
                t_type = input("  Type? (r: Reply / c: Check) [c]: ").strip().lower()
                action = "reply" if t_type == 'r' else "check"
                
                # Ask/Verify Deadline
                user_dl = input("  Deadline (YYYY-MM-DD)? [Enter for None]: ").strip()
                deadline = user_dl if user_dl else None

                plan["propose_task"].append({
                    "thread": item, 
                    "analysis": {"action": action, "summary": item['subject'], "deadline": deadline}
                })

            elif act == 'v':
                # Mark as Invoice Pending
                print(f"  -> Marked as Invoice Pending (for Invoice Processor)")
                plan["mark_invoice"].append(item)

        # Update Config
        if new_archive_senders:
            print(f"Updating config with {len(new_archive_senders)} new rules...")
            config['archive_rules']['senders'].extend(new_archive_senders)
            # Deduplicate
            config['archive_rules']['senders'] = list(set(config['archive_rules']['senders']))
            save_config(config)

    # 5. Execution
    print("\nExecuting...")
    
    # Archiving
    for item in plan["auto_archive"]:
        print(f"Archiving: {item['subject']}")
        # Thread modify: remove INBOX
        run_gog(["gmail", "thread", "modify", item['id'], "--remove", "INBOX"], json_output=False)

    # Invoice Pending
    for item in plan["mark_invoice"]:
        print(f"Marking as Invoice: {item['subject']}")
        # Add Invoice_Pending, Remove INBOX
        run_gog(["gmail", "thread", "modify", item['id'], "--add", "Invoice_Pending", "--remove", "INBOX"], json_output=False)

    # Task Creation
    new_tasks = []
    today_str = datetime.date.today().isoformat()
    
    for item in plan["propose_task"]:
        thread = item['thread']
        analysis = item['analysis']
        
        # Labeling
        label_map = {"reply": "要返信", "check": "要確認"}
        label_text = label_map.get(analysis['action'], "要確認")
        
        # Add Label to Gmail (Create if not exists? gog might fail. Assume user labels exist or just skip failing)
        # run_gog(["gmail", "labels", "add", thread['id'], label_text], json_output=False) 
        # (Skipping API label add for now to avoid errors if label missing, focusing on MD)

        # Markdown Entry
        # - [ ] [期限: YYYY-MM-DD] [LABEL] Subject (From: Sender)
        deadline_str = analysis['deadline'] if analysis['deadline'] else "未定"
        task_line = f"- [ ] [期限: {deadline_str}] [{label_text}] {thread['subject']} (From: {thread['from']})"
        new_tasks.append(task_line)

    if new_tasks:
        print(f"Appending {len(new_tasks)} tasks to {MAIL_TASK_PATH}...")
        with open(MAIL_TASK_PATH, 'a', encoding='utf-8') as f:
            for line in new_tasks:
                f.write(line + "\n")
    
    print("Done.")

if __name__ == "__main__":
    main()
