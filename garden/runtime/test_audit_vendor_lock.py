"""audit-vendor-lock.py の最小テスト。"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "audit_vendor_lock", os.path.join(HERE, "audit-vendor-lock.py")
)
avl = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = avl
_spec.loader.exec_module(avl)


def test_classify_runtime_kit():
    assert avl.classify("garden/runtime/VENDOR_SWITCH.md") == "runtime-kit"


def test_classify_seed_as_config_surface():
    assert avl.classify("garden/seeds/daily-pilot/morning-briefing.md") == "config-surface"


def test_classify_live_doc():
    assert avl.classify("garden/MAP.md") == "live-doc"


def test_scan_skips_secret_named_files():
    with tempfile.TemporaryDirectory() as d:
        root = avl.Path(d)
        (root / "garden").mkdir()
        (root / "garden" / ".env").write_text("CLAUDE_BIN=secret\n", encoding="utf-8")
        (root / "garden" / "note.md").write_text("engine: claude-code\n", encoding="utf-8")
        hits = avl.scan(root, ["garden"], include_history=True, max_bytes=512_000)
        assert hits
        assert {hit.path for hit in hits} == {"garden/note.md"}


def test_scan_finds_anthropic():
    with tempfile.TemporaryDirectory() as d:
        root = avl.Path(d)
        (root / "garden" / "services" / "garden-gaku-co" / "brain").mkdir(parents=True)
        p = root / "garden" / "services" / "garden-gaku-co" / "brain" / "provider.py"
        p.write_text("from anthropic import Anthropic\n", encoding="utf-8")
        hits = avl.scan(root, ["garden"], include_history=True, max_bytes=512_000)
        assert hits
        assert hits[0].category == "intended"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"✔ {test.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"✘ {test.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    raise SystemExit(1 if _run_all() else 0)
