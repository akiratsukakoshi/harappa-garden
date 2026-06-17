"""section_guesser — 部門推定(Garden 版 = ルールのみ、Gemini 依存なし)

HMC apps/finance_importer/section_guesser.py からの差分(ガクチョ S47 決定):
- HMC は 1)完全一致 → 2)keyword rule → 3)Gemini CLI 推測 の3段。
- Garden は **1)+2) のルールのみ**。当たらなければ None を返し、ガクチョが
  レビュー(Sheets)で部門を埋める。AI 推測の当て勘より、ガクチョの剪定に委ねる。
  (合言葉「塚越さんが著者、Garden が整形者」/ 財務は特に勝手に推定しない)

config は同 service の config/mapping_config.json を既定参照。
"""
import json
import logging
import os

logger = logging.getLogger("SectionGuesser")

_DEFAULT_CONFIG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "config", "mapping_config.json"
)


class SectionGuesser:
    def __init__(self, config_path=None):
        config_path = config_path or _DEFAULT_CONFIG
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.sections = self.config.get("sections", {})
        self.keyword_rules = self.config.get("keyword_rules", {})

    def guess(self, description):
        """description から部門 ID を推定。当たらなければ None(= 要レビュー)。"""
        # 1. 完全一致(部門名そのものが摘要に含まれる)
        for name, id_val in self.sections.items():
            if name in description:
                logger.info(f"Rule match: '{name}' in '{description}'")
                return id_val
        # 2. keyword rule(短縮形)
        for keyword, section_name in self.keyword_rules.items():
            if keyword in description and section_name in self.sections:
                logger.info(f"Keyword match: '{keyword}' -> {section_name}")
                return self.sections[section_name]
        # 3. 当たらなければ None(ガクチョがレビューで埋める)
        return None

    def guess_name(self, description):
        """部門名を返す版(レビュー CSV / Sheets の section_name 列用)。当たらなければ ''。"""
        sid = self.guess(description)
        if sid is None:
            return ""
        for name, id_val in self.sections.items():
            if id_val == sid:
                return name
        return ""
