"""render-claude-settings.py の unit test(S60 / 測量士 2026-06-24 提案3)。

VPS 不要。同梱の grants.yml をレンダリングして件数・形式・代表エントリを検証する。
実行: garden/runtime/ で `python3 test_render.py`
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ハイフン入りファイル名なので spec から読み込む
_spec = importlib.util.spec_from_file_location(
    "render_claude_settings", os.path.join(HERE, "render-claude-settings.py")
)
rcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rcs)


def _grants():
    return rcs.load_grants(os.path.join(HERE, "grants.yml"))


def test_entry_count_is_23():
    allow = rcs.render_allow(_grants())
    assert len(allow) == 23, f"期待 23 / 実際 {len(allow)}"


def test_no_duplicates():
    allow = rcs.render_allow(_grants())
    assert len(allow) == len(set(allow)), "重複エントリがある"


def test_write_generates_edit_pair():
    allow = set(rcs.render_allow(_grants()))
    # 全体 write の board は Write と Edit の両方が出る
    assert "Write(//home/vps-harappa/garden/board/**)" in allow
    assert "Edit(//home/vps-harappa/garden/board/**)" in allow


def test_bash_format_has_colon_star():
    allow = set(rcs.render_allow(_grants()))
    # サービスの bash は絶対パス + :*(launcher の scoped Bash 形式)
    assert "Bash(/home/vps-harappa/garden/services/finance/.venv/bin/python:*)" in allow


def test_service_write_relative_to_service():
    allow = set(rcs.render_allow(_grants()))
    # S57 で漏れた sns-manager/temp が Write+Edit で出ること(再発防止の要)
    assert "Write(//home/vps-harappa/garden/services/sns-manager/temp/**)" in allow
    assert "Edit(//home/vps-harappa/garden/services/sns-manager/temp/**)" in allow


def test_read_double_slash_prefix():
    allow = set(rcs.render_allow(_grants()))
    assert "Read(//home/vps-harappa/garden/**)" in allow


def test_default_host_profile_selected():
    selected = rcs.select_grants(_grants())
    assert selected["host"] == "vps-harappa"
    assert selected["profile"] == "claude-code"
    assert selected["home"] == "/home/vps-harappa"


def test_explicit_local_codex_read_only_profile():
    allow = rcs.render_allow(_grants(), host="local-wsl", profile="codex-read-only")
    assert allow == ["Read(//home/tukapontas/harappa-garden/**)"]


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✔ {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"✘ {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
