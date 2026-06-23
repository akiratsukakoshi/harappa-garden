#!/usr/bin/env python3
"""① 生取り込みレーン回帰テスト: append_inbox は新着スレッドの要点を _inbox.md に
append-only で書き、thread_id で dedup する(一度載せた行は人が消しても再 append しない)。

承認境界(SKILL): 生取り込み=自動、解釈=board 剪定。本テストは「自動レーンが履歴を
汚さず冪等」であることを担保する。google/dotenv 依存は import 時だけスタブ化。

実行: .venv/bin/python3 garden/services/client-steward/test/test_inbox_append.py
"""
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = os.path.dirname(HERE)
sys.path.insert(0, SERVICE)

sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
sys.modules["dotenv"].load_dotenv = lambda *a, **k: None
for name in [
    "google", "google.oauth2", "google.oauth2.credentials",
    "google.auth", "google.auth.transport", "google.auth.transport.requests",
    "googleapiclient", "googleapiclient.discovery",
]:
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["google.oauth2.credentials"].Credentials = object
sys.modules["google.auth.transport.requests"].Request = object
sys.modules["googleapiclient.discovery"].build = lambda *a, **k: None

import sweep_client  # noqa: E402


def _thread(tid, subj, finance=False, awaiting=False):
    return {
        "thread_id": tid, "subject": subj, "msgs": 2,
        "last_date": "Mon, 23 Jun 2026", "last_dt": None,
        "awaiting_us": awaiting, "days_since": 1,
        "finance": finance, "schedule": False,
    }


def run():
    with tempfile.TemporaryDirectory() as tmp:
        clients = os.path.join(tmp, "clients")
        slug = "acme"
        os.makedirs(os.path.join(clients, slug))  # soil 足場あり
        # CLIENTS_DIR / STATE_DIR をテスト用に差し替え
        sweep_client.CLIENTS_DIR = clients
        sweep_client.STATE_DIR = os.path.join(tmp, "state")
        fm = {"company": "ACME株式会社", "primary_domain": "acme.co.jp"}
        inbox = os.path.join(clients, slug, "_inbox.md")

        # --- 1回目: 2件 append・ヘッダ生成・state 記録 ---
        n1 = sweep_client.append_inbox(
            slug, fm,
            [_thread("t1", "見積の件", finance=True), _thread("t2", "日程調整", awaiting=True)],
            "2026-06-23")
        assert n1 == 2, f"初回は2件: {n1}"
        body = open(inbox, encoding="utf-8").read()
        assert "type: client_inbox" in body and "ACME株式会社" in body, "ヘッダ生成"
        assert "見積の件" in body and "日程調整" in body
        assert "<!-- thread:t1 -->" in body and "💰" in body, "thread marker + flag"

        # --- 2回目: 同じ2件 + 新規1件 → 新規だけ append(dedup) ---
        n2 = sweep_client.append_inbox(
            slug, fm,
            [_thread("t1", "見積の件", finance=True),
             _thread("t2", "日程調整", awaiting=True),
             _thread("t3", "請求書送付")],
            "2026-06-30")
        assert n2 == 1, f"既出2件は skip・新規1件のみ: {n2}"
        body2 = open(inbox, encoding="utf-8").read()
        assert body2.count("<!-- thread:t1 -->") == 1, "t1 は二重 append されない"
        assert "<!-- thread:t3 -->" in body2, "新規 t3 は載る"
        assert body2.count("type: client_inbox") == 1, "ヘッダは1回だけ"

        # --- 3回目: 人が _inbox.md を空にしても、state にある限り再 append しない ---
        open(inbox, "w").close()  # filing して空にした想定
        n3 = sweep_client.append_inbox(
            slug, fm, [_thread("t1", "見積の件"), _thread("t3", "請求書送付")], "2026-07-07")
        assert n3 == 0, f"state dedup で再 append ゼロ: {n3}"

        # --- soil 足場が無い slug(bootstrap 等)は 0 件・ファイルも作らない ---
        n4 = sweep_client.append_inbox(
            "no-soil", fm, [_thread("z1", "x")], "2026-06-23")
        assert n4 == 0, "soil 足場なしは書かない"

    print("OK test_inbox_append: append-only + thread_id dedup + 足場ガード")


if __name__ == "__main__":
    run()
