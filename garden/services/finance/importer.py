#!/usr/bin/env python3
"""importer — 売上CSV(STORES/Square)→ Freee 振替伝票(HMC apps/finance_importer/ 移植)

Garden 化の差分(業務知識は継承、起動と承認だけ Garden に変える):
- import パス: modules.* / apps.* → lib.*(同 service 内に集約)
- 部門推定は Gemini を外しルールのみ(section_guesser。当たらなければ空欄 → ガクチョが Sheets で埋める)
- 人間が CSV を手編集 → upload の代わりに、レビューを **Google Sheets タブ**に出す(expense/invoice と統一)
- Drive から売上CSVを取得(ガクチョが毎月5日にアップ)。stores/square は中身で自動判定
- データ dir はサービス相対の絶対パス(cron 実行で cwd 非依存)

フロー(SKILL Mode I):
    importer.py fetch                       # Drive の売上CSV → input/
    importer.py generate                    # input/ → 振替伝票候補 review CSV(部門ルール推定)
    importer.py to-sheet <csv> --tab YYYYMM # レビュー用 Sheets タブを作る(ガクチョが部門を埋める)
    importer.py from-sheet <tab>            # レビュー後タブ → working CSV
    importer.py register <csv> --dry-run    # 振替伝票の内容を確認(Freee 更新しない)
    importer.py register <csv>              # Freee に manual_journal 本登録 + Drive 原本を processed へ
"""
import os
import sys
import csv
import json
import hashlib
import calendar
import argparse
import datetime
from datetime import datetime as dt_cls

from dotenv import load_dotenv

from lib.freee_client import FreeeClient
from lib.utils import setup_logger, ensure_directory
from lib.drive_client import DriveClient
from lib.section_guesser import SectionGuesser

logger = setup_logger("FinanceImporter")
load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(_BASE_DIR, "input")
REVIEW_DIR = os.path.join(_BASE_DIR, "review")
PROCEEDED_DIR = os.path.join(_BASE_DIR, "proceeded")
CONFIG_PATH = os.path.join(_BASE_DIR, "config", "mapping_config.json")

# ガクチョが毎月5日に売上CSVをアップする Drive フォルダ
DRIVE_FOLDER_ID = os.getenv("FINANCE_SALES_DRIVE_FOLDER_ID")

# レビュー Sheets の列(位置固定)。section_name にプルダウン、空ならハイライト。
REVIEW_COLUMNS = [
    ("date", "取引日"),
    ("registration_date", "起票日(月末)"),
    ("amount", "金額"),
    ("description", "摘要"),
    ("section_name", "部門"),
]


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 冪等性台帳(S49 測量士 P1)──────────────────────────────────────────────
# register が行ごとに Freee へ post する構造上、部分失敗(例: 79行中78行成功・1行失敗)で
# input が残り、同じ review CSV を再投入すると成功済み行も再投稿されて二重記帳になる。
# 登録成功した行の hash を append-only 台帳に残し、再実行時は登録済み行を skip する。
def _state_dir():
    # VPS では FINANCE_STATE_DIR を指定可。既定は service 相対(.gitignore 済)。
    return os.getenv("FINANCE_STATE_DIR") or os.path.join(_BASE_DIR, "state")


def _ledger_path():
    return os.path.join(_state_dir(), "registered_ledger.jsonl")


def _row_hash(issue_date, amount, description, section_name, occurrence):
    """振替伝票1行を一意に識別。同一CSV内の重複行は occurrence(0,1,2…)で区別し、
    まったく同じ取引が正当に2件あっても2件目を誤 skip しないようにする。"""
    key = f"{issue_date}|{amount}|{description}|{section_name}|{occurrence}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _load_ledger():
    path = _ledger_path()
    seen = set()
    if not os.path.exists(path):
        return seen
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(json.loads(line)["hash"])
            except (json.JSONDecodeError, KeyError):
                continue
    return seen


