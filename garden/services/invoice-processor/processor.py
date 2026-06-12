#!/usr/bin/env python3
"""invoice-processor — Gmail の請求書 → 解析 → スタッフ照合 → Freee 登録
(HMC apps/invoice_processor/ の hybrid 移植、S41)

Garden 化の差分(業務知識は継承、起動と承認だけ Garden に変える):
- gog CLI(keyring)→ Gmail API + user OAuth token(lib/gmail_client.py)
- 旧 SDK google.generativeai + gemini-2.0-flash(退役 404)→ google.genai + 2.5-flash
- データ dir をサービス相対の絶対パスに(cron で cwd 非依存)
- ★新機能 1: extract 時に soil スタッフマスターと照合し、全行に
  staff_slug / staff_contract / group(スタッフ or リスト外)を付与
- ★新機能 2: `check` = 稼働時間シート(区分=業務委託)と突合して
  「稼働があるのに請求書が来ていない人」を検出
- レビューは Google Sheets 直接編集(expense S38 案A と同 UX。to-sheet / from-sheet)

使い方:
    python processor.py fetch [--after YYYY-MM-DD]   # Gmail → Drive Inbox
    python processor.py extract [--date YYYY-MM-DD]  # Drive Inbox → review CSV(照合つき)
    python processor.py check --month YYYY-MM [--csv PATH]  # 稼働突合(請求漏れ検出)
    python processor.py to-sheet <csv> [--tab YYYYMM]
    python processor.py from-sheet <tab> [--out PATH]
    python processor.py register --file <csv> --dry-run
    python processor.py register --file <csv>        # Freee 本登録 + Gmail/Drive 後始末
"""
import argparse
import csv
import datetime
import os
import sys
import tempfile

from dotenv import load_dotenv

from lib.utils import setup_logger, ensure_directory

logger = setup_logger("InvoiceProcessor")

load_dotenv()

# --- Configuration(サービス相対の絶対パス。cron 実行で cwd に依存しない) ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(_BASE_DIR, "temp")
WORKING_DIR = os.path.join(_BASE_DIR, "working")

DRIVE_INBOX_ID = os.getenv("DRIVE_INBOX_ID")
DRIVE_PROCESSED_ID = os.getenv("DRIVE_PROCESSED_ID")
DRIVE_ERROR_ID = os.getenv("DRIVE_ERROR_ID")

# fetch のフィルタ(HMC fetcher.py から継承)
GMAIL_SEARCH_QUERY = "has:attachment -label:処理済 -label:Invoice_Fetched"
FILTER_SUBJECT_KEYWORDS = ["請求書", "invoice", "領収書", "利用明細", "bill", "payment", "精算", "費用"]
FETCH_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".zip", ".lzh"}
# extract で解析対象にする拡張子(HMC utils.is_valid_extension 相当)
ANALYZE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

# レビュー用 Sheets の勘定科目プルダウン(mapping_config の account_rules キー + 既定の外注費)
REVIEW_CATEGORIES = ["外注費", "旅費交通費", "消耗品費", "会議費", "通信費", "原材料"]

# review CSV ヘッダ = HMC 18 列(register 互換)+ スタッフ照合 3 列
CSV_HEADERS = [
    "file_id", "file_name", "date", "payee", "", "partner_code", "partner_id",
    "description", "section_name", "section_id", "account_item_name", "invoice_number",
    "amount", "document_total", "calculated_total", "diff", "warning", "tax_code",
    "staff_slug", "staff_contract", "group",
]

GROUP_STAFF = "スタッフ"
GROUP_OUTSIDE = "リスト外"


def normalize_date(date_str):
    """日付文字列を Freee API 用の YYYY-MM-DD に揃える(YYYY/MM/DD も受ける)。"""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def previous_month(today=None):
    today = today or datetime.date.today()
    first = today.replace(day=1)
    prev_last = first - datetime.timedelta(days=1)
    return prev_last.strftime("%Y-%m")


