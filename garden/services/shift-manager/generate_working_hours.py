#!/usr/bin/env python3
"""generate_working_hours.py - 月次スタッフ別稼働時間集計シートを生成する

HMC apps/shift_manager/logic/generate_working_hours.py から Garden 化。
変更点:
- パスを __file__ ベースの絶対パスに(cwd 非依存)
- credentials/token は SCRIPT_DIR/secrets/ 配下
- config は SCRIPT_DIR/config/ 配下
- import: modules → lib
- それ以外のロジックは HMC 版と完全同一
"""

import sys
import os
import json
import re

import gspread
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from gspread_formatting import set_column_width

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from lib.utils import setup_logger
from lib.freee_client import FreeeClient

logger = setup_logger("WorkingHours")

CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "secrets", "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "secrets", "token.json")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "config_ids.json")
SECTION_MAPPING_PATH = os.path.join(SCRIPT_DIR, "config", "section_mapping.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SABORU_CATEGORY = "放サボ"
HOURLY_RATE = 1250
DEFAULT_PAYMENT_TYPE = "業務委託"

HOUR_ROLES = {
    "現場責任者": 8,
    "応急衛生": 9,
    "スタッフ": 10,
}

MARKER_ROLES = {
    "フォトグラファー": (11, "写真"),
    "調理": (12, "調理"),
}

PRESET_NICKNAMES = {
    "塚越暁": "ガクチョ",
    "和田祐司": "ゆーじ",
    "志村正太郎": "少佐",
}

COMPANY_KEYWORDS = [
    "株式会社", "合同会社", "有限会社", "一般社団", "公益社団",
    "NPO", "ＮＰＯ", "協会", "財団", "研究所", "学校", "大学",
    "Inc", "LLC", "Co.",
]


def col_letter(n: int) -> str:
    """0-based列インデックス → スプレッドシート列文字 (A, B, ..., Z, AA, ...)"""
    result = ""
    n += 1
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def parse_hours(time_str: str):
    if not time_str:
        return None
    s = time_str.strip()
    if s == "開催":
        return "開催"
    m = re.match(r"(\d{1,2}):(\d{2})\s*[-~〜]\s*(\d{1,2}):(\d{2})", s)
    if m:
        h1, m1, h2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        dur = (h2 + m2 / 60) - (h1 + m1 / 60)
        if dur < 0:
            dur += 24
        return round(dur * 4) / 4
    return None


def split_names(cell: str) -> list:
    if not cell or not cell.strip():
        return []
    parts = re.split(r"[,、]+", cell)
    return [p.strip() for p in parts if p.strip()]


class WorkingHoursGenerator:
    def __init__(self):
        self.creds = self._auth()
        self.gc = gspread.authorize(self.creds)
        with open(CONFIG_PATH) as f:
            self.config = json.load(f)
        self.monthly_sh = self.gc.open_by_key(self.config["monthly_ui_id"])
        self.db_sh = self.gc.open_by_key(self.config["backend_db_id"])
        self.nick_map = self._ensure_nickname_sheet()
        self.payment_type_map = self._load_payment_types()
        self.hourly_rate = self._load_hourly_rate()

    def _auth(self):
        creds = None
        try:
            with open(CREDENTIALS_PATH) as f:
                d = json.load(f)
                if d.get("type") == "service_account":
                    return service_account.Credentials.from_service_account_file(
                        CREDENTIALS_PATH, scopes=SCOPES
                    )
        except Exception:
            pass
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        return creds

    def _ensure_nickname_sheet(self) -> dict:
        try:
            ws = self.db_sh.worksheet("DB_Master_Nicknames")
            rows = ws.get_all_values()
            mapping = {}
            for r in rows[1:]:
                if len(r) < 2 or not r[0].strip() or not r[1].strip():
                    continue
                official_name = r[1].strip()
                for nick in re.split(r"[,、]+", r[0]):
                    nick = nick.strip()
                    if nick:
                        mapping[nick] = official_name
            logger.info(f"ニックネームマップ読み込み: {len(mapping)} 件")
            return mapping
        except gspread.exceptions.WorksheetNotFound:
            logger.info("DB_Master_Nicknames 未作成。Freeeから生成します...")
            return self._create_nickname_sheet()

    def _create_nickname_sheet(self) -> dict:
        ws = self.db_sh.add_worksheet("DB_Master_Nicknames", rows=200, cols=5)

        try:
            fc = FreeeClient()
            partners = fc.get_partners() or []
        except Exception as e:
            logger.warning(f"Freee取得失敗: {e}")
            partners = []

        individuals = []
        for p in partners:
            if not p.get("available", True):
                continue
            name = p.get("name", "").strip()
            if not name:
                continue
            if any(kw in name for kw in COMPANY_KEYWORDS):
                continue
            individuals.append({"name": name, "id": p.get("id", "")})

        individuals.sort(key=lambda x: x["name"])

        headers = ["ニックネーム", "正式名称", "Freee_ID", "備考"]
        data_rows = []
        preset_map = {}

        for ind in individuals:
            nick = PRESET_NICKNAMES.get(ind["name"], "")
            if nick:
                preset_map[nick] = ind["name"]
            data_rows.append([nick, ind["name"], str(ind["id"]), ""])

        ws.update(range_name="A1", values=[headers] + data_rows)

        ws.spreadsheet.batch_update({"requests": [{
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.73, "green": 0.85, "blue": 0.98},
                    "textFormat": {"bold": True},
                }},
                "fields": "userEnteredFormat",
            }
        }]})

        db_url = f"https://docs.google.com/spreadsheets/d/{self.config['backend_db_id']}/edit"
        logger.info(f"DB_Master_Nicknames 作成完了: {len(data_rows)} 件")
        print(f"✓ ニックネーム照合テーブル作成: DB_Master_Nicknames ({len(data_rows)} 名)")
        print(f"  → ニックネーム列を入力してください: {db_url}")

        return preset_map

    def _resolve(self, nick: str) -> str:
        return self.nick_map.get(nick, nick)

    def _load_payment_types(self) -> dict:
        try:
            ws = self.db_sh.worksheet("DB_Master_Nicknames")
            rows = ws.get_all_values()
            if not rows or len(rows[0]) < 5:
                logger.warning("DB_Master_NicknamesにPaymentType列(E列)がありません。デフォルト値を使用します。")
                return {}
            mapping = {}
            for r in rows[1:]:
                if len(r) < 5 or not r[1].strip():
                    continue
                official_name = r[1].strip()
                ptype = r[4].strip()
                if ptype:
                    mapping[official_name] = ptype
            logger.info(f"PaymentType読み込み: {len(mapping)} 件")
            return mapping
        except Exception as e:
            logger.warning(f"PaymentType読み込み失敗: {e}")
            return {}

    def _load_hourly_rate(self) -> int:
        try:
            with open(SECTION_MAPPING_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("hourly_rate", HOURLY_RATE))
        except Exception:
            return HOURLY_RATE

    def _get_or_create_output_sh(self, output_id: str = ""):
        if output_id:
            sh = self.gc.open_by_key(output_id)
            self.config["working_hours_id"] = output_id
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"出力先を設定: {output_id}")
            return sh

        wh_id = self.config.get("working_hours_id", "")
        if wh_id:
            try:
                return self.gc.open_by_key(wh_id)
            except Exception:
                logger.warning(f"working_hours_id ({wh_id}) が開けません。新規作成を試みます。")

        try:
            sh = self.gc.create("HARAPPA スタッフ別稼働時間")
        except gspread.exceptions.APIError as e:
            if "quota" in str(e).lower() or "403" in str(e):
                print("\n[エラー] Googleドライブの容量が上限に達しているため新規スプレッドシートを作成できません。")
                print("以下のいずれかを行ってください:")
                print("  1. Googleドライブの不要ファイルを削除して容量を確保する")
                print("  2. 既存のスプレッドシートのIDを --output-id オプションで指定する")
            raise

        self.config["working_hours_id"] = sh.id
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        logger.info(f"稼働時間スプレッドシート新規作成: {sh.id}")
        print(f"✓ 新規スプレッドシート作成: https://docs.google.com/spreadsheets/d/{sh.id}/edit")
        return sh

    def _has_saboru_data(self, raw: list) -> bool:
        """既存タブの「放サボ列の日付セル」に人手入力 or import 済みデータがあるか判定。

        S27 既存タブガード用。「放サボ計」「放サボ額」のような集計列(数式入り)は対象外で、
        header_row が "M/D" 形式の日付ラベルになっている列だけを人手データ列とみなす。
        import_kodomon.py の saboru_cols 抽出ロジックと同じ前提。
        """
        if len(raw) < 4:
            return False
        header_row = raw[1]
        cat_row = raw[2]
        saboru_cols = [i for i, lbl in enumerate(cat_row) if lbl.strip() == SABORU_CATEGORY]
        if not saboru_cols:
            return False
        date_cols = []
        for c in saboru_cols:
            if c < len(header_row) and re.match(r"^\d{1,2}/\d{1,2}$", header_row[c].strip()):
                date_cols.append(c)
        if not date_cols:
            return False
        for row in raw[3:]:
            for c in date_cols:
                if c < len(row) and row[c].strip():
                    return True
        return False

    def generate(self, target_ym: str, output_id: str = "", force_regenerate: bool = False):
        year, month = map(int, target_ym.split("-"))

        # S27 既存タブガード: 上書きで放サボ列が消える事故([S27 inspection](../../../docs/sessions/2026-06-02-session27.md))
        # を構造的に防ぐ。force_regenerate なしで既存タブに放サボ日付セルのデータがあれば中断。
        if not force_regenerate:
            sheet_title_check = f"{target_ym}_稼働時間"
            try:
                tentative_sh = self._get_or_create_output_sh(output_id)
                existing_ws = tentative_sh.worksheet(sheet_title_check)
                existing_data = existing_ws.get_all_values()
                if self._has_saboru_data(existing_data):
                    logger.error(
                        f"既存タブ {sheet_title_check} に放サボ列のデータあり → 上書き防止のため中断。"
                        f"再生成するなら --force-regenerate を付けて実行してください。"
                    )
                    return None
                logger.warning(f"既存タブ {sheet_title_check} 検出(放サボ列は空)→ 再生成続行")
            except gspread.exceptions.WorksheetNotFound:
                pass  # 未生成、通常通り進む
            except Exception as e:
                logger.warning(f"既存タブガードチェック失敗(続行): {e}")

        ws_src = self.monthly_sh.worksheet(target_ym)
        raw = ws_src.get_all_values()
        if not raw or len(raw) < 2:
            logger.error("月次シートにデータがありません。")
            return None

        events = []
        for row in raw[1:]:
            if len(row) < 13:
                continue
            date_label = row[0].strip()
            category = row[4].strip()
            time_str = row[6].strip()
            is_saboru = category == SABORU_CATEGORY

            if not category and not time_str:
                continue

            # 放サボイベントは時間空でも events に入れる(import_kodomon.py が CSV から書き込む前提、S24)
            if is_saboru:
                hours_result = None
                auto_hours = None
            else:
                hours_result = parse_hours(time_str)
                if hours_result is None:
                    continue
                if hours_result == "開催":
                    auto_hours = None
                else:
                    auto_hours = hours_result / 24

            hour_staff = set()
            for role, idx in HOUR_ROLES.items():
                if idx < len(row):
                    hour_staff.update(split_names(row[idx]))

            marker_staff = {}
            for role, (idx, label) in MARKER_ROLES.items():
                if idx < len(row):
                    for nick in split_names(row[idx]):
                        if nick not in marker_staff:
                            marker_staff[nick] = label

            all_staff = hour_staff | set(marker_staff.keys())
            if not all_staff:
                continue

            date_disp = re.sub(r"(\d+)月(\d+)日", r"\1/\2", date_label)

            events.append({
                "date_disp": date_disp,
                "category": category,
                "auto_hours": auto_hours,
                "is_saboru": is_saboru,
                "hour_staff": hour_staff,
                "marker_staff": marker_staff,
            })

        if not events:
            logger.error("集計対象イベントが見つかりません。")
            return None

        all_nicks_set = set()
        for ev in events:
            all_nicks_set.update(ev["hour_staff"] | set(ev["marker_staff"].keys()))
        all_nicks = sorted(all_nicks_set, key=self._resolve)

        ev_cats = []
        seen_cats = set()
        for ev in events:
            if ev["category"] not in seen_cats:
                ev_cats.append(ev["category"])
                seen_cats.add(ev["category"])

        n_ev = len(events)
        n_cats = len(ev_cats)
        n_staff = len(all_nicks)

        first_ev_col = col_letter(1)
        last_ev_col = col_letter(n_ev)
        total_hours_col_idx = n_ev + n_cats + 1
        amount_start_col_idx = n_ev + n_cats + 2
        total_amount_col_idx = n_ev + 2 * n_cats + 2
        payment_type_col_idx = n_ev + 2 * n_cats + 3

        def cat_col(i):
            return col_letter(n_ev + 1 + i)

        def amount_col(i):
            return col_letter(amount_start_col_idx + i)

        n_extra_cols = n_cats + 2
        title_row = [f"{year}年{month}月 スタッフ別稼働時間"] + [""] * (n_ev + n_cats + 1 + n_extra_cols)

        header_row = ["スタッフ名"]
        for ev in events:
            header_row.append(ev["date_disp"])
        for cat in ev_cats:
            header_row.append(f"{cat}計")
        header_row.append("合計")
        for cat in ev_cats:
            header_row.append(f"{cat}額")
        header_row.append("合計額")
        header_row.append("区分")

        cat_label_row = [""]
        for ev in events:
            cat_label_row.append(ev["category"])
        for cat in ev_cats:
            cat_label_row.append(cat)
        cat_label_row.append("")
        for cat in ev_cats:
            cat_label_row.append(cat)
        cat_label_row.append("")
        cat_label_row.append("")

        data_rows = []
        saboru_cells = []

        for i, nick in enumerate(all_nicks):
            staff_row_num = 4 + i
            row = [self._resolve(nick)]

            for j, ev in enumerate(events):
                col_i = j + 1
                if nick in ev["hour_staff"]:
                    if ev["auto_hours"] is not None:
                        row.append(ev["auto_hours"])
                    else:
                        row.append("")
                        saboru_cells.append((i, col_i))
                elif nick in ev["marker_staff"]:
                    row.append(ev["marker_staff"][nick])
                else:
                    row.append("")

            for j in range(n_cats):
                cc = cat_col(j)
                formula = (
                    f"=SUMPRODUCT(({first_ev_col}$3:{last_ev_col}$3={cc}$3)"
                    f"*N(IFERROR({first_ev_col}{staff_row_num}:{last_ev_col}{staff_row_num},0)))"
                )
                row.append(formula)

            row.append(f"=SUM({first_ev_col}{staff_row_num}:{last_ev_col}{staff_row_num})")

            for j in range(n_cats):
                tc = cat_col(j)
                row.append(f"=ROUND({tc}{staff_row_num}*24*{self.hourly_rate},0)")

            amount_first_col = amount_col(0)
            amount_last_col = amount_col(n_cats - 1)
            row.append(f"=SUM({amount_first_col}{staff_row_num}:{amount_last_col}{staff_row_num})")

            official_name = self._resolve(nick)
            ptype = self.payment_type_map.get(official_name, DEFAULT_PAYMENT_TYPE)
            row.append(ptype)

            data_rows.append(row)

        out_sh = self._get_or_create_output_sh(output_id)
        sheet_title = f"{target_ym}_稼働時間"

        try:
            ws_out = out_sh.worksheet(sheet_title)
            ws_out.clear()
            logger.info(f"既存シートをクリア: {sheet_title}")
        except gspread.exceptions.WorksheetNotFound:
            ws_out = out_sh.add_worksheet(
                sheet_title, rows=n_staff + 10, cols=n_ev + 2 * n_cats + 6
            )
            for default_title in ("シート1", "Sheet1"):
                try:
                    out_sh.del_worksheet(out_sh.worksheet(default_title))
                except Exception:
                    pass
            logger.info(f"新規シート作成: {sheet_title}")

        ws_out.update(
            range_name="A1",
            values=[title_row, header_row, cat_label_row],
            value_input_option="RAW",
        )
        if data_rows:
            ws_out.update(
                range_name="A4",
                values=data_rows,
                value_input_option="USER_ENTERED",
            )

        self._format_sheet(ws_out, n_staff, n_ev, n_cats, saboru_cells)

        wh_id = self.config["working_hours_id"]
        url = f"https://docs.google.com/spreadsheets/d/{wh_id}/edit#gid={ws_out.id}"
        logger.info(f"生成完了: {sheet_title}")
        return url

    def _format_sheet(self, ws, n_staff, n_ev, n_cats, saboru_cells):
        sid = ws.id
        total_cols = n_ev + 2 * n_cats + 4
        amount_start = n_ev + n_cats + 2
        total_amount_col = n_ev + 2 * n_cats + 2
        payment_type_col = n_ev + 2 * n_cats + 3
        requests = []

        requests.append({"mergeCells": {
            "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": total_cols},
            "mergeType": "MERGE_ALL",
        }})
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": total_cols},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.27, "green": 0.51, "blue": 0.71},
                "textFormat": {
                    "bold": True, "fontSize": 13,
                    "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                },
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
            }},
            "fields": "userEnteredFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 2,
                      "startColumnIndex": 0, "endColumnIndex": total_cols},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.73, "green": 0.85, "blue": 0.98},
                "textFormat": {"bold": True},
                "horizontalAlignment": "CENTER",
            }},
            "fields": "userEnteredFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 2, "endRowIndex": 3,
                      "startColumnIndex": 0, "endColumnIndex": total_cols},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93},
                "textFormat": {"italic": True, "fontSize": 9},
                "horizontalAlignment": "CENTER",
            }},
            "fields": "userEnteredFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": 1, "endColumnIndex": amount_start},
            "cell": {"userEnteredFormat": {
                "horizontalAlignment": "CENTER",
                "numberFormat": {"type": "TIME", "pattern": "[h]:mm;;@"},
            }},
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": amount_start, "endColumnIndex": payment_type_col},
            "cell": {"userEnteredFormat": {
                "horizontalAlignment": "RIGHT",
                "numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0;¥-#,##0;"},
            }},
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": payment_type_col, "endColumnIndex": payment_type_col + 1},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat.horizontalAlignment",
        }})

        if n_cats > 0:
            requests.append({"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                          "startColumnIndex": n_ev + 1, "endColumnIndex": n_ev + 1 + n_cats},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 1.0, "green": 0.97, "blue": 0.82},
                }},
                "fields": "userEnteredFormat.backgroundColor",
            }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": n_ev + 1 + n_cats, "endColumnIndex": n_ev + 2 + n_cats},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.85, "green": 0.93, "blue": 0.83},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat",
        }})

        if n_cats > 0:
            requests.append({"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                          "startColumnIndex": amount_start, "endColumnIndex": amount_start + n_cats},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.85, "green": 0.93, "blue": 0.98},
                }},
                "fields": "userEnteredFormat.backgroundColor",
            }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": total_amount_col, "endColumnIndex": total_amount_col + 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.71, "green": 0.84, "blue": 0.66},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat",
        }})

        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": payment_type_col, "endColumnIndex": payment_type_col + 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
            }},
            "fields": "userEnteredFormat.backgroundColor",
        }})

        for staff_i, col_i in saboru_cells:
            row_i = 3 + staff_i
            requests.append({"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": row_i, "endRowIndex": row_i + 1,
                          "startColumnIndex": col_i, "endColumnIndex": col_i + 1},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 1.0, "green": 0.90, "blue": 0.74},
                }},
                "fields": "userEnteredFormat.backgroundColor",
            }})

        requests.append({"updateSheetProperties": {
            "properties": {
                "sheetId": sid,
                "gridProperties": {"frozenRowCount": 3, "frozenColumnCount": 0},
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }})

        ws.spreadsheet.batch_update({"requests": requests})

        set_column_width(ws, "A", 110)
        for i in range(n_ev):
            set_column_width(ws, col_letter(i + 1), 55)
        for i in range(n_cats):
            set_column_width(ws, col_letter(n_ev + 1 + i), 85)
        set_column_width(ws, col_letter(n_ev + 1 + n_cats), 70)
        for i in range(n_cats):
            set_column_width(ws, col_letter(amount_start + i), 90)
        set_column_width(ws, col_letter(total_amount_col), 90)
        set_column_width(ws, col_letter(payment_type_col), 75)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="スタッフ別月次稼働時間集計シートを生成する")
    parser.add_argument("--month", required=True, help="対象月 YYYY-MM")
    parser.add_argument("--output-id", default="", help="出力先スプレッドシートのID (省略時は自動作成または設定済みIDを使用)")
    parser.add_argument("--force-regenerate", action="store_true",
                        help="既存タブに放サボ列データがあっても強制再生成(default: ガード ON)")
    args = parser.parse_args()

    gen = WorkingHoursGenerator()
    url = gen.generate(args.month, output_id=args.output_id, force_regenerate=args.force_regenerate)
    if url:
        print(f"✓ 完了: {url}")
    else:
        # S27 既存タブガードで中断、または別エラー
        sys.exit(1)
