import sys
import os
import glob
from modules.utils import setup_logger

logger = setup_logger("MainMenu")

def show_menu():
    print("\n=== HARAPPA Management Cockpit ===")
    print("1. [Step 1] Generate Review File (CSVから確認用ファイルを作成)")
    print("2. [Step 2] Upload from Review File (確認用ファイルをFreeeへ送信)")
    print("q. Quit")
    print("==================================")

def run_generate():
    print("\n[Step 1: Generate Review File]")
    print("Select Source Type:")
    print("1. STORES")
    print("2. Square")
    choice = input("Choice: ").strip()
    
    ftype = ""
    if choice == "1":
        ftype = "stores"
    elif choice == "2":
        ftype = "square"
    else:
        print("Invalid choice.")
        return

    path = input("Enter full path to Source CSV file: ").strip()
    if not os.path.exists(path):
        print("File not found.")
        return

    # Dry run has no meaning for generate step really (it just generates file), 
    # but we pass generate mode.
    # Note: import_sales.py arguments: <file_path> <config_type> <mode> [--dry-run]
    
    cmd = f"{sys.executable} apps/finance_importer/import_sales.py \"{path}\" {ftype} generate"
    os.system(cmd)

def run_upload():
    print("\n[Step 2: Upload from Review File]")
    
    # List available review files
    # Path: data/finance_importer/review/
    search_path = "data/finance_importer/review/*.csv"
    files = sorted(glob.glob(search_path), reverse=True)
    if not files:
        print(f"No review files found in {os.path.dirname(search_path)}")
        return
        
    print("Select file to upload:")
    for i, f in enumerate(files):
        print(f"{i+1}. {os.path.basename(f)}")
    
    choice = input("Choice (default 1): ").strip()
    if not choice:
        choice = "1"
        
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(files):
            print("Invalid index.")
            return
        target_file = files[idx]
    except ValueError:
        print("Invalid input.")
        return

    # Confirm
    print(f"Target: {target_file}")
    print("Select Mode:")
    print("y: Execute Upload (本番登録)")
    print("n: Dry Run (テスト実行 - ログのみ)")
    choice = input("Choice (y/n): ").strip().lower()
    
    is_dry = True # Default to safe
    if choice == "y":
        is_dry = False
    
    # Mode = upload, Config Type = review (automatically handled by logic but we pass something)
    # Passed config type doesn't matter much for upload mode as it uses 'review' schema,
    # but we need to pass something valid or 'review'.
    cmd = f"{sys.executable} apps/finance_importer/import_sales.py \"{target_file}\" review upload"
    if is_dry:
        cmd += " --dry-run"
        
    os.system(cmd)

def run_expense_processor():
    print("\n[Expense Processor]")
    print("1. Extract (CSV/Receipt -> Working CSV)")
    print("2. Upload (Working CSV -> Freee)")
    choice = input("Choice: ").strip()
    
    if choice == "1":
        cmd = f"{sys.executable} apps/expense_processor/processor.py extract"
        os.system(cmd)
    elif choice == "2":
        # List working files
        search_path = "data/expense_processor/working/*.csv"
        files = sorted(glob.glob(search_path), reverse=True)
        if not files:
            print("No working files found.")
            return
            
        print("Select file to upload:")
        for i, f in enumerate(files):
            print(f"{i+1}. {os.path.basename(f)}")
            
        file_choice = input("Choice (default 1): ").strip()
        if not file_choice: file_choice = "1"
        try:
            idx = int(file_choice) - 1
            if idx < 0 or idx >= len(files): return
            target = files[idx]
        except ValueError: return
        
        print(f"Target: {target}")
        print("y: Execute Upload")
        print("n: Dry Run")
        mode = input("Choice (y/n): ").strip().lower()
        is_dry = mode != "y"
        
        cmd = f"{sys.executable} apps/expense_processor/processor.py upload \"{target}\""
        if is_dry:
            cmd += " --dry-run"
        os.system(cmd)
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    while True:
        # Update menu display
        print("\n=== HARAPPA Management Cockpit ===")
        print("1. [Finance Importer] Generate Review File")
        print("2. [Finance Importer] Upload from Review File")
        print("3. [Expense Processor] Extract & Upload")
        print("q. Quit")
        print("==================================")
        
        val = input("Select Action: ").strip()
        
        if val == "1":
            run_generate()
        elif val == "2":
            run_upload()
        elif val == "3":
            run_expense_processor()
        elif val == "q":
            break
        else:
            print("Unknown command.")
