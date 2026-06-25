#!/usr/bin/env python3
"""garden/runtime/grants.yml → .claude/settings.json の permissions.allow を生成する。

測量士 2026-06-24 提案3。権限の意図を repo 内の機械可読正本(grants.yml)に置き、
.claude/settings.json は「そこから生成される側」にする。手編集による S57 型の
権限漏れ(sns-manager/temp/** の付け忘れ)を構造的に防ぐ。

使い方:
  python3 render-claude-settings.py             # 生成して stdout に表示
  python3 render-claude-settings.py -o PATH      # PATH に書き出し
  python3 render-claude-settings.py --check PATH # PATH(live settings)の allow と
                                                 # 集合比較。一致で exit 0 / 差分で exit 1

軸: サブプロセス全権エージェントの OS 権限(Bash/Read/Write/Edit allowlist)の生成。
    LLM tool scope(capabilities.py)とは別。詳細は grants.yml 冒頭コメント。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GRANTS = os.path.join(HERE, "grants.yml")


def select_grants(grants: dict, host: str | None = None, profile: str | None = None) -> dict:
    """host/profile 対応 grants から renderer 入力を取り出す。

    S60 初版の単一 host 形式も読めるように残す。
    """
    if "hosts" not in grants:
        return grants

    host_name = host or grants.get("default_host")
    profile_name = profile or grants.get("default_profile")
    if not host_name:
        raise KeyError("default_host is not set")
    host_cfg = (grants.get("hosts") or {}).get(host_name)
    if not host_cfg:
        raise KeyError(f"host not found: {host_name}")
    profiles = host_cfg.get("profiles") or {}
    if not profile_name:
        if len(profiles) == 1:
            profile_name = next(iter(profiles))
        else:
            raise KeyError("default_profile is not set")
    profile_cfg = profiles.get(profile_name)
    if not profile_cfg:
        raise KeyError(f"profile not found for host {host_name}: {profile_name}")
    selected = dict(profile_cfg)
    selected["host"] = host_name
    selected["profile"] = profile_name
    selected["home"] = host_cfg["home"]
    return selected


def render_allow(grants: dict, host: str | None = None, profile: str | None = None) -> list[str]:
    """grants から permissions.allow のエントリ列を決定的順序で生成する。"""
    grants = select_grants(grants, host=host, profile=profile)
    home = grants["home"]              # 例 /home/vps-harappa
    fp = "/" + home                    # file-perm 接頭辞 → //home/vps-harappa
    allow: list[str] = []

    for g in grants.get("read", []) or []:
        allow.append(f"Read({fp}/{g})")

    for g in grants.get("write", []) or []:
        allow.append(f"Write({fp}/{g})")
        allow.append(f"Edit({fp}/{g})")

    for svc, cfg in (grants.get("services") or {}).items():
        base = f"garden/services/{svc}"
        cfg = cfg or {}
        for b in cfg.get("bash", []) or []:
            allow.append(f"Bash({home}/{base}/{b}:*)")
        for w in cfg.get("write", []) or []:
            allow.append(f"Write({fp}/{base}/{w})")
            allow.append(f"Edit({fp}/{base}/{w})")

    return allow


def render_settings(grants: dict, host: str | None = None, profile: str | None = None) -> dict:
    return {"permissions": {"allow": render_allow(grants, host=host, profile=profile)}}


def load_grants(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--grants", default=DEFAULT_GRANTS, help="grants.yml のパス")
    ap.add_argument("--host", help="生成対象 host。未指定なら grants.yml の default_host")
    ap.add_argument("--profile", help="生成対象 profile。未指定なら grants.yml の default_profile")
    ap.add_argument("-o", "--out", help="生成した settings.json の書き出し先")
    ap.add_argument("--check", metavar="LIVE",
                    help="LIVE(既存 settings.json)の allow と集合比較し差分を表示")
    args = ap.parse_args()

    grants = load_grants(args.grants)
    settings = render_settings(grants, host=args.host, profile=args.profile)
    rendered = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        with open(args.check, encoding="utf-8") as f:
            live = json.load(f)
        live_set = set(live.get("permissions", {}).get("allow", []))
        gen_set = set(settings["permissions"]["allow"])
        missing = sorted(live_set - gen_set)   # live にあるが grants から出ない(=正本未反映)
        extra = sorted(gen_set - live_set)      # grants から出るが live に無い(=未適用)
        if not missing and not extra:
            print(f"[check] IDENTICAL — grants と {args.check} の allow は完全一致"
                  f"({len(gen_set)} entries)")
            return 0
        print(f"[check] DIFFERS — live={len(live_set)} generated={len(gen_set)}")
        for e in missing:
            print(f"  live のみ(grants 未反映): {e}")
        for e in extra:
            print(f"  generated のみ(未適用): {e}")
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"[written] {args.out} ({len(settings['permissions']['allow'])} entries)")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