def latest_review_csv():
    """working/ の最新 invoices_*.csv を返す(無ければ None)。"""
    if not os.path.isdir(WORKING_DIR):
        return None
    cands = sorted(
        f for f in os.listdir(WORKING_DIR)
        if f.startswith("invoices_") and f.endswith(".csv")
    )
    return os.path.join(WORKING_DIR, cands[-1]) if cands else None


# =====================================================================
# fetch — Gmail → Drive Inbox(HMC fetcher.py の API 移植)
# =====================================================================

def cmd_fetch(args):
    from lib.gmail_client import GmailClient, LABEL_FETCHED, LABEL_PENDING
    from lib.drive_client import DriveClient

    if not DRIVE_INBOX_ID:
        logger.error("DRIVE_INBOX_ID が未設定です(.env)。")
        return 1

    gmail = GmailClient()
    drive = DriveClient(creds=gmail.creds)

    query = GMAIL_SEARCH_QUERY
    if args.after:
        query += f" after:{args.after.replace('-', '/')}"
    logger.info(f"Searching Gmail: {query}")

    pending_lbl_id = gmail.label_id(LABEL_PENDING)
    thread_ids = gmail.search_threads(query, max_results=30)
    if not thread_ids:
        logger.info("No matching emails found.")
        print("FETCHED_FILES: 0")
        return 0
    logger.info(f"Found {len(thread_ids)} threads.")

    uploaded = []
    for thread_id in thread_ids:
        try:
            messages = gmail.get_thread(thread_id)
            thread_had_upload = False
            for msg in messages:
                hdrs = gmail.headers(msg)
                # 対象判定: Invoice_Pending ラベル付き or 件名キーワード一致(HMC と同一)
                label_ids = msg.get("labelIds", [])
                if pending_lbl_id and pending_lbl_id in label_ids:
                    logger.info(f"  MATCH(Pending label): {hdrs['Subject']}")
                elif any(k.lower() in hdrs["Subject"].lower() for k in FILTER_SUBJECT_KEYWORDS):
                    logger.info(f"  MATCH(keyword): {hdrs['Subject']}")
                else:
                    continue

                attachments = gmail.find_attachments(msg, valid_extensions=FETCH_EXTENSIONS)
                for att in attachments:
                    filename = att["filename"]
                    with tempfile.TemporaryDirectory() as temp_dir:
                        local_path = os.path.join(temp_dir, filename)
                        gmail.download_attachment(msg["id"], att["attachmentId"], local_path)
                        # thread_id をファイル名に前置(register 後の Gmail 後始末に使う。HMC と同一)
                        new_filename = f"{thread_id}_{filename}"
                        logger.info(f"  Uploading to Drive as {new_filename}...")
                        file_id = drive.upload_file(local_path, DRIVE_INBOX_ID, name=new_filename)
                        if file_id:
                            thread_had_upload = True
                            uploaded.append({
                                "date": hdrs["Date"], "sender": hdrs["From"],
                                "subject": hdrs["Subject"], "filename": filename,
                            })
                        else:
                            logger.error(f"  Upload failed: {filename}")

            if thread_had_upload:
                gmail.modify_thread(
                    thread_id, add_labels=[LABEL_FETCHED], remove_labels=[LABEL_PENDING]
                )
        except Exception as e:
            logger.error(f"Error processing thread {thread_id}: {e}")
            continue

    print(f"FETCHED_FILES: {len(uploaded)}")
    if uploaded:
        print(f"\n{'Date':<32} | {'Sender':<30} | Subject")
        print("-" * 100)
        for f in uploaded:
            sender = (f["sender"][:27] + "...") if len(f["sender"]) > 30 else f["sender"]
            subject = (f["subject"][:45] + "...") if len(f["subject"]) > 48 else f["subject"]
            print(f"{f['date']:<32} | {sender:<30} | {subject}")
    return 0


# =====================================================================
# extract — Drive Inbox → review CSV(Gemini 解析 + ルール推論 + ★スタッフ照合)
# =====================================================================

