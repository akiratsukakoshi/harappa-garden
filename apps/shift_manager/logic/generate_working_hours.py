#!/usr/bin/env python3
"""generate_working_hours.py - 月次スタッフ別稼働時間集計シートを生成する"""

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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from modules.utils import setup_logger
from modules.freee_client import FreeeClient

logger = setup_logger("WorkingHours")

CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.json"
CONFIG_PATH = "apps/shift_manager/config_ids.json"
SECTION_MAPPING_PATH = "apps/shift_manager/section_mapping.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SABORU_CATEGORY = "放サボ"
HOURLY_RATE = 1250  # 時給単価（円）- section_mapping.jsonで上書き可能
DEFAULT_PAYMENT_TYPE = "業務委託"  # PaymentType未登録時のデフォルト

# 稼働時間を集計する役割列 (月次シートの0-based列インデックス)
HOUR_ROLES = {
    "現場責任者": 8,
    "応急衛生": 9,
    "スタッフ": 10,
}

# 「稼働」マーカーのみ表示する役割列 → {役割名: (列インデックス, 表示テキスト)}
MARKER_ROLES = {
    "フォトグラファー": (11, "写真"),
    "調理": (12, "調理"),
}

# Freee正式名称 → 事前入力するニックネーム
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
    """
    "HH:MM-HH:MM" → float (15分刻みで丸め)
    "開催" → "開催"
    それ以外 → None
    """
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
        return round(dur * 4) / 4  # 15分単位
    return None