def _append_ledger(entry):
    ensure_directory(_state_dir())
    with open(_ledger_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_amount(value, params=None):
    if not value:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if params:
        if params.get("is_quoted"):
            value = value.replace('"', "")
        for char in params.get("remove_chars", []):
            value = value.replace(char, "")
    try:
        return int(float(value))
    except ValueError:
        return 0


def get_description(row, options, config_type):
    if config_type == "stores":
        opts = options if isinstance(options, list) else [options]
        for opt in opts:
            if opt in row and row[opt]:
                return row[opt]
    elif config_type == "review":
        return row.get(options, "")
    elif isinstance(options, str):
        return row.get(options, "")
    return ""


# 形式ごとのエンコーディング候補(STORES は実エクスポートが utf-8-sig、旧式が shift_jis。
# Square は utf-16 タブ区切り)。実ファイルで判定するので config に固定しすぎない。
_TYPE_ENCODINGS = {
    "stores": ["utf-8-sig", "shift_jis", "cp932"],
    "square": ["utf-16", "utf-8-sig"],
}


def _read_header(path, enc):
    try:
        with open(path, "r", encoding=enc) as f:
            return f.readline()
    except (UnicodeDecodeError, UnicodeError):
        return None


def detect_csv_type(file_path, config):
    """CSV の中身から (形式, 実エンコーディング) を自動判定。判定不能なら (None, None)。

    STORES: `取引日時` + `売上` 列(products / reservations 両エクスポートに共通)。
    Square: `日付` 列(utf-16 タブ区切り)。
    """
    s = config["stores"]
    for enc in _TYPE_ENCODINGS["stores"]:
        h = _read_header(file_path, enc)
        if h and s["date_column"] in h and s["amount_column"] in h:
            return "stores", enc
    q = config["square"]
    for enc in _TYPE_ENCODINGS["square"]:
        h = _read_header(file_path, enc)
        if h and q["date_column"] in h:
            return "square", enc
    return None, None


# ── fetch(Drive → input/)──────────────────────────────────────────────────────
def cmd_fetch(args):
    ensure_directory(INPUT_DIR)
    if not DRIVE_FOLDER_ID:
        logger.error("FINANCE_SALES_DRIVE_FOLDER_ID が未設定です。")
        print("FETCHED_FILES: 0")
        return 0
    drive = DriveClient()
    if not drive.service:
        logger.error("Drive 認証に失敗しました(secrets/credentials.json を確認)。")
        print("FETCHED_FILES: 0")
        return 1
    files = drive.list_files_in_folder(DRIVE_FOLDER_ID)
    csvs = [f for f in files if f["name"].lower().endswith(".csv")
            and f["mimeType"] != "application/vnd.google-apps.folder"]
    for f in csvs:
        local = os.path.join(INPUT_DIR, f["name"])
        logger.info(f"Downloading {f['name']} from Drive...")
        drive.download_file(f["id"], local)
    print(f"FETCHED_FILES: {len(csvs)}")
    return 0


# ── generate(input/ → review CSV)────────────────────────────────────────────
def cmd_generate(args):
    config = load_config()
    sections_map = config.get("sections", {})
    guesser = SectionGuesser(CONFIG_PATH)
    ensure_directory(INPUT_DIR)
    ensure_directory(REVIEW_DIR)

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".csv")]
    if not files:
        logger.info("input/ に売上CSVがありません。")
        print("EXTRACT_ROWS: 0")
        return 0

    output_rows = []
    for filename in files:
        path = os.path.join(INPUT_DIR, filename)
        ctype, enc = detect_csv_type(path, config)
        if not ctype:
            logger.warning(f"形式を判定できないCSV(stores/square 以外): {filename} — スキップ")
            continue
        rules = config[ctype]
        enc = enc or rules.get("encoding", "utf-8")  # 検出した実エンコーディングを優先
        logger.info(f"Parsing {filename} as {ctype} (encoding={enc})...")
        with open(path, "r", encoding=enc) as f:
            reader = csv.DictReader(f, delimiter=rules.get("delimiter", ","))
            for row in reader:
                try:
                    if ctype == "square":
                        date_str = f"{row[rules['date_column']]} {row[rules['time_column']]}"
                    else:
                        date_str = row[rules["date_column"]]
                    date_str = date_str.replace("/", "-")
                    d = dt_cls.strptime(date_str, rules["date_format"])
                    formatted_date = d.strftime("%Y-%m-%d")
                    # 起票日 = 入金ベース(ガクチョ方針 S47): --month 指定時は取引日時に関係なく
                    # その入金月の末日に売上を立てる(4月取引でも 5月入金なら 5/31)。
                    # 未指定時は取引日時の月末(旧挙動・手動単発用)。
                    if args.month:
                        ry, rm = [int(x) for x in args.month.split("-")]
                    else:
                        ry, rm = d.year, d.month
                    last_day = calendar.monthrange(ry, rm)[1]
                    registration_date = datetime.date(ry, rm, last_day).strftime("%Y-%m-%d")

                    amount = parse_amount(row[rules["amount_column"]], rules.get("amount_params"))
                    if amount <= 0:
                        continue

                    desc_col = rules.get("description_column") or rules.get("description_options")
                    description = get_description(row, desc_col, ctype)
                    if "[FinanceImporter]" not in description:
                        description = f"{description} [FinanceImporter]"

                    section_name = guesser.guess_name(description)
                    output_rows.append({
                        "date": formatted_date,
                        "registration_date": registration_date,
                        "amount": amount,
                        "description": description,
                        "section_name": section_name,
                    })
                except Exception as e:
                    logger.error(f"行の処理でエラー({filename}): {e}")

    if not output_rows:
        logger.info("有効な売上行がありませんでした。")
        print("EXTRACT_ROWS: 0")
        return 0

    ts = dt_cls.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(REVIEW_DIR, f"review_{ts}.csv")
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[k for k, _ in REVIEW_COLUMNS])
        writer.writeheader()
        writer.writerows(output_rows)
    n_missing = sum(1 for r in output_rows if not r["section_name"])
    logger.info(f"Review CSV generated: {out_path}")
    print(f"REVIEW_CSV: {out_path}")
    print(f"EXTRACT_ROWS: {len(output_rows)}")
    print(f"SECTION_MISSING: {n_missing}")
    return 0


