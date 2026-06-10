"""staff_master — soil スタッフマスター(garden/soil/people/staff/)の読み取りと請求元照合。

invoice_processor の新機能(S41)の中核:
- 請求書の支払先(payee / partner_id)を soil のスタッフと照合し、
  「スタッフからの請求書」と「リスト外(取引先・ベンダー)の請求書」を分ける
- contract(経営/業務委託/外部スタッフ/アルバイト)を引けるようにし、
  稼働突合(worktime.py)で「業務委託なのに請求書が来ていない人」を検出する

正本は repo の soil(構造ファイル正本ルール、ADR 2026-06-02)。VPS では soil-sync が
garden-mirror に複製しているので、SOIL_STAFF_DIR でそこを指す。
照合キーは (1) Freee partner_id == freee_id (2) 氏名の正規化一致(空白除去)の 2 段。
ニックネームは誤マッチが怖い(「少佐」等)ので使わない。
"""
import os
import re

import yaml

from .utils import setup_logger

logger = setup_logger("StaffMaster")

_SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ローカル(repo)では service からの相対で soil に届く。VPS は garden-mirror 配下のため
# .env の SOIL_STAFF_DIR で明示する(/home/vps-harappa/garden-mirror/garden/soil/people/staff)。
DEFAULT_STAFF_DIR = os.path.normpath(
    os.path.join(_SERVICE_DIR, "..", "..", "soil", "people", "staff")
)
STAFF_DIR = os.environ.get("SOIL_STAFF_DIR", DEFAULT_STAFF_DIR)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _normalize(name: str) -> str:
    """氏名照合用の正規化: 全半角スペース除去 + 小文字化。"""
    if not name:
        return ""
    return name.replace(" ", "").replace("　", "").lower()


def load_staff(staff_dir=None):
    """active スタッフのリストを返す。

    各要素: {slug, name, name_norm, kana, contract, freee_id, freee_type, nicknames}
    `_` 始まり(テンプレ・alumni 等)と status != active は除外。
    """
    staff_dir = staff_dir or STAFF_DIR
    if not os.path.isdir(staff_dir):
        raise RuntimeError(
            f"スタッフマスターのディレクトリがありません: {staff_dir}\n"
            "→ SOIL_STAFF_DIR を確認してください(VPS は garden-mirror 配下)。"
        )
    staff = []
    for fn in sorted(os.listdir(staff_dir)):
        if not fn.endswith(".md") or fn.startswith("_") or fn == "README.md":
            continue
        path = os.path.join(staff_dir, fn)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            m = _FRONTMATTER_RE.match(text)
            if not m:
                continue
            meta = yaml.safe_load(m.group(1)) or {}
            if meta.get("type") != "staff" or meta.get("status") != "active":
                continue
            # 氏名は frontmatter に無く H1 が正本: 「# 和田 祐司(ユージさん)」
            h1 = _H1_RE.search(text[m.end():])
            name = h1.group(1).strip() if h1 else fn[:-3]
            name = re.sub(r"[((].*?[))]\s*$", "", name).strip()  # 末尾の(ニックネーム)を除去
            staff.append({
                "slug": fn[:-3],
                "name": name,
                "name_norm": _normalize(name),
                "kana": meta.get("kana", ""),
                "contract": str(meta.get("contract", "")),
                "freee_id": str(meta.get("freee_id", "") or ""),
                "freee_type": meta.get("freee_type", ""),
                "nicknames": meta.get("nicknames") or [],
            })
        except Exception as e:
            logger.warning(f"スタッフページの読み取り失敗(スキップ): {fn}: {e}")
    logger.info(f"Loaded {len(staff)} active staff from {staff_dir}")
    return staff


class StaffMatcher:
    def __init__(self, staff=None):
        self.staff = staff if staff is not None else load_staff()
        self._by_freee_id = {s["freee_id"]: s for s in self.staff if s["freee_id"]}

    def match(self, payee: str = "", partner_id=None):
        """請求書 1 枚をスタッフに照合する。該当スタッフ dict か None を返す。

        1. partner_id == freee_id(最優先。Freee 取引先が解決済みなら確実)
        2. 氏名の正規化一致(payee がスタッフ名を含む / スタッフ名が payee を含む)
        """
        if partner_id:
            s = self._by_freee_id.get(str(partner_id))
            if s:
                return s
        p = _normalize(payee)
        if not p:
            return None
        for s in self.staff:
            n = s["name_norm"]
            if n and (n in p or p in n):
                return s
        return None

    def find_by_name(self, name: str):
        """氏名(worktime シートの A 列等)からスタッフを引く。"""
        return self.match(payee=name)