def split_names(cell: str) -> list:
    """カンマ区切りのニックネームを分割して返す"""
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
        self.nick_map = self._ensure_nickname_sheet()  # {ニックネーム: 正式名称}
        self.payment_type_map = self._load_payment_types()  # {正式名称: 給与/業務委託/追加}
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

    # ── ニックネームシート管理 ───────────────────────────────────

    def _ensure_nickname_sheet(self) -> dict:
        """DB_Master_Nicknamesシートを読み込む。なければFreeeから作成する。
        ニックネーム列はカンマ区切りで複数表記に対応 (例: 'ゆーじ, ユージ')。
        返り値: {ニックネーム各表記: 正式名称}
        """
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
        """FreeeパートナーマスタからDB_Master_Nicknamesシートを作成する。"""
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
        """ニックネーム → 正式名称 (未登録の場合はニックネームをそのまま返す)"""
        return self.nick_map.get(nick, nick)

    def _load_payment_types(self) -> dict:
        """DB_Master_NicknamesからPaymentType (給与/業務委託/追加) を読み込む。
        正式名称 → PaymentType の辞書を返す。"""
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
        """section_mapping.jsonから時給単価を読み込む。未設定時はHOURLY_RATE定数を使用。"""
        try:
            with open(SECTION_MAPPING_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("hourly_rate", HOURLY_RATE))
        except Exception:
            return HOURLY_RATE

    # ── 出力スプレッドシート管理 ────────────────────────────────

    def _get_or_create_output_sh(self, output_id: str = ""):
        """稼働時間専用スプレッドシートを取得または新規作成する。
        output_id が指定された場合はそのシートを使い、config に保存する。
        """
        # 引数で明示指定された場合は優先して使用・保存
        if output_id:
            sh = self.gc.open_by_key(output_id)
            self.config["working_hours_id"] = output_id
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"出力先を設定: {output_id}")
            return sh

        # config に保存済みの場合
        wh_id = self.config.get("working_hours_id", "")
        if wh_id:
            try:
                return self.gc.open_by_key(wh_id)
            except Exception:
                logger.warning(f"working_hours_id ({wh_id}) が開けません。新規作成を試みます。")

        # 新規作成
        try:
            sh = self.gc.create("HARAPPA スタッフ別稼働時間")
        except gspread.exceptions.APIError as e:
            if "quota" in str(e).lower() or "403" in str(e):
                print("\n[エラー] Googleドライブの容量が上限に達しているため新規スプレッドシートを作成できません。")
                print("以下のいずれかを行ってください:")
                print("  1. Googleドライブの不要ファイルを削除して容量を確保する")
                print("  2. 既存のスプレッドシートのIDを --output-id オプションで指定する")
                print("     例: python generate_working_hours.py --month 2026-04 --output-id <SPREADSHEET_ID>")
            raise

        self.config["working_hours_id"] = sh.id
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        logger.info(f"稼働時間スプレッドシート新規作成: {sh.id}")
        print(f"✓ 新規スプレッドシート作成: https://docs.google.com/spreadsheets/d/{sh.id}/edit")
        return sh

    # ── 稼働時間シート生成 ──────────────────────────────────────

    def generate(self, target_ym: str, output_id: str = ""):
        year, month = map(int, target_ym.split("-"))

        ws_src = self.monthly_sh.worksheet(target_ym)
        raw = ws_src.get_all_values()
        if not raw or len(raw) < 2:
            logger.error("月次シートにデータがありません。")
            return None

        # 集計対象イベントの抽出
        events = []
        for row in raw[1:]:
            if len(row) < 13:
                continue
            date_label = row[0].strip()
            category = row[4].strip()
            time_str = row[6].strip()

            if not category and not time_str:
                continue

            hours_result = parse_hours(time_str)
            if hours_result is None:
                continue  # 時間なし → スキップ

            is_saboru = category == SABORU_CATEGORY
            # 時間は「1日=1」単位で保存 → Googleスプレッドシートの時刻フォーマットと互換
            if is_saboru or hours_result == "開催":
                auto_hours = None  # 手入力
            else:
                auto_hours = hours_result / 24  # 小数時間 → 日分率

            hour_staff = set()
            for role, idx in HOUR_ROLES.items():
                if idx < len(row):
                    hour_staff.update(split_names(row[idx]))

            # marker_staff: {ニックネーム: 表示テキスト}
            marker_staff = {}
            for role, (idx, label) in MARKER_ROLES.items():
                if idx < len(row):
                    for nick in split_names(row[idx]):
                        if nick not in marker_staff:  # 複数役割の場合は先勝ち
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
                "marker_staff": marker_staff,  # {nick: label}
            })

        if not events:
            logger.error("集計対象イベントが見つかりません。")
            return None

        # スタッフ一覧（正式名称順でソート）
        all_nicks_set = set()
        for ev in events:
            all_nicks_set.update(ev["hour_staff"] | set(ev["marker_staff"].keys()))
        all_nicks = sorted(all_nicks_set, key=self._resolve)

        # イベント別カテゴリ（出現順）
        ev_cats = []
        seen_cats = set()
        for ev in events:
            if ev["category"] not in seen_cats:
                ev_cats.append(ev["category"])
                seen_cats.add(ev["category"])

        n_ev = len(events)
        n_cats = len(ev_cats)
        n_staff = len(all_nicks)

        # 列レイアウト:
        # col 0 (A): スタッフ名
        # col 1..n_ev (B..): イベント別日付列
        # col n_ev+1..n_ev+n_cats: カテゴリ別時間小計
        # col n_ev+n_cats+1: 合計時間
        # col n_ev+n_cats+2..n_ev+2*n_cats+1: カテゴリ別金額
        # col n_ev+2*n_cats+2: 合計金額
        # col n_ev+2*n_cats+3: PaymentType (給与/業務委託/追加)

        first_ev_col = col_letter(1)
        last_ev_col = col_letter(n_ev)
        total_hours_col_idx = n_ev + n_cats + 1
        amount_start_col_idx = n_ev + n_cats + 2
        total_amount_col_idx = n_ev + 2 * n_cats + 2
        payment_type_col_idx = n_ev + 2 * n_cats + 3

        def cat_col(i):
            """カテゴリ別時間小計列のスプレッドシート列文字"""
            return col_letter(n_ev + 1 + i)

        def amount_col(i):
            """カテゴリ別金額列のスプレッドシート列文字"""
            return col_letter(amount_start_col_idx + i)

        # ── データ行生成 ──

        n_extra_cols = n_cats + 2  # 金額カテゴリ列 + 合計金額 + PaymentType
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
        saboru_cells = []  # (staff_i, col_i) 放サボ手入力セルの位置

        for i, nick in enumerate(all_nicks):
            staff_row_num = 4 + i  # スプレッドシート上の行番号 (1-indexed)
            row = [self._resolve(nick)]

            for j, ev in enumerate(events):
                col_i = j + 1  # 0-based
                if nick in ev["hour_staff"]:
                    if ev["auto_hours"] is not None:
                        row.append(ev["auto_hours"])
                    else:
                        row.append("")  # 放サボ or 開催 → 手入力
                        saboru_cells.append((i, col_i))
                elif nick in ev["marker_staff"]:
                    row.append(ev["marker_staff"][nick])  # "写真" or "調理"
                else:
                    row.append("")

            # カテゴリ別時間小計 (SUMPRODUCT)
            for j in range(n_cats):
                cc = cat_col(j)
                formula = (
                    f"=SUMPRODUCT(({first_ev_col}$3:{last_ev_col}$3={cc}$3)"
                    f"*N(IFERROR({first_ev_col}{staff_row_num}:{last_ev_col}{staff_row_num},0)))"
                )
                row.append(formula)

            # 全体合計時間
            row.append(f"=SUM({first_ev_col}{staff_row_num}:{last_ev_col}{staff_row_num})")

            # カテゴリ別金額: 時間(日分率) × 24 × 時給, 四捨五入
            for j in range(n_cats):
                tc = cat_col(j)
                row.append(f"=ROUND({tc}{staff_row_num}*24*{self.hourly_rate},0)")

            # 合計金額
            amount_first_col = amount_col(0)
            amount_last_col = amount_col(n_cats - 1)
            row.append(f"=SUM({amount_first_col}{staff_row_num}:{amount_last_col}{staff_row_num})")

            # PaymentType (区分)
            official_name = self._resolve(nick)
            ptype = self.payment_type_map.get(official_name, DEFAULT_PAYMENT_TYPE)
            row.append(ptype)

            data_rows.append(row)

        # ── 出力先シートの準備 ──

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
            # 新規スプレッドシート作成時のデフォルトシートを削除
            for default_title in ("シート1", "Sheet1"):
                try:
                    out_sh.del_worksheet(out_sh.worksheet(default_title))
                except Exception:
                    pass
            logger.info(f"新規シート作成: {sheet_title}")

        # ヘッダー行はRAWで書く（"4/2"が日付数値に変換されるのを防ぐ）
        ws_out.update(
            range_name="A1",
            values=[title_row, header_row, cat_label_row],
            value_input_option="RAW",
        )
        # データ行はUSER_ENTEREDで書く（数式を有効化）
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
        total_cols = n_ev + 2 * n_cats + 4  # name + dates + cat_hours + total_hours + cat_amounts + total_amount + payment_type
        amount_start = n_ev + n_cats + 2
        total_amount_col = n_ev + 2 * n_cats + 2
        payment_type_col = n_ev + 2 * n_cats + 3
        requests = []

        # Row 1: タイトル (結合・濃い青・白字)
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

        # Row 2: ヘッダー (薄い青・太字)
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

        # Row 3: カテゴリラベル (薄いグレー・イタリック・小さめ)
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

        # スタッフ名列 (A, rows 4+): 太字
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat",
        }})

        # 時間データセル (B〜V列): 中央揃え + 時刻フォーマット [h]:mm
        # パターン "[h]:mm;;@" → 数値は「時間:分」表示、ゼロは非表示、テキスト("写真"等)はそのまま
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": 1, "endColumnIndex": amount_start},
            "cell": {"userEnteredFormat": {
                "horizontalAlignment": "CENTER",
                "numberFormat": {"type": "TIME", "pattern": "[h]:mm;;@"},
            }},
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat",
        }})

        # 金額データセル (W〜AC列): 右寄せ + 通貨フォーマット
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": amount_start, "endColumnIndex": payment_type_col},
            "cell": {"userEnteredFormat": {
                "horizontalAlignment": "RIGHT",
                "numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0;¥-#,##0;"},
            }},
            "fields": "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat",
        }})

        # PaymentType列 (AD): 中央揃え
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 3, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": payment_type_col, "endColumnIndex": payment_type_col + 1},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat.horizontalAlignment",
        }})

        # カテゴリ別時間小計列: 薄い黄色
        if n_cats > 0:
            requests.append({"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                          "startColumnIndex": n_ev + 1, "endColumnIndex": n_ev + 1 + n_cats},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 1.0, "green": 0.97, "blue": 0.82},
                }},
                "fields": "userEnteredFormat.backgroundColor",
            }})

        # 合計時間列: 薄い緑・太字
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": n_ev + 1 + n_cats, "endColumnIndex": n_ev + 2 + n_cats},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.85, "green": 0.93, "blue": 0.83},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat",
        }})

        # カテゴリ別金額列: 薄い水色
        if n_cats > 0:
            requests.append({"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                          "startColumnIndex": amount_start, "endColumnIndex": amount_start + n_cats},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.85, "green": 0.93, "blue": 0.98},
                }},
                "fields": "userEnteredFormat.backgroundColor",
            }})

        # 合計金額列 (AC): 濃い緑・太字
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": total_amount_col, "endColumnIndex": total_amount_col + 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.71, "green": 0.84, "blue": 0.66},
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat",
        }})

        # PaymentType列 (AD): 灰色
        requests.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": 3 + n_staff,
                      "startColumnIndex": payment_type_col, "endColumnIndex": payment_type_col + 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95},
            }},
            "fields": "userEnteredFormat.backgroundColor",
        }})

        # 放サボ手入力セル: 薄いオレンジ
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

        # 先頭3行を固定
        requests.append({"updateSheetProperties": {
            "properties": {
                "sheetId": sid,
                "gridProperties": {"frozenRowCount": 3, "frozenColumnCount": 0},
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }})

        ws.spreadsheet.batch_update({"requests": requests})

        # 列幅
        set_column_width(ws, "A", 110)
        for i in range(n_ev):
            set_column_width(ws, col_letter(i + 1), 55)
        # カテゴリ別時間小計列
        for i in range(n_cats):
            set_column_width(ws, col_letter(n_ev + 1 + i), 85)
        # 合計時間列
        set_column_width(ws, col_letter(n_ev + 1 + n_cats), 70)
        # カテゴリ別金額列
        for i in range(n_cats):
            set_column_width(ws, col_letter(amount_start + i), 90)
        # 合計金額列
        set_column_width(ws, col_letter(total_amount_col), 90)
        # PaymentType列
        set_column_width(ws, col_letter(payment_type_col), 75)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="スタッフ別月次稼働時間集計シートを生成する")
    parser.add_argument("--month", required=True, help="対象月 YYYY-MM")
    parser.add_argument("--output-id", default="", help="出力先スプレッドシートのID (省略時は自動作成または設定済みIDを使用)")
    args = parser.parse_args()

    gen = WorkingHoursGenerator()
    url = gen.generate(args.month, output_id=args.output_id)
    if url:
        print(f"✓ 完了: {url}")