# ── to-sheet / from-sheet ─────────────────────────────────────────────────────
def cmd_to_sheet(args):
    from lib import sheets_client
    # 部門ドロップダウンは **実 Freee を正本**(mapping_config は guesser ヒント用で古くなり得る)
    client = FreeeClient()
    sections = [s["name"] for s in client.get_sections()]
    with open(args.file, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("EMPTY: no rows")
        return 0
    tab = args.tab or dt_cls.now().strftime("%Y%m")
    url, gid = sheets_client.write_tab(
        rows, tab, REVIEW_COLUMNS,
        dropdown_key="section_name", dropdown_values=sections,
        highlight_keys=["section_name"],
    )
    logger.info(f"Wrote {len(rows)} rows to review tab {tab}: {url}")
    print(f"REVIEW_SHEET_URL: {url}")
    print(f"REVIEW_TAB: {tab}")
    print(f"REVIEW_ROWS: {len(rows)}")
    return 0


def cmd_from_sheet(args):
    from lib import sheets_client
    rows = sheets_client.read_tab(args.tab, REVIEW_COLUMNS)
    # 金額が空/0 の行(ガクチョが削除)はスキップ
    rows = [r for r in rows if (r.get("amount", "").replace(",", "").strip() not in ("", "0"))]
    if not rows:
        logger.error(f"タブ {args.tab} に有効な行がありません。")
        print("EMPTY: no rows after review")
        return 1
    ensure_directory(REVIEW_DIR)
    ts = dt_cls.now().strftime("%Y%m%d_%H%M%S")
    out = args.out or os.path.join(REVIEW_DIR, f"review_{args.tab}_reviewed_{ts}.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k, _ in REVIEW_COLUMNS])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in [c for c, _ in REVIEW_COLUMNS]})
    logger.info(f"Read {len(rows)} reviewed rows from tab {args.tab} → {out}")
    print(f"REVIEWED_CSV: {out}")
    print(f"REVIEWED_ROWS: {len(rows)}")
    return 0


# ── register(review CSV → Freee manual_journal)──────────────────────────────
def cmd_register(args):
    config = load_config()
    rules = config["review"]

    if not os.path.exists(args.file):
        logger.error(f"File not found: {args.file}")
        return 1

    with open(args.file, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        logger.info("CSV にデータ行がありません。")
        print("REGISTERED: 0")
        return 0

    client = FreeeClient()
    # 部門 name→id は **実 Freee を正本**(mapping_config の古い部門で誤記帳しないように)
    sections_map = {s["name"]: s["id"] for s in client.get_sections()}
    # 勘定科目 ID
    credit_id = client.get_account_items(rules["account_item_name"])
    debit_id = client.get_account_items(rules.get("debit_account_item_name", "前受金"))
    if not credit_id or not debit_id:
        logger.error("勘定科目(売上高 / 前受金)が Freee に見つかりません。")
        return 1
    # 税区分
    tax_code_credit, tax_code_debit = None, None
    for t in client.get_taxes():
        if t["name"] == "taxable_10":
            tax_code_credit = t["code"]
        elif t["name"] == "taxable" and not tax_code_credit:
            tax_code_credit = t["code"]
        if t["name"] == "non_taxable":
            tax_code_debit = t["code"]
    tax_code_credit = tax_code_credit or 1
    tax_code_debit = tax_code_debit or 2

    ledger = _load_ledger()
    seen_counts = {}
    registered, skipped, failed = 0, 0, []
    for i, row in enumerate(rows):
        rownum = i + 1
        try:
            amount = parse_amount(row.get("amount", "0"), {"remove_chars": [","]})
            if amount <= 0:
                continue
            description = row.get("description", "")
            section_name = (row.get("section_name") or "").strip()
            section_id = sections_map.get(section_name) if section_name else None
            reg_col = rules.get("registration_date_column")
            issue_date = (row.get(reg_col) or "").replace("/", "-").strip()
            if not issue_date:
                d = dt_cls.strptime(row["date"].replace("/", "-"), "%Y-%m-%d")
                last_day = calendar.monthrange(d.year, d.month)[1]
                issue_date = datetime.date(d.year, d.month, last_day).strftime("%Y-%m-%d")

            # 冪等性: 同一CSV内の重複行は occurrence で区別し、登録済み行は台帳で skip
            occ_key = f"{issue_date}|{amount}|{description}|{section_name}"
            occurrence = seen_counts.get(occ_key, 0)
            seen_counts[occ_key] = occurrence + 1
            rhash = _row_hash(issue_date, amount, description, section_name, occurrence)
            already = rhash in ledger

            if args.dry_run:
                tag = " [登録済→skip]" if already else ""
                logger.info(f"[DRY RUN] {issue_date} ¥{amount:,} / {description} / 部門:{section_name or '(なし)'}{tag}")
                continue

            if already:
                skipped += 1
                logger.info(f"Skip(登録済): {issue_date} ¥{amount:,} / {description}")
                continue

            details = [
                {"entry_side": "debit", "account_item_id": debit_id, "tax_code": tax_code_debit,
                 "amount": amount, "description": description, "section_id": section_id},
                {"entry_side": "credit", "account_item_id": credit_id, "tax_code": tax_code_credit,
                 "amount": amount, "description": description, "section_id": section_id},
            ]
            resp = client.post_manual_journal(issue_date, details)
            if resp:
                registered += 1
                _append_ledger({
                    "hash": rhash, "issue_date": issue_date, "amount": amount,
                    "description": description, "section_name": section_name,
                    "registered_at": dt_cls.now().isoformat(timespec="seconds"),
                })
                ledger.add(rhash)
                logger.info(f"Registered: {issue_date} ¥{amount:,} / {description}")
            else:
                failed.append((rownum, "post_manual_journal 失敗"))
        except Exception as e:
            failed.append((rownum, f"例外 {type(e).__name__}: {e}"))

    if args.dry_run:
        print(f"DRY_RUN_ROWS: {len([r for r in rows if parse_amount(r.get('amount','0'), {'remove_chars': [',']}) > 0])}")
        return 0

    print(f"REGISTERED: {registered}")
    print(f"SKIPPED: {skipped}")
    print(f"FAILED: {len(failed)}")
    if failed:
        for rn, reason in failed:
            logger.error(f"  行{rn}: {reason}")
        print(
            "\n==NOTIFY==\n"
            f"❌ 売上記帳: {len(rows)}件中 {len(failed)}件 登録失敗"
            f"(成功 {registered}件 / skip {skipped}件)。\n"
            f"→ 原因を直したら **同じ review CSV をそのまま再実行**してください"
            f"(登録済みの行は冪等性台帳で自動 skip されるので二重記帳しません): {args.file}\n"
            "==END==\n"
        )
        return len(failed)

    # 成功したら Drive 原本を processed へ退避 + ローカル input/ を掃除(--no-archive で抑止)
    # ⚠️ ローカル input/ を残すと次回 generate が同じ CSV を再処理 → 二重記帳になる。
    # 全件 skip(registered=0/skipped>0)だけのケースも、過去に登録済みで input が残った
    # 残骸なので退避してよい(冪等性台帳が二重記帳を防ぐ)。
    if not failed and (registered > 0 or skipped > 0) and not args.no_archive:
        _archive_drive_inputs()
        _archive_local_inputs()
    return 0


def _archive_local_inputs():
    """登録済みのローカル input/*.csv を proceeded/{date}/ へ移動(再処理=二重記帳防止)。"""
    if not os.path.isdir(INPUT_DIR):
        return
    csvs = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".csv")]
    if not csvs:
        return
    dest = os.path.join(PROCEEDED_DIR, dt_cls.now().strftime("%Y%m%d"))
    ensure_directory(dest)
    for f in csvs:
        try:
            os.rename(os.path.join(INPUT_DIR, f), os.path.join(dest, f))
            logger.info(f"Archived local input: {f} → {dest}")
        except OSError as e:
            logger.error(f"local input 退避失敗 {f}: {e}")


def _archive_drive_inputs():
    if not DRIVE_FOLDER_ID:
        return
    drive = DriveClient()
    if not drive.service:
        return
    archive_date = dt_cls.now().strftime("%Y%m%d")
    files = drive.list_files_in_folder(DRIVE_FOLDER_ID)
    csvs = [f for f in files if f["name"].lower().endswith(".csv")
            and f["mimeType"] != "application/vnd.google-apps.folder"]
    processed_id = None
    for f in files:
        if f["name"] == "processed" and f["mimeType"] == "application/vnd.google-apps.folder":
            processed_id = f["id"]
            break
    if not processed_id:
        meta = {"name": "processed", "mimeType": "application/vnd.google-apps.folder",
                "parents": [DRIVE_FOLDER_ID]}
        processed_id = drive.service.files().create(body=meta, fields="id").execute().get("id")
    # 日付サブフォルダ
    date_id = None
    for df in drive.list_files_in_folder(processed_id):
        if df["name"] == archive_date and df["mimeType"] == "application/vnd.google-apps.folder":
            date_id = df["id"]
            break
    if not date_id:
        meta = {"name": archive_date, "mimeType": "application/vnd.google-apps.folder",
                "parents": [processed_id]}
        date_id = drive.service.files().create(body=meta, fields="id").execute().get("id")
    for f in csvs:
        logger.info(f"Archiving Drive file {f['name']} → processed/{archive_date}")
        drive.move_file(f["id"], DRIVE_FOLDER_ID, date_id)


def main():
    parser = argparse.ArgumentParser(description="finance importer — 売上CSV → Freee 振替伝票")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch")
    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--month", default=None,
                       help="入金月 YYYY-MM。指定すると取引日時に関係なく全行をその月末に起票(入金ベース)")
    p_ts = sub.add_parser("to-sheet")
    p_ts.add_argument("file")
    p_ts.add_argument("--tab", default=None)
    p_fs = sub.add_parser("from-sheet")
    p_fs.add_argument("tab")
    p_fs.add_argument("--out", default=None)
    p_reg = sub.add_parser("register")
    p_reg.add_argument("file")
    p_reg.add_argument("--dry-run", action="store_true")
    p_reg.add_argument("--no-archive", action="store_true")

    args = parser.parse_args()
    rc = 0
    if args.command == "fetch":
        rc = cmd_fetch(args)
    elif args.command == "generate":
        rc = cmd_generate(args)
    elif args.command == "to-sheet":
        rc = cmd_to_sheet(args)
    elif args.command == "from-sheet":
        rc = cmd_from_sheet(args)
    elif args.command == "register":
        rc = cmd_register(args)
    if rc:
        sys.exit(rc)


if __name__ == "__main__":
    main()