def cmd_extract(args):
    from lib.drive_client import DriveClient
    from lib.pdf_analyzer import PDFAnalyzer
    from lib.rule_engine import RuleEngine
    from lib.freee_client import FreeeClient
    from lib.staff_master import StaffMatcher

    if not DRIVE_INBOX_ID:
        logger.error("DRIVE_INBOX_ID が未設定です(.env)。")
        return 1

    ensure_directory(TEMP_DIR)
    ensure_directory(WORKING_DIR)

    drive = DriveClient()
    analyzer = PDFAnalyzer()
    freee = FreeeClient()
    rule_engine = RuleEngine(freee)
    matcher = StaffMatcher()

    logger.info(f"Checking Drive folder {DRIVE_INBOX_ID}...")
    files = drive.list_files_in_folder(DRIVE_INBOX_ID)
    files = [
        f for f in files
        if os.path.splitext(f["name"])[1].lower() in ANALYZE_EXTENSIONS
    ]
    if not files:
        logger.info("No files found.")
        print("EXTRACT_ROWS: 0")
        return 0
    logger.info(f"Found {len(files)} files.")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(WORKING_DIR, f"invoices_{timestamp}.csv")

    extracted = []
    failed_files = []
    for file in files:
        file_id, file_name = file["id"], file["name"]
        logger.info(f"Processing {file_name}...")
        local_path = os.path.join(TEMP_DIR, file_name)
        if not drive.download_file(file_id, local_path):
            logger.error("Failed to download file.")
            failed_files.append(file_name)
            continue

        result = analyzer.analyze(
            local_path, section_candidates=list(rule_engine.sections.keys())
        )
        if os.path.exists(local_path):
            os.remove(local_path)
        if not result:
            logger.error(f"Failed to analyze {file_name}.")
            failed_files.append(file_name)
            continue

        items = result.get("items", [])

        # --- 金額整合性チェック + 補正(HMC と同一: 税抜→税込 / 端数 / MISMATCH) ---
        document_total = result.get("document_total") or 0
        calculated_total = sum(item.get("amount") or 0 for item in items)
        diff = calculated_total - document_total
        warning_msg = ""
        if diff != 0:
            logger.info(f"Integrity Mismatch: Doc={document_total}, Calc={calculated_total}, Diff={diff}")
            if abs(int(calculated_total * 1.1) - document_total) <= 5:
                logger.info("Correction: Items seem to be Tax-Exclusive. Adding 10% tax.")
                for item in items:
                    item["amount"] = int((item.get("amount") or 0) * 1.1)
                calculated_total = sum(item["amount"] for item in items)
                diff = calculated_total - document_total
            if abs(diff) <= 5 and items:
                logger.info(f"Correction: Adjusting rounding error of {diff} JPY.")
                largest_item = max(items, key=lambda x: x.get("amount") or 0)
                if largest_item.get("amount") is None:
                    largest_item["amount"] = 0
                largest_item["amount"] -= diff
                calculated_total = sum(item["amount"] for item in items)
                diff = calculated_total - document_total
            if diff != 0:
                warning_msg = "MISMATCH"
                logger.warning(f"Final Mismatch: {diff}")

        transaction_date = args.date if args.date else result.get("date")

        # --- 支払先正規化 + 取引先解決(HMC と同一) ---
        raw_payee = result.get("payee") or ""
        main_desc = result.get("description") or ""
        full_text_list = [main_desc] + [
            item["description"] for item in items if item.get("description")
        ]
        full_text = " ".join(full_text_list)
        normalized_payee = rule_engine.normalize_payee(raw_payee, extra_text=full_text)
        partner_info = rule_engine.resolve_partner_id(normalized_payee)
        partner_id = partner_info.get("id")
        partner_code = partner_info.get("code")

        # --- ★スタッフ照合(S41 新機能 1): ファイル単位で請求元を判定 ---
        staff = matcher.match(payee=normalized_payee, partner_id=partner_id)
        if not staff and raw_payee != normalized_payee:
            staff = matcher.match(payee=raw_payee)

        for item in items:
            item_desc = item.get("description") or ""
            item_amount = item.get("amount") or 0

            section_info = rule_engine.guess_section(item_desc)
            if not section_info["section_id"]:
                item_section_name = item.get("section_name")
                if item_section_name and item_section_name in rule_engine.sections:
                    section_info = {
                        "section_name": item_section_name,
                        "section_id": rule_engine.sections[item_section_name],
                    }
                else:
                    top_section = result.get("section_name")
                    if top_section and top_section in rule_engine.sections:
                        section_info = {
                            "section_name": top_section,
                            "section_id": rule_engine.sections[top_section],
                        }

            inferred = rule_engine.infer_category(normalized_payee, item_desc)
            tax_val = inferred.get("tax_code", 189)
            tax_display = f"{tax_val}: {rule_engine.get_tax_code_name(tax_val)}"

            extracted.append({
                "file_id": file_id,
                "file_name": file_name,
                "date": transaction_date,
                "payee": normalized_payee,
                "": "",
                "partner_code": partner_code or "",
                "partner_id": partner_id or "",
                "description": item_desc,
                "section_name": section_info.get("section_name") or "",
                "section_id": section_info.get("section_id") or "",
                "account_item_name": inferred.get("account_item_name", "外注費"),
                "invoice_number": result.get("invoice_number") or "",
                "amount": item_amount,
                "document_total": document_total,
                "calculated_total": calculated_total,
                "diff": diff,
                "warning": warning_msg,
                "tax_code": tax_display,
                "staff_slug": staff["slug"] if staff else "",
                "staff_contract": staff["contract"] if staff else "",
                "group": GROUP_STAFF if staff else GROUP_OUTSIDE,
            })

    if not extracted:
        logger.info("No data extracted.")
        print("EXTRACT_ROWS: 0")
        if failed_files:
            print(f"EXTRACT_FAILED_FILES: {','.join(failed_files)}")
            return 1
        return 0

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(extracted)
    logger.info(f"Extraction complete. Saved to {csv_path}")

    n_files = len({r["file_id"] for r in extracted})
    n_staff = len({r["file_id"] for r in extracted if r["group"] == GROUP_STAFF})
    # 呼び出し側(種 / bot)が拾える機械可読な行
    print(f"REVIEW_CSV: {csv_path}")
    print(f"EXTRACT_ROWS: {len(extracted)}")
    print(f"EXTRACT_FILES: {n_files}")
    print(f"EXTRACT_STAFF_FILES: {n_staff}")
    print(f"EXTRACT_OUTSIDE_FILES: {n_files - n_staff}")
    if failed_files:
        print(f"EXTRACT_FAILED_FILES: {','.join(failed_files)}")
    return 0


