#!/usr/bin/env python3
"""Vendor 固有語の分布を分類して表示する。

この監査は「Claude と書いてあるから悪い」とは扱わない。runner / provider / renderer
などの意図された依存、runtime kit 内の依存説明、履歴ログ、seed frontmatter の
切替面を分け、未分類の直書きを見つけるための道具。
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_PATTERNS = {
    "claude-command": re.compile(r"\bclaude(?:\s+-p|\b)"),
    "claude-bin": re.compile(r"\bCLAUDE_BIN\b"),
    "claude-settings": re.compile(r"\.claude/settings\.json"),
    "claude-tools-flag": re.compile(r"--(?:allowedTools|disallowedTools|permission-mode)"),
    "claude-model": re.compile(r"\b(?:sonnet|haiku|opus)(?:[-\w]*)?\b", re.IGNORECASE),
    "anthropic": re.compile(r"\banthropic\b", re.IGNORECASE),
    "claude-engine": re.compile(r"engine:\s*claude-code\b"),
}

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}

EXCLUDED_FILENAMES = {
    ".env",
    "credentials.json",
    "token.json",
    "oauth_credentials.json",
}

SECRET_NAME_RE = re.compile(r"(^|[./])(\.env|.*secret.*|.*token.*|.*credential.*)(\.|$)", re.IGNORECASE)


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    pattern: str
    category: str
    text: str


def classify(rel: str) -> str:
    """依存の位置を分類する。"""
    if rel in {"CLAUDE.md", "AGENTS.md", "garden/MAP.md", "garden/OPERATIONS.md"}:
        return "live-doc"
    if rel.startswith("garden/runtime/"):
        return "runtime-kit"
    if rel.startswith("docs/sessions/") or rel.startswith("docs/decisions/"):
        return "history"
    if rel.startswith("docs/surveyor/letters/") or rel.startswith("docs/security/incidents/"):
        return "history"
    if rel.startswith("garden/seeds/"):
        return "config-surface"
    if rel.startswith("garden/services/launcher/"):
        return "intended"
    if rel.startswith("garden/services/garden-gaku-co/"):
        return "intended"
    return "unclassified"


def is_probably_text(path: Path, max_bytes: int) -> bool:
    try:
        if path.stat().st_size > max_bytes:
            return False
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in sample


def iter_files(root: Path, targets: list[str], include_history: bool, max_bytes: int) -> Iterable[Path]:
    roots = [root / t for t in targets] if targets else [
        root / "CLAUDE.md",
        root / "AGENTS.md",
        root / "garden" / "MAP.md",
        root / "garden" / "OPERATIONS.md",
        root / "garden" / "runtime",
        root / "garden" / "services" / "launcher",
        root / "garden" / "services" / "garden-gaku-co",
        root / "garden" / "seeds",
        root / "docs" / "decisions",
        root / "docs" / "surveyor",
    ]
    for start in roots:
        if not start.exists():
            continue
        if start.is_file():
            rel = start.relative_to(root).as_posix()
            if should_scan(rel, include_history) and is_probably_text(start, max_bytes):
                yield start
            continue
        for dirpath, dirnames, filenames in os.walk(start):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
            for name in filenames:
                path = Path(dirpath) / name
                rel = path.relative_to(root).as_posix()
                if should_scan(rel, include_history) and is_probably_text(path, max_bytes):
                    yield path


def should_scan(rel: str, include_history: bool) -> bool:
    name = Path(rel).name
    if name in EXCLUDED_FILENAMES:
        return False
    if SECRET_NAME_RE.search(rel):
        return False
    if not include_history and (
        rel.startswith("docs/sessions/")
        or rel.startswith("docs/decisions/")
        or rel.startswith("docs/surveyor/letters/")
        or rel.startswith("docs/security/incidents/")
    ):
        return False
    return True


def scan(root: Path, targets: list[str], include_history: bool, max_bytes: int) -> list[Hit]:
    hits: list[Hit] = []
    for path in iter_files(root, targets, include_history, max_bytes):
        rel = path.relative_to(root).as_posix()
        category = classify(rel)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, 1):
            for name, pattern in DEFAULT_PATTERNS.items():
                if pattern.search(line):
                    hits.append(
                        Hit(
                            path=rel,
                            line=line_no,
                            pattern=name,
                            category=category,
                            text=line.strip()[:180],
                        )
                    )
    return hits


def summarize(hits: list[Hit]) -> dict[str, int]:
    out: dict[str, int] = {}
    for hit in hits:
        out[hit.category] = out.get(hit.category, 0) + 1
    return dict(sorted(out.items()))


def print_text(hits: list[Hit], *, show_history: bool) -> None:
    summary = summarize(hits)
    print("Vendor lock audit")
    print("=================")
    if not hits:
        print("No vendor-specific terms found.")
        return
    print("Summary:")
    for category, count in summary.items():
        print(f"- {category}: {count}")
    print()

    categories = ["unclassified", "live-doc", "config-surface", "intended", "runtime-kit"]
    if show_history:
        categories.append("history")
    for category in categories:
        rows = [h for h in hits if h.category == category]
        if not rows:
            continue
        print(f"[{category}]")
        for hit in rows:
            print(f"{hit.path}:{hit.line}: {hit.pattern}: {hit.text}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parents[2], type=Path)
    parser.add_argument("--target", action="append", default=[], help="scan only this path, relative to root")
    parser.add_argument("--include-history", action="store_true", help="include sessions/ADR/surveyor history")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--max-bytes", type=int, default=512_000)
    parser.add_argument("--fail-on-unclassified", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    hits = scan(root, args.target, args.include_history, args.max_bytes)
    if args.format == "json":
        print(json.dumps({"summary": summarize(hits), "hits": [asdict(h) for h in hits]}, ensure_ascii=False, indent=2))
    else:
        print_text(hits, show_history=args.include_history)

    if args.fail_on_unclassified and any(h.category == "unclassified" for h in hits):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
