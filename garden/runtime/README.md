# garden/runtime — Garden Runtime の切替正本

> サブプロセス全権エージェント(seed runner / master bot / 定時あいさつ)の
> **OS 権限**と、LLM / agent runner / API provider の**切替点**を置く。
> 測量士 2026-06-24 提案3 / 2026-06-25 Vendor Switch Kit。

## ファイル

| ファイル | 役割 |
|---|---|
| [`VENDOR_SWITCH.md`](VENDOR_SWITCH.md) | ベンダー切替時に必ず見る正本。切替点・標準手順・監査の読み方 |
| [`engines.yml`](engines.yml) | active engine / candidate engine の台帳 |
| [`checklists/`](checklists/) | engine 別の切替チェックリスト |
| [`grants.yml`](grants.yml) | **権限正本**。host/home・全体 read/write・サービス別 bash/write を宣言 |
| [`render-claude-settings.py`](render-claude-settings.py) | `grants.yml` → `.claude/settings.json` を生成。`--check` で live と集合比較 |
| [`test_render.py`](test_render.py) | 生成器の退行ガード(件数・形式・代表エントリ) |
| [`audit-vendor-lock.py`](audit-vendor-lock.py) | Claude / Anthropic 固有語の分布を分類する監査 |
| [`test_audit_vendor_lock.py`](test_audit_vendor_lock.py) | vendor lock 監査の最小テスト |
| [`smoke/`](smoke/) | runner 切替時の低リスク smoke。temp/log のみで seed runner と master runner 配線を確認 |

## なぜ

VPS `.claude/settings.json` を手編集していたため、権限の意図が repo 外にあり別 LLM が読めず、
S57 の SNS temp 権限漏れも起きた。権限を **repo 内の機械可読正本**にし、settings.json は
そこから**生成される側**にする。

また、Claude / Codex / Gemini CLI / API provider の切替を単発の移行作業にすると、
runner 引数・MCP 設定・権限形式・secret の確認点が散らばる。`garden/runtime/` に
Vendor Switch Kit を置き、切替を Garden Runtime の点検作業として扱う。

## 運用(権限を変えるとき)

settings.json を手で触らない:

```bash
# 1. grants.yml を編集
# 2. 意図差分を確認(live settings と集合比較)
python3 garden/runtime/render-claude-settings.py --check /path/to/live/settings.json
# 3. 生成して VPS へ反映
python3 garden/runtime/render-claude-settings.py --host vps-harappa --profile claude-code -o settings.json
rsync settings.json harappa:/home/vps-harappa/.claude/settings.json
```

## 軸の注意

ここは「**OS 権限**(Bash/Read/Write/Edit allowlist)」の正本。
[`garden-gaku-co/capabilities.py`](../services/garden-gaku-co/capabilities.py) の
「**LLM tool の scope 認可**」とは別軸 — 混ぜない。

## Vendor lock 監査

```bash
python3 garden/runtime/audit-vendor-lock.py
python3 garden/runtime/audit-vendor-lock.py --include-history
```

この監査は vendor 固有語を即エラー扱いしない。`intended` / `runtime-kit` /
`live-doc` / `config-surface` / `history` / `unclassified` に分類し、
切替時に読むべき場所を見える化する。

## Runtime smoke

```bash
python3 garden/runtime/smoke/run-smoke.py
python3 garden/runtime/smoke/run-smoke.py --engine codex
python3 garden/runtime/smoke/run-smoke.py --engine codex --mode scratch-write
python3 garden/runtime/smoke/run-smoke.py --engine codex --real-runner
python3 garden/runtime/smoke/run-smoke.py --engine codex --mode scratch-write --real-runner
```

実 LLM / secret / production board には触れず、temp directory と `/bin/echo` runner で
seed runner の dry-run / 実行パス、master runner の単体テスト、grants renderer の単体テストを確認する。
`--real-runner` は temp directory のまま実 Codex CLI 経路だけを確認する。
