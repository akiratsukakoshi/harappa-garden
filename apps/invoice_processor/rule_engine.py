import json
import os
from modules.freee_client import FreeeClient
from modules.utils import setup_logger

class RuleEngine:
    def __init__(self, freee_client: FreeeClient = None, config_path="apps/invoice_processor/mapping_config.json"):
        self.logger = setup_logger("RuleEngine")
        self.freee_client = freee_client
        self.partners = []
        self.account_items_cache = {}
        
        # Load Config for Section Rules
        # Load Config for Section Rules and Partner Rules
        self.sections = {}
        self.keyword_rules = {}
        self.partner_rules = {}
        self.account_rules = {}
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.sections = config.get('sections', {})
                self.keyword_rules = config.get('keyword_rules', {})
                self.partner_rules = config.get('partner_rules', {})
                self.account_rules = config.get('account_rules', {})
        else:
            self.logger.warning(f"Config file not found: {config_path}")

        # Account Item Heuristics
        # Priority: Partner Default > Specific Payee > Keywords > Default
        # Using loaded account_rules, falling back to a small default set if empty for safety
        if not self.account_rules:
             self.category_keywords = {
                # Restricted to 3 categories per user request: 外注費, 旅費交通費, 消耗品費
                # Default is "外注費" (implied if no match)
                "旅費交通費": ["タクシー", "交通", "JR", "鉄道", "航空", "ホテル", "宿泊", "出張", "電車", "バス"],
                "消耗品費": ["Amazon", "アスクル", "モノタロウ", "書店", "文具", "PC", "ソフト", "書籍", "本", "インク"],
                "外注費": ["委託", "報酬", "サービス", "代行", "制作", "開発", "デザイン"] # Explicit keywords for 外注費
            }
        else:
            self.category_keywords = self.account_rules
        
        # Pre-fetch data if client is available
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
        """
        抽出された支払先名を正規化する。
        Priority:
        1. Partner Rules (Dictionary Match) [Extracted Payee or Extra Text]
        2. Freee Partner List Exact Match
        3. Freee Partner List Substring Match
        """
        
        # Strategy 0: Partner Rules (Dictionary) - Extended Search
        # Check priority:
        # A. Extracted Payee matches Rule Key (Exact)
        if extracted_payee and extracted_payee in self.partner_rules:
            rule = self.partner_rules[extracted_payee]
            if isinstance(rule, dict) and 'name' in rule:
                return rule['name']

        # Search scope: Extracted Payee + Extra Text
        search_targets = [extracted_payee]
        if extra_text:
            search_targets.append(extra_text)

        # B. Rule Key contained in Extracted Payee or Extra Text
        for target in search_targets:
            if not target: continue
            for key, rule in self.partner_rules.items():
                if not isinstance(rule, dict): continue
                # Case insensitive search for key in target text
                # Ignore spaces for robust matching? User said "spaces doesn't matter"
                # Let's clean both
                clean_target = target.replace(" ", "").replace("　", "").lower()
                clean_key = key.replace(" ", "").replace("　", "").lower()
                
                if clean_key in clean_target:
                    return rule['name']
        
        if not self.partners or not extracted_payee:
            return extracted_payee

        best_match = None
        
        # Strategy 1: Exact Match (Case insensitive)
        for p in self.partners:
            if p['name'].lower() == extracted_payee.lower():
                return p['name']
        
        # Strategy 2: Substring Match
        for p in self.partners:
            p_name = p['name']
            if extracted_payee in p_name or p_name in extracted_payee:
                return p_name
                
        return extracted_payee

    def resolve_partner_id(self, payee_name: str) -> dict:
        """
        正規化された支払先名から partner_id と code を返す
        """
        if not payee_name or not self.partners:
            return {"id": None, "code": None}
        
        for p in self.partners:
            if p['name'] == payee_name:
                return {"id": p['id'], "code": p.get('code')}
        return {"id": None, "code": None}

    def fetch_taxes(self):
        try:
            self.taxes = self.freee_client.get_taxes()
            self.logger.info(f"Fetched {len(self.taxes)} taxes from Freee.")
        except Exception as e:
            self.logger.error(f"Failed to fetch taxes: {e}")
            self.taxes = []

    def get_preferred_tax_codes(self):
        """
        ユーザー指定の税区分のみを返す
        1. 課対仕入（控80）10％ -> purchase_with_tax_10_exempt_80
        2. 非課税仕入 -> non_taxable (2) or purchase_no_tax (37)?
           Here we assume 2 for "非課税". 
           If needed, we can list both or check naming.
        """
        preferred_names = [
            "purchase_with_tax_10_exempt_80", # 課対仕入（控80）10％
            "non_taxable", # 非課税
            "purchase_no_tax" # 対象外 (Just in case)
        ]
        
        filtered = []
        for t in self.taxes:
            # Check ID or Name
            # The API 'name' is often the English key (e.g. 'purchase_with_tax_10_exempt_80')
            # 'name_ja' might be available but we only see 'name' in logged output which looks like the key.
            # We match against the key content.
            if t['name'] in preferred_names:
                filtered.append((t['code'], t['name']))
        
        # If specific codes are known standard:
        # 189: purchase_with_tax_10_exempt_80
        # 2: non_taxable
        # We can also prioritize sorting.
        
        # Sort so 189 and 2 come first if present
        filtered.sort(key=lambda x: x[0])
        return filtered

    def get_tax_code_name(self, tax_code: int) -> str:
        for t in self.taxes:
            if t['code'] == tax_code:
                return t['name']
        return str(tax_code)

    def list_tax_codes(self):
        return [(t['code'], t['name']) for t in self.taxes]


    def guess_section(self, description: str) -> dict:
        """
        説明文から部門を推測する
        """
        if not description:
             return {"section_id": None, "section_name": None}
             
        # 1. Exact Name Match
        for name, id_val in self.sections.items():
            if name in description:
                return {"section_id": id_val, "section_name": name}
        
        # 2. Keyword Match
        for keyword, section_name in self.keyword_rules.items():
            if keyword in description:
                if section_name in self.sections:
                    return {"section_id": self.sections[section_name], "section_name": section_name}
        
        return {"section_id": None, "section_name": None}

    def infer_category(self, payee: str, description: str = "") -> dict:
        """
        支払先と説明文から勘定科目を推論する
        """
        result = {
            "account_item_id": None,
            "tax_code": 189, # default: 課対仕入（控80）10％ (purchase_with_tax_10_exempt_80)
            "account_item_name": "外注費" # Default changed from "雑費" per user request
        }
        
        # 1. Check Partner Default (Dictionary in Config)
        # Note: We loop through partner_rules to find if any rule matches the NORMALIZED payee name
        # However, self.partner_rules keys are usually the inputs. 
        # But if the payee is already normalized to "Amazon Japan G.K.", we might not find "Amazon" here directly unless we reverse lookup.
        # Ideally, we should check if the mapped name matches.
        
        detected_account = None
        
        # Check if the payee matches any defined rule (Key match or Name match)
        for key, rule in self.partner_rules.items():
            # Skip metadata keys like 'description'
            if not isinstance(rule, dict):
                continue
                
            # Check against the key (original keyword) or the normalized name in the rule
            if payee == key or payee == rule.get('name'):
                 detected_account = rule.get('account')
                 break
        
        if detected_account:
             result["account_item_name"] = detected_account
             if detected_account == "通信費":
                 result["tax_code"] = 21
             return result

        search_text = f"{payee} {description}"
        
        # 2. Check Keywords
        for category, keywords in self.category_keywords.items():
            for kw in keywords:
                if kw.lower() in search_text.lower():
                    result["account_item_name"] = category
                    # Set tax code based on category defaults if needed?
                    # For now keep 1.
                    if category == "通信費":
                         result["tax_code"] = 21 # リバースチャージ等の可能性 (Global typically)
                    return result

        return result

    def resolve_account_item_id(self, account_item_name: str) -> int:
        if not self.freee_client:
            return None
        
        # Check cache
        if account_item_name in self.account_items_cache:
            return self.account_items_cache[account_item_name]

        item_id = self.freee_client.get_account_items(account_item_name)
        if item_id:
            self.account_items_cache[account_item_name] = item_id
        return item_id
