"""board_lint.py — board 運用ルールの機械チェック(S56 一元管理の enforcement)。

「種ごとに各自ルールを書く」と必ず規約が破られる(stale fallback・unknown 分類・
status:approved 罠・pending 汚染は全部それが原因)。正本(garden/board/README.md)と
単一レジストリ(board_registry.py)に照らして、違反を機械的に拾い上げる。

チェック対象:
  1. レジストリ自身の整合(board_registry.self_check)
  2. board/pending/ の各 board: from_seed 有無・登録済み・status 値域・title 解決可否
  3. board を作る種(seeds/*/*.md): その from_seed が registry に登録済みか

呼び出し:
  python board_lint.py            # 全違反を stdout に出して終了コードで返す(0=clean)
  import board_lint; board_lint.collect_violations()  # 番人/ダッシュボードが使う [(sev,msg)...]
"""
import os
import re
from pathlib import Path

import board_registry as breg
import send_pending as sp

BOARD_PENDING = Path(os.environ.get("BOARD_PENDING", "/home/vps-harappa/garden/board/pending"))
SEEDS_DIR = Path(os.environ.get("GARDEN_SEEDS_DIR", "/home/vps-harappa/garden/seeds"))

VALID_STATUSES = {
    "pending", "approved", "test",
    "processed", "registered", "done", "completed", "sent", "skipped", "failed",
}

# 種が board を作る印(本文 raw を走査。簡易 frontmatter parser は nested を見ないため)
_BOARD_MARKERS = ("kind: board_draft", "channel: board", "channel: board_with_notify")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def lint_registry() -> list:
    return [("ERROR", f"registry: {p}") for p in breg.self_check()]


def lint_pending_boards() -> list:
    out = []
    if not BOARD_PENDING.exists():
        return out
    for path in sorted(BOARD_PENDING.glob("*.md")):
        if path.name == "placeholder.md":
            continue
        fm, body = sp.parse_frontmatter(_read(path))
        name = path.name
        seed = (fm.get("from_seed") or "").strip()
        status = (fm.get("status") or "").strip()
        if not seed:
            out.append(("ERROR", f"{name}: from_seed が無い"))
        elif not breg.is_registered(seed):
            out.append(("ERROR", f"{name}: 種 `{seed}` が board_registry 未登録"))
        if not status:
            out.append(("WARN", f"{name}: status が無い"))
        elif status not in VALID_STATUSES:
            out.append(("WARN", f"{name}: status `{status}` は規定外(正本の許容値を確認)"))
        # title 解決可否(frontmatter title / registry / 本文H1 のいずれかで出るか)
        _, title = breg.classify(seed, fm, body)
        if not title or title == seed:
            out.append(("WARN", f"{name}: 日本語タイトルを解決できない(frontmatter に title: を)"))
    return out


def _iter_seed_files():
    if not SEEDS_DIR.exists():
        return
    for path in SEEDS_DIR.glob("*/*.md"):
        yield path


def lint_seeds() -> list:
    """board を作る種が registry に登録済みか(双方向の取りこぼし防止)。"""
    out = []
    for path in _iter_seed_files():
        text = _read(path)
        if not any(m in text for m in _BOARD_MARKERS):
            continue  # board を作らない種は対象外
        fm, _ = sp.parse_frontmatter(text)
        name = (fm.get("name") or "").strip()
        plot = (fm.get("plot") or "").strip()
        if not name or not plot:
            out.append(("WARN", f"seed {path.parent.name}/{path.name}: name/plot 欠落で照合不可"))
            continue
        seed = f"{plot}/{name}"
        if not breg.is_registered(seed):
            out.append(("ERROR", f"seed `{seed}` は board を作るが board_registry 未登録"))
    return out


def collect_violations() -> list:
    """[(severity, message)] を返す。severity: ERROR / WARN。"""
    return lint_registry() + lint_pending_boards() + lint_seeds()


def main() -> int:
    sp.load_env()
    viol = collect_violations()
    if not viol:
        print("✅ board lint: 違反なし")
        return 0
    errors = [m for s, m in viol if s == "ERROR"]
    warns = [m for s, m in viol if s == "WARN"]
    for s, m in viol:
        print(f"[{s}] {m}")
    print(f"\n--- ERROR {len(errors)} / WARN {len(warns)} ---")
    return 1 if errors else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
