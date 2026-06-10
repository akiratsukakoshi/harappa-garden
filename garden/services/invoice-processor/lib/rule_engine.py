"""rule_engine — 支払先正規化・部門/勘定科目推論(HMC apps/invoice_processor/rule_engine.py 移植)。

Garden 化の差分:
- import: modules.* → lib.*(同 service 内に集約)
- config パスをサービス相対の絶対パスに(cron で cwd 非依存)
- それ以外のロジック(partner_rules 辞書 → Freee 完全一致 → 部分一致、
  keyword → 部門、partner/keyword → 勘定科目、tax 既定 189)は HMC と完全同一
"""
import json
import os

from .freee_client import FreeeClient
from .utils import setup_logger

_SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(_SERVICE_DIR, "config", "mapping_config.json")


class RuleEngine:
    def __init__(self, freee_client: FreeeClient = None, config_path=DEFAULT_CONFIG_PATH):
        self.logger = setup_logger("RuleEngine")
        self.freee_client = freee_client
        self.partners = []
        self.account_items_cache = {}
        self.taxes = []

        self.sections = {}
        self.keyword_rules = {}
        self.partner_rules = {}
        self.account_rules = {}

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                self.sections = config.get("sections", {})
                self.keyword_rules = config.get("keyword_rules", {})
                self.partner_rules = config.get("partner_rules", {})
                self.account_rules = config.get("account_rules", {})
        else:
            self.logger.warning(f"Config file not found: {config_path}")

        if not self.account_rules:
            self.category_keywords = {
                "旅費交通費": ["タクシー", "交通", "JR", "鉄道", "航空", "ホテル", "宿泊", "出張", "電車", "バス"],
                "消耗品費": ["Amazon", "アスクル", "モノタロウ", "書店", "文具", "PC", "ソフト", "書籍", "本", "インク"],
                "外注費": ["委託", "報酬", "サービス", "代行", "制作", "開発", "デザイン"],
            }
        else:
            self.category_keywords = self.account_rules

        if self.freee_client:
            self.fetch_partners()
            self.fetch_taxes()

    def fetch_partners(self):
        try:
            self.partners = self.freee_client.get_partners()
            self.logger.info(f"Fetched {len(self.partners)} partners from Freee.")
        except Exception as e:
            self.logger.error(f"Failed to fetch partners: {e}")

    def normalize_payee(self, extracted_payee: str, extra_text: str = "") -> str:
        """抽出された支払先名を正規化する。

        Priority:
        1. Partner Rules (Dictionary Match) [Extracted Payee or Extra Text]
        2. Freee Partner List Exact Match
        3. Freee Partner List Substring Match
        """
        if extracted_payee and extracted_payee in self.partner_rules:
            rule = self.partner_rules[extracted_payee]
            if isinstance(rule, dict) and "name" in rule:
                return rule["name"]

        search_targets = [extracted_payee]
        if extra_text:
            search_targets.append(extra_text)

        for target in search_targets:
            if not target:
                continue
            for key, rule in self.partner_rules.items():
                if not isinstance(rule, dict):
                    continue
                clean_target = target.replace(" ", "").replace("　", "").lower()
                clean_key = key.replace(" ", "").replace("　", "").lower()
                if clean_key in clean_target:
                    return rule["name"]

        if not self.partners or not extracted_payee:
            return extracted_payee

        for p in self.partners:
            if p["name"].lower() == extracted_payee.lower():
                return p["name"]

        for p in self.partners:
            p_name = p["name"]
            if extracted_payee in p_name or p_name in extracted_payee:
                return p_name

        return extracted_payee

    def resolve_partner_id(self, payee_name: str) -> dict:
        """正規化された支払先名から partner_id と code を返す"""
        if not payee_name or not self.partners:
            return {"id": None, "code": None}
        for p in self.partners:
            if p["name"] == payee_name:
                return {"id": p["id"], "code": p.get("code")}
        return {"id": None, "code": None}

    def fetch_taxes(self):
        try:
            self.taxes = self.freee_client.get_taxes()
            self.logger.info(f"Fetched {len(self.taxes)} taxes from Freee.")
        except Exception as e:
            self.logger.error(f"Failed to fetch taxes: {e}")
            self.taxes = []

    def get_tax_code_name(self, tax_code: int) -> str:
        for t in self.taxes:
            if t["code"] == tax_code:
                return t["name"]
        return str(tax_code)

    def guess_section(self, description: str) -> dict:
        """説明文から部門を推測する"""
        if not description:
            return {"section_id": None, "section_name": None}

        for name, id_val in self.sections.items():
            if name in description:
                return {"section_id": id_val, "section_name": name}

        for keyword, section_name in self.keyword_rules.items():
            if keyword in description:
                if section_name in self.sections:
                    return {"section_id": self.sections[section_name], "section_name": section_name}

        return {"section_id": None, "section_name": None}

    def infer_category(self, payee: str, description: str = "") -> dict:
        """支払先と説明文から勘定科目を推論する"""
        result = {
            "account_item_id": None,
            "tax_code": 189,  # default: 課対仕入(控80)10% (purchase_with_tax_10_exempt_80)
            "account_item_name": "外注費",
        }

        detected_account = None
        for key, rule in self.partner_rules.items():
            if not isinstance(rule, dict):
                continue
            if payee == key or payee == rule.get("name"):
                detected_account = rule.get("account")
                break

        if detected_account:
            result["account_item_name"] = detected_account
            if detected_account == "通信費":
                result["tax_code"] = 21
            return result

        search_text = f"{payee} {description}"
        for category, keywords in self.category_keywords.items():
            if not isinstance(keywords, list):
                continue
            for kw in keywords:
                if kw.lower() in search_text.lower():
                    result["account_item_name"] = category
                    if category == "通信費":
                        result["tax_code"] = 21
                    return result

        return result

    def resolve_account_item_id(self, account_item_name: str):
        if not self.freee_client:
            return None
        if account_item_name in self.account_items_cache:
            return self.account_items_cache[account_item_name]
        item_id = self.freee_client.get_account_items(account_item_name)
        if item_id:
            self.account_items_cache[account_item_name] = item_id
        return item_id