# =====================================================================
# check — ★稼働突合(S41 新機能 2): 区分=業務委託 で稼働あり & 請求書なしを検出
# =====================================================================

def cmd_check(args):
    from lib.staff_master import StaffMatcher
    from lib.worktime import read_worked_staff

    target_ym = args.month or previous_month()
    csv_path = args.csv or latest_review_csv()

    invoiced_slugs = set()
    invoiced_payees_outside = set()
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("staff_slug"):
                    invoiced_slugs.add(row["staff_slug"])
                elif row.get("payee"):
                    invoiced_payees_outside.add(row["payee"])
        logger.info(f"Review CSV: {csv_path}(スタッフ請求 {len(invoiced_slugs)} 名)")
    else:
        logger.warning("review CSV が見つかりません(請求 0 件として突合します)。")

    worked = read_worked_staff(target_ym)
    if worked is None:
        print(f"CHECK_MONTH: {target_ym}")
        print("CHECK_RESULT: NO_WORKTIME_SHEET")
        print(f"⚠️ '{target_ym}_稼働時間' シートがまだ無いため、稼働突合はできませんでした。")
        return 0

    matcher = StaffMatcher()
    expected = []   # 区分=業務委託 で稼働実績のある人(請求書が来るはずの人)
    for w in worked:
        if w["payment_type"] != "業務委託":
            continue
        # 稼働 0(空 / 0 / 0:00)は「稼働があるのに請求がない」の対象外。
        # 形式不明の値は安全側(対象に含める)に倒す
        h = (w["hours"] or "").strip()
        if h in ("", "-", "0") or h.startswith("0:00"):
            continue
        staff = matcher.find_by_name(w["name"])
        # soil で contract=経営(代表)は請求書を出さない働き方なので突合対象外
        # (S43 ガクチョ「僕は請求ナシです」。稼働シートの区分が業務委託のままでも除外)
        if staff and staff.get("contract") == "経営":
            continue
        expected.append({
            "name": w["name"],
            "slug": staff["slug"] if staff else "",
            "hours": w["hours"],
        })

    # 稼働シート外でも毎月請求が来る人(soil の invoice_monthly: true。大阪チーム等、S43)
    expected_slugs = {e["slug"] for e in expected if e["slug"]}
    for s in matcher.staff:
        if s.get("invoice_monthly") and s["slug"] not in expected_slugs:
            expected.append({"name": s["name"], "slug": s["slug"], "hours": ""})

    missing = [
        e for e in expected
        if not (e["slug"] and e["slug"] in invoiced_slugs)
    ]

    print(f"CHECK_MONTH: {target_ym}")
    print(f"CHECK_EXPECTED: {len(expected)}")
    print(f"CHECK_INVOICED_STAFF: {len(invoiced_slugs)}")
    print(f"CHECK_OUTSIDE_PAYEES: {len(invoiced_payees_outside)}")
    if missing:
        print(f"CHECK_MISSING: {','.join(m['name'] for m in missing)}")
        print(f"\n⚠️ {target_ym} に稼働があるのに請求書が見当たらない業務委託スタッフ({len(missing)} 名):")
        for m in missing:
            hours = f"(稼働 {m['hours']}h)" if m["hours"] else "(毎月請求・稼働シート外)"
            soil = "" if m["slug"] else " ※soil スタッフマスター未照合"
            print(f"  - {m['name']} {hours}{soil}")
    else:
        print("CHECK_MISSING: NONE")
        print(f"\n✅ {target_ym} 稼働の業務委託スタッフ {len(expected)} 名、全員分の請求書が揃っています。")
    if invoiced_payees_outside:
        print(f"\n📋 リスト外(スタッフ以外)の請求元 {len(invoiced_payees_outside)} 件:")
        for p in sorted(invoiced_payees_outside):
            print(f"  - {p}")
    return 0


