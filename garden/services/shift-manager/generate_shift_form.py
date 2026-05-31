"""generate_shift_form.py - 翌月シフト募集フォームを生成する

HMC apps/shift_manager/logic/generate_shift_form.py から Garden 化。
変更点:
- パスを __file__ ベースの絶対パスに(cwd 非依存)
- credentials/token は SCRIPT_DIR/secrets/ 配下
- config は SCRIPT_DIR/config/ 配下
- 「ガクチョー」→「ガクチョ」(memory rule)
- それ以外のロジックは HMC 版と完全同一
"""

import sys
import os
import json
import gspread
from datetime import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from lib.utils import setup_logger

logger = setup_logger("GenerateShiftForm")

# Constants (Garden: 絶対パス化)
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "secrets", "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "secrets", "token.json")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "config_ids.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/forms.body",
]


class ShiftFormGenerator:
    def __init__(self):
        self.creds = self._authenticate()
        self.gd_client = gspread.authorize(self.creds)
        self.form_service = build("forms", "v1", credentials=self.creds)
        self.config = self._load_config()
        self.monthly_sh = self.gd_client.open_by_key(self.config["monthly_ui_id"])

    def _authenticate(self):
        if not os.path.exists(CREDENTIALS_PATH):
            logger.error(f"credentials not found: {CREDENTIALS_PATH}")
            sys.exit(1)
        creds = None
        try:
            with open(CREDENTIALS_PATH, "r") as f:
                data = json.load(f)
                if data.get("type") == "service_account":
                    creds = service_account.Credentials.from_service_account_file(
                        CREDENTIALS_PATH, scopes=SCOPES
                    )
        except Exception:
            pass
        if not creds:
            if os.path.exists(TOKEN_PATH):
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
        return creds

    def _load_config(self):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)

    def _save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)

    def generate(self, target_ym):
        logger.info(f"Generating Shift Form for {target_ym}...")

        # 1. Read Monthly Sheet
        try:
            ws = self.monthly_sh.worksheet(target_ym)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Sheet {target_ym} not found.")
            return

        raw_vals = ws.get_all_values()
        if len(raw_vals) < 2:
            return

        targets = []
        for row in raw_vals[1:]:
            if len(row) <= 16:
                continue

            chk = row[16].strip().upper()
            if chk == "TRUE":
                date = row[0]
                wd = row[1]
                loc = row[3]
                cat = row[4]
                cont = row[5]
                time_sch = row[6]

                label = f"{date} ({wd}) 【{loc}】{cat}: {cont} {time_sch}"
                targets.append(label)

        if not targets:
            logger.info("No events selected for recruitment.")
            return

        targets.append("全部NG")
        targets.append("むしろ全部OK")

        logger.info(f"Found {len(targets)} recruitment targets (including fixed options).")

        # 2. Get or Create Form
        form_id = self.config.get("shift_form_id")
        if not form_id:
            logger.info("Form ID not found in config. Creating new form...")
            form_info = {
                "info": {
                    "title": f"原っぱ大学 シフト希望調査 ({target_ym})",
                    "documentTitle": f"Shift Form {target_ym}",
                }
            }
            res = self.form_service.forms().create(body=form_info).execute()
            form_id = res["formId"]
            self.config["shift_form_id"] = form_id
            self._save_config()
            logger.info(f"Created Form ID: {form_id}")

        # 3. Update Form Content
        form_meta = self.form_service.forms().get(formId=form_id).execute()
        items = form_meta.get("items", [])

        requests = []

        indices_to_delete = list(range(len(items)))

        for idx in sorted(indices_to_delete, reverse=True):
            requests.append({"deleteItem": {"location": {"index": idx}}})

        name_question = {"question": {"required": True, "textQuestion": {}}}

        new_date_question = {
            "question": {
                "required": True,
                "choiceQuestion": {
                    "type": "CHECKBOX",
                    "options": [{"value": t} for t in targets],
                },
            }
        }

        requests.append(
            {
                "createItem": {
                    "item": {"title": "お名前", "questionItem": name_question},
                    "location": {"index": 0},
                }
            }
        )
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": "どれくらいシフトに入れますか？",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": "毎週"},
                                        {"value": "隔週"},
                                        {"value": "月1回程度"},
                                        {"value": "スタッフがいないときだけ"},
                                        {"value": "今月は入れません"},
                                    ],
                                },
                            }
                        },
                    },
                    "location": {"index": 1},
                }
            }
        )
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": "参加不可（NG）の日程",
                        "questionItem": new_date_question,
                    },
                    "location": {"index": 2},
                }
            }
        )
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": "連絡・相談したいことが何かあればご記入ください。",
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {"paragraph": True},
                            }
                        },
                    },
                    "location": {"index": 3},
                }
            }
        )
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": "ガクチョとの面談を希望する場合は希望するにチェックを入れてください",
                        "questionItem": {
                            "question": {
                                "required": False,
                                "choiceQuestion": {
                                    "type": "CHECKBOX",
                                    "options": [{"value": "希望する"}],
                                },
                            }
                        },
                    },
                    "location": {"index": 4},
                }
            }
        )

        y_int = int(target_ym.split("-")[0])
        m_int = int(target_ym.split("-")[1])
        title_str = f"{y_int}年{m_int}月原っぱ大学シフトアンケート"

        requests.append(
            {
                "updateFormInfo": {
                    "info": {"title": title_str},
                    "updateMask": "title",
                }
            }
        )

        if requests:
            logger.info(f"Sending Batch Update with {len(requests)} requests.")
            self.form_service.forms().batchUpdate(
                formId=form_id, body={"requests": requests}
            ).execute()
            logger.info("Form Updated.")

        form_res = self.form_service.forms().get(formId=form_id).execute()
        responder_uri = form_res.get("responderUri")
        logger.info(f"Form URL: {responder_uri}")
        print(f"Shift Form URL: {responder_uri}")
        return responder_uri


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=str, required=True, help="Target Month YYYY-MM")
    parser.add_argument("--form_id", type=str, help="Existing Form ID to use (updates config)")
    args = parser.parse_args()

    gen = ShiftFormGenerator()

    if args.form_id:
        gen.config["shift_form_id"] = args.form_id
        gen._save_config()
        logger.info(f"Config updated with Form ID: {args.form_id}")

    gen.generate(target_ym=args.month)
