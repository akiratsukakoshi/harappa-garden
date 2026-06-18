#!/usr/bin/env python3
"""S49 測量士 P1 回帰テスト: get_all_wallet_txns は 100 件超を offset ページングで全件取得する。

freee_client(service コピー)の get_all_wallet_txns を、get_wallet_txns を擬似ページに
差し替えて検証する。実 API は叩かない。

実行: .venv/bin/python3 garden/services/finance/test/test_auditor_pagination.py
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = os.path.dirname(HERE)
sys.path.insert(0, SERVICE)

sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))
sys.modules["dotenv"].load_dotenv = lambda *a, **k: None

# FreeeClient.__init__ は int(os.getenv("FREEE_TARGET_COMPANY_ID")) を読むのでダミーを置く
os.environ.setdefault("FREEE_TARGET_COMPANY_ID", "0")
os.environ.setdefault("FREEE_CLIENT_ID", "dummy")
os.environ.setdefault("FREEE_CLIENT_SECRET", "dummy")

from lib.freee_client import FreeeClient  # noqa: E402


def _make_client(total):
    """total 件のデータを持ち、get_wallet_txns を offset/limit でスライスする client。"""
    client = FreeeClient(token_file=os.path.join(HERE, "_no_such_token.json"))
    data = [{"id": i, "status": 1} for i in range(total)]

    def fake_get_wallet_txns(walletable_type=None, walletable_id=None,
                             start_date=None, end_date=None, limit=100, offset=0):
        return data[offset:offset + limit]

    client.get_wallet_txns = fake_get_wallet_txns
    return client


def run():
    # 250 件 → page_size 100 で 100/100/50 の3ページを全部辿る
    c = _make_client(250)
    got = c.get_all_wallet_txns(page_size=100)
    assert len(got) == 250, f"250件取得のはず, got {len(got)}"
    assert [t["id"] for t in got] == list(range(250)), "順序/欠落なく全件のはず"

    # ちょうど 100 件(満ページ)→ 次ページ空で break、100件
    c = _make_client(100)
    assert len(c.get_all_wallet_txns(page_size=100)) == 100, "100件ちょうど"

    # 30 件(満たない)→ 1ページで終了
    c = _make_client(30)
    assert len(c.get_all_wallet_txns(page_size=100)) == 30, "30件"

    # 0 件 → 空
    c = _make_client(0)
    assert c.get_all_wallet_txns(page_size=100) == [], "0件は空リスト"

    # max_pages 安全弁: page_size=10 で 250 件は 25 ページ必要 → max_pages=3 で打ち切り
    c = _make_client(250)
    capped = c.get_all_wallet_txns(page_size=10, max_pages=3)
    assert len(capped) == 30, f"max_pages=3 で 30件打ち切りのはず, got {len(capped)}"

    print("OK test_auditor_pagination: 100件超を全ページ取得 + max_pages 安全弁")


if __name__ == "__main__":
    run()