# =====================================================================
# to-sheet / from-sheet — レビュー用 Sheets(expense S38 案A と同 UX)
# =====================================================================

def cmd_external(args):
    """外部スタッフ(稼働シート区分=追加)の稼働金額 → レビュー行(S43)。

    HMC export_external_staff.py を移植。請求書を出さない外部スタッフは
    稼働時間シートのカテゴリ別金額(生成済み)から部門ごとに行を展開し、
    Freee 登録候補としてレビュー Sheet に追記する。tax は不課税(20)。
    """
    from lib.worktime import read_external_amounts
    from lib.staff_master import StaffMatcher
    from lib.freee_client import FreeeClient

    target_ym = args.month or previous_month()
    data = read_external_amounts(target_ym)
    if data is None:
        print(f"EXTERNAL_RESULT: NO_WORKTIME_SHEET({target_ym})")
        return 0
    if not data:
        print("EXTERNAL_ROWS: 0")
        print(f"({target_ym} は区分=追加の外部スタッフがいません)")
        return 0

    import json
    mapping_path = os.path.join(_BASE_DIR, "config", "section_mapping.json")
    with open(mapping_path, encoding="utf-8") as f:
        sm = json.load(f)
    section_map = sm.get("mapping", {})
    default_account = sm.get("default_account_item", "外注費")

    matcher = StaffMatcher()
    freee = FreeeClient()
    partners = {p["name"].replace(" ", "").replace("　", ""): p for p in freee.get_partners() or []}

    # 請求日 = 月末
    year, month = map(int, target_ym.split("-"))
    nxt = datetime.date(year + 1, 1, 1) if month == 12 else datetime.date(year, month + 1, 1)
    invoice_date = (nxt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    rows, unmatched = [], []
    for i, ext in enumerate(data, start=1):
        staff = matcher.find_by_name(ext["name"])
        partner_id = staff["freee_id"] if staff and staff.get("freee_id") else ""
        if not partner_id:
            p = partners.get(ext["name"].replace(" ", "").replace("　", ""))
            partner_id = p["id"] if p else ""
        if not partner_id:
            unmatched.append(ext["name"])
        for cat, amount in ext["amounts"].items():
            rows.append({
                "file_id": f"{target_ym.replace('-', '')}_extra_{i:03d}",
                "file_name": "",  # 空 = register が Gmail/Drive 後始末をスキップ(既存仕様)
                "date": invoice_date,
                "payee": ext["name"],
                "partner_code": "",
                "partner_id": partner_id,
                "description": f"{target_ym} {cat} 稼働分",
                "section_name": section_map.get(cat, cat),
                "section_id": "",
                "account_item_name": default_account,
                "invoice_number": "",
                "amount": amount,
                "document_total": "",
                "calculated_total": "",
                "diff": "",
                "warning": "" if partner_id else "PARTNER未解決",
                "tax_code": "20: 不課税",  # 個人払い(HMC 既定を継承、表記は Freee name_ja)
                "staff_slug": staff["slug"] if staff else "",
                "staff_contract": "外部スタッフ",
                "group": "外部スタッフ",
            })

    if not rows:
        print("EXTERNAL_ROWS: 0")
        print(f"({target_ym} の区分=追加スタッフに金額>0 のカテゴリがありません)")
        return 0

    ensure_directory(WORKING_DIR)
    out = os.path.join(WORKING_DIR, f"external_{target_ym.replace('-', '')}.csv")
    headers = list(rows[0].keys())
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    total = sum(r["amount"] for r in rows)
    print(f"EXTERNAL_CSV: {out}")
    print(f"EXTERNAL_ROWS: {len(rows)}({len(data)}名 / 計 ¥{total:,})")
    if unmatched:
        print(f"EXTERNAL_UNMATCHED: {','.join(unmatched)}(Freee 取引先未解決 — 警告列に記載)")

    if args.append_sheet:
        from lib import sheets_client
        url, start_row = sheets_client.append_rows(
            rows, args.append_sheet, background=sheets_client.EXTERNAL_BG)
        print(f"EXTERNAL_SHEET_URL: {url}")
        print(f"(タブ {args.append_sheet} の {start_row} 行目から薄緑で追記)")
    return 0


def cmd_to_sheet(args):
    from lib import sheets_client
    from lib.rule_engine import RuleEngine

    csv_path = args.file
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return 1
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        logger.info("CSV にデータ行がありません。シートは作りません。")
        print("EMPTY: no rows")
        return 0

    # スタッフ請求を先頭・リスト外を後ろに並べる(ガクチョが見る順)
    rows.sort(key=lambda r: (r.get("group") != GROUP_STAFF, r.get("payee", "")))

    tab = args.tab or datetime.datetime.now().strftime("%Y%m")
    sections = list(RuleEngine(None).sections.keys())
    url, gid = sheets_client.write_tab(rows, tab, REVIEW_CATEGORIES, sections=sections)
    logger.info(f"Wrote {len(rows)} rows to review tab {tab}: {url}")
    print(f"REVIEW_SHEET_URL: {url}")
    print(f"REVIEW_TAB: {tab}")
    print(f"REVIEW_ROWS: {len(rows)}")
    return 0


def cmd_from_sheet(args):
    from lib import sheets_client

    tab = args.tab
    rows = sheets_client.read_tab(tab)
    if not rows:
        logger.error(f"タブ {tab} に有効な行がありません(全削除 or タブ無し)。")
        print("EMPTY: no rows after review")
        return 1
    ensure_directory(WORKING_DIR)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(WORKING_DIR, f"invoices_{tab}_reviewed_{ts}.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=sheets_client.CSV_KEYS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in sheets_client.CSV_KEYS})
    logger.info(f"Read {len(rows)} reviewed rows from tab {tab} → {out}")
    print(f"REVIEWED_CSV: {out}")
    print(f"REVIEWED_ROWS: {len(rows)}")
    return 0


# =====================================================================
# register — CSV → Freee 登録 + Gmail/Drive 後始末(HMC cmd_register 移植)
# =====================================================================

def cmd_register(args):
    from lib.freee_client import FreeeClient
    from lib.rule_engine import RuleEngine

    csv_path = args.file
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return 1

    freee = FreeeClient()
    rule_engine = RuleEngine(freee)

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        logger.info("No rows in CSV.")
        return 0

    print(f"Found {len(rows)} rows to register.")
    if args.dry_run:
        print("[DRY RUN] No changes will be made to Freee, Gmail or Drive.")

    processed_files = {}   # file_id -> file_name(成功分。Drive 移動 + Gmail 後始末用)
    error_files = set()
    num_success = 0
    num_error = 0

    for i, row in enumerate(rows):
        rownum = i + 1
        if not row.get("amount") or not row.get("date") or not row.get("account_item_name"):
            logger.warning(f"Row {rownum}: Missing required fields. Skipping.")
            error_files.add(row.get("file_id"))
            num_error += 1
            continue

        acct_name = row["account_item_name"].strip()
        acct_id = rule_engine.resolve_account_item_id(acct_name)
        if not acct_id:
            logger.error(f"Row {rownum}: Invalid Account Item '{acct_name}'. Skipping.")
            error_files.add(row.get("file_id"))
            num_error += 1
            continue

        sect_id = row.get("section_id")
        sect_name = row.get("section_name")
        if not sect_id and sect_name and sect_name in rule_engine.sections:
            sect_id = rule_engine.sections[sect_name]

        part_id = row.get("partner_id")
        final_desc = row.get("description") or ""
        if not part_id:
            final_desc = f"{row.get('payee')} - {final_desc}"

        try:
            tax_code = int(str(row.get("tax_code", "189")).split(":")[0].strip())
        except ValueError:
            logger.error(f"Row {rownum}: 不正な tax_code '{row.get('tax_code')}'. Skipping.")
            error_files.add(row.get("file_id"))
            num_error += 1
            continue

        amount = int(str(row["amount"]).replace(",", "").replace("¥", ""))
        deal_date = normalize_date(row.get("date"))

        if args.dry_run:
            print(
                f"[DRY RUN] Register: {deal_date} ¥{amount:,} {acct_name} "
                f"(Sect:{sect_name or '-'} / Partner:{part_id or '-'} / Tax:{tax_code}) {final_desc[:40]}"
            )
            processed_files[row.get("file_id")] = row.get("file_name", "")
            num_success += 1
            continue

        resp = freee.post_deal(
            date=deal_date,
            amount=amount,
            description=final_desc,
            account_item_id=acct_id,
            section_id=int(sect_id) if sect_id else None,
            partner_id=int(part_id) if part_id else None,
            tax_code=tax_code,
            type="expense",
        )
        if resp:
            logger.info(f"Registered row {rownum}: {deal_date} ¥{amount:,} {acct_name}")
            processed_files[row.get("file_id")] = row.get("file_name", "")
            num_success += 1
        else:
            logger.error(f"Row {rownum}: Freee 登録失敗(直前の API エラー参照)")
            error_files.add(row.get("file_id"))
            num_error += 1

    # --- 後始末: Gmail ラベル + Drive 移動(成功ファイルのみ。dry-run はスキップ) ---
    if not args.dry_run:
        gmail = None
        drive = None
        try:
            from lib.gmail_client import GmailClient, LABEL_PROCESSED, LABEL_FETCHED
            from lib.drive_client import DriveClient
            gmail = GmailClient()
            drive = DriveClient(creds=gmail.creds)
        except Exception as e:
            logger.warning(f"Gmail/Drive クライアント初期化失敗(後始末スキップ): {e}")

        if gmail and drive:
            # HMC cmd_register と同じ後始末:
            #   成功ファイル(エラー行を含まないもの)→ Processed + Gmail 処理済化
            #   エラー行を含むファイル → Error フォルダ
            finalized_threads = set()
            for fid, fname in processed_files.items():
                if not fid or fid in error_files:
                    continue
                # 外部スタッフ CSV 行などファイル実体の無い行(file_name 空)は後始末不要
                if not fname:
                    continue
                # Gmail 後始末: ファイル名先頭の thread_id(fetch が前置)で処理済化
                parts = fname.split("_", 1)
                if len(parts) > 1 and len(parts[0]) >= 10 and parts[0] not in finalized_threads:
                    try:
                        gmail.modify_thread(
                            parts[0],
                            add_labels=[LABEL_PROCESSED],
                            remove_labels=["INBOX", LABEL_FETCHED],
                        )
                        finalized_threads.add(parts[0])
                    except Exception as e:
                        logger.warning(f"Gmail 後始末失敗(thread {parts[0]}): {e}")
                if DRIVE_PROCESSED_ID:
                    drive.move_file(fid, DRIVE_INBOX_ID, DRIVE_PROCESSED_ID)
            if DRIVE_ERROR_ID:
                for fid in error_files:
                    # 実体の無い id(外部 CSV のダミー等)は move が警告を出して終わる(HMC と同じ)
                    if fid:
                        drive.move_file(fid, DRIVE_INBOX_ID, DRIVE_ERROR_ID)

    print("\n--- Registration Summary ---")
    print(f"Total:   {len(rows)}")
    print(f"Success: {num_success}")
    print(f"Error:   {num_error}")
    print(f"REGISTER_SUCCESS: {num_success}")
    print(f"REGISTER_ERROR: {num_error}")

    if num_error > 0:
        logger.error(f"Registration finished with {num_error} errors.")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Invoice Processor (Garden)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_fetch = subparsers.add_parser("fetch", help="Gmail → Drive Inbox")
    p_fetch.add_argument("--after", help="この日付以降のメールのみ(YYYY-MM-DD)")

    p_extract = subparsers.add_parser("extract", help="Drive Inbox → review CSV(スタッフ照合つき)")
    p_extract.add_argument("--date", help="取引日を強制上書き(YYYY-MM-DD)")

    p_check = subparsers.add_parser("check", help="稼働突合(請求漏れ検出)")
    p_check.add_argument("--month", help="対象月 YYYY-MM(省略時は前月)")
    p_check.add_argument("--csv", help="review CSV パス(省略時は working/ の最新)")

    p_to_sheet = subparsers.add_parser("to-sheet", help="review CSV → レビュー用 Sheets タブ")
    p_to_sheet.add_argument("file", help="review CSV のパス")
    p_to_sheet.add_argument("--tab", default=None, help="タブ名(既定: 現在の YYYYMM)")

    p_from_sheet = subparsers.add_parser("from-sheet", help="レビュー用タブ → CSV 書き戻し")
    p_from_sheet.add_argument("tab", help="読み戻すタブ名(YYYYMM)")
    p_from_sheet.add_argument("--out", default=None, help="出力 CSV パス")

    p_register = subparsers.add_parser("register", help="CSV → Freee 登録 + 後始末")
    p_register.add_argument("--file", required=True, help="登録する CSV のパス")
    p_register.add_argument("--dry-run", action="store_true")

    p_external = subparsers.add_parser(
        "external", help="外部スタッフ(区分=追加)の稼働金額 → レビュー行(S43)")
    p_external.add_argument("--month", help="対象月 YYYY-MM(省略時は前月)")
    p_external.add_argument("--append-sheet", default=None,
                            help="既存レビュータブ(YYYYMM)の末尾に追記する")

    args = parser.parse_args()
    handlers = {
        "fetch": cmd_fetch,
        "extract": cmd_extract,
        "check": cmd_check,
        "to-sheet": cmd_to_sheet,
        "from-sheet": cmd_from_sheet,
        "register": cmd_register,
        "external": cmd_external,
    }
    rc = handlers[args.command](args)
    if rc:
        sys.exit(rc)


if __name__ == "__main__":
    main()
