#!/usr/bin/env python3
"""S49 測量士 P1 回帰テスト: importer は部分失敗後の再実行で成功済み行を二重記帳しない。

外部依存(google / Freee)を持たないようヘルメティックに動かす:
  - lib.drive_client / lib.section_guesser はスタブ(google を読み込ませない)
  - dotenv は no-op スタブ
  - importer.FreeeClient を Fake に差し替え、Freee へ実 POST しない
  - FINANCE_STATE_DIR を一時ディレクトリに向け、冪等性台帳を隔離する

実行: .venv/bin/python3 garden/services/finance/test/test_importer_idempotency.py
"""
import os
import sys
import csv
import types
import tempfile
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = os.path.dirname(HERE)
sys.path.insert(0, SERVICE)


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m


# 外部依存をスタブ化(import importer が google を読み込まないように)
sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
sys.modules["dotenv"].load_dotenv = lambda *a, **k: None
import lib  # noqa: E402  (namespace package を確定させる)
_stub("lib.drive_client", DriveClient=object)
_stub("lib.section_guesser", SectionGuesser=object)

import importer  # noqa: E402


class FakeFreee:
    """Freee の代わり。post_manual_journal の呼び出しを記録し、fail_amounts は失敗させる。"""

    def __init__(self):
        self.posted = []          # 実際に POST が試みられた金額の列(成功・失敗とも)
        self.fail_amounts = set()  # この金額の行は post 失敗(None を返す)

    def get_sections(self):
        return [{"name": "営業部", "id": 1}]

    def get_account_items(self, name_hook=None):
        return 101 if name_hook == "売上高" else 102

    def get_taxes(self):
        return [{"name": "taxable_10", "code": 10}, {"name": "non_taxable", "code": 2}]

    def post_manual_journal(self, issue_date, details):
        amount = details[0]["amount"]
        self.posted.append(amount)
        if amount in self.fail_amounts:
            return None
        return {"id": len(self.posted)}


def _write_csv(path, rows):
    cols = ["date", "registration_date", "amount", "description", "section_name"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run():
    tmp = tempfile.mkdtemp(prefix="finance-idem-")
    os.environ["FINANCE_STATE_DIR"] = os.path.join(tmp, "state")
    csv_path = os.path.join(tmp, "review.csv")

    rows = [
        {"date": "2026-05-01", "registration_date": "2026-05-31", "amount": "1000",
         "description": "STORES 売上", "section_name": ""},
        {"date": "2026-05-02", "registration_date": "2026-05-31", "amount": "2000",
         "description": "Square 売上", "section_name": ""},
        {"date": "2026-05-03", "registration_date": "2026-05-31", "amount": "3000",
         "description": "STORES 売上", "section_name": ""},
    ]
    _write_csv(csv_path, rows)

    fake = FakeFreee()
    importer.FreeeClient = lambda *a, **k: fake

    args = argparse.Namespace(file=csv_path, dry_run=False, no_archive=True)

    # --- run 1: 2000 の行だけ失敗させる ---
    fake.fail_amounts = {2000}
    rc1 = importer.cmd_register(args)
    assert rc1 == 1, f"run1: 失敗1件で戻り値=1のはず, got {rc1}"
    assert fake.posted == [1000, 2000, 3000], f"run1 posts: {fake.posted}"

    # --- run 2: 失敗を解消して同じ CSV を再実行 ---
    fake.fail_amounts = set()
    rc2 = importer.cmd_register(args)
    assert rc2 == 0, f"run2: 全成功で戻り値=0のはず, got {rc2}"
    # 1000/3000 は run1 で登録済 → skip。2000 のみ再 post される。
    assert fake.posted == [1000, 2000, 3000, 2000], f"run2 後の posts: {fake.posted}"

    # 二重記帳していないことの本質的検証:
    assert fake.posted.count(1000) == 1, "1000 が二重 post された"
    assert fake.posted.count(3000) == 1, "3000 が二重 post された"
    assert fake.posted.count(2000) == 2, "2000 は失敗1回+成功1回で2回のはず"

    # --- run 3: 全件登録済 → 1件も post されない(完全冪等)---
    rc3 = importer.cmd_register(args)
    assert rc3 == 0, f"run3 戻り値=0のはず, got {rc3}"
    assert fake.posted == [1000, 2000, 3000, 2000], f"run3 で余分な post: {fake.posted}"

    print("OK test_importer_idempotency: 部分失敗後の再実行で二重記帳なし")


if __name__ == "__main__":
    run()
