#!/usr/bin/env python3
"""S49 測量士 P2 回帰テスト: list_thread_ids は nextPageToken を辿り、上限到達時は
truncated=True を返す(取りこぼしを watermark で隠さない)。

google ライブラリはスタブ化してヘルメティックに動かす(import 時の依存解決のみ目的)。

実行: .venv/bin/python3 garden/services/client-steward/test/test_sweep_pagination.py
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = os.path.dirname(HERE)
sys.path.insert(0, SERVICE)

# dotenv / google 依存を import 時だけスタブ化(実 API は使わない)
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


class _Exec:
    def __init__(self, val):
        self.val = val

    def execute(self):
        return self.val


class _Threads:
    def __init__(self, pages):
        self.pages = pages
        self.tokens_seen = []

    def list(self, userId=None, q=None, maxResults=None, pageToken=None):
        self.tokens_seen.append(pageToken)
        idx = 0 if pageToken is None else int(pageToken)
        return _Exec(self.pages[idx])


class _Users:
    def __init__(self, threads):
        self._t = threads

    def threads(self):
        return self._t


class FakeSvc:
    def __init__(self, pages):
        self._t = _Threads(pages)
        self._u = _Users(self._t)

    def users(self):
        return self._u


def run():
    # --- 3ページ・最終ページに token なし → 全件取得・truncated False ---
    pages = [
        {"threads": [{"id": "a"}, {"id": "b"}], "nextPageToken": "1"},
        {"threads": [{"id": "c"}], "nextPageToken": "2"},
        {"threads": [{"id": "d"}]},  # token なし → ここで終了
    ]
    svc = FakeSvc(pages)
    ids, truncated = sweep_client.list_thread_ids(svc, "q", page_size=100, max_pages=10)
    assert ids == ["a", "b", "c", "d"], f"全ページ集約のはず: {ids}"
    assert truncated is False, "全件取れたら truncated=False"
    assert svc._t.tokens_seen == [None, "1", "2"], f"pageToken 連鎖: {svc._t.tokens_seen}"

    # --- max_pages 到達でまだ続きがある → truncated True・watermark を進めさせない ---
    pages2 = [
        {"threads": [{"id": "a"}], "nextPageToken": "1"},
        {"threads": [{"id": "b"}], "nextPageToken": "2"},
        {"threads": [{"id": "c"}], "nextPageToken": "3"},
    ]
    svc2 = FakeSvc(pages2)
    ids2, truncated2 = sweep_client.list_thread_ids(svc2, "q", page_size=100, max_pages=2)
    assert ids2 == ["a", "b"], f"max_pages=2 で2ページ分: {ids2}"
    assert truncated2 is True, "続きが残るなら truncated=True(取りこぼし顕在化)"

    # --- 1ページで完結(token なし)→ truncated False ---
    svc3 = FakeSvc([{"threads": [{"id": "x"}]}])
    ids3, truncated3 = sweep_client.list_thread_ids(svc3, "q", page_size=100, max_pages=20)
    assert ids3 == ["x"] and truncated3 is False

    print("OK test_sweep_pagination: nextPageToken 連鎖 + 上限到達で truncated")


if __name__ == "__main__":
    run()
