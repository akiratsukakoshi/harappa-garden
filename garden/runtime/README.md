# garden/runtime — Garden Runtime の権限正本

> サブプロセス全権エージェント(`claude -p` = launcher seed / master bot / 定時あいさつ)が
> 使う **OS 権限の宣言的正本**を置く。測量士 2026-06-24 提案3 / [ADR 2026-06-25](../../docs/decisions/2026-06-25-permission-source-of-truth-in-repo.md)。

## ファイル

| ファイル | 役割 |
|---|---|
| [`grants.yml`](grants.yml) | **権限正本**。host/home・全体 read/write・サービス別 bash/write を宣言 |
| [`render-claude-settings.py`](render-claude-settings.py) | `grants.yml` → `.claude/settings.json` を生成。`--check` で live と集合比較 |
| [`test_render.py`](test_render.py) | 生成器の退行ガード(件数・形式・代表エントリ) |

## なぜ

VPS `.claude/settings.json` を手編集していたため、権限の意図が repo 外にあり別 LLM が読めず、
S57 の SNS temp 権限漏れも起きた。権限を **repo 内の機械可読正本**にし、settings.json は
そこから**生成される側**にする。

## 運用(権限を変えるとき)

settings.json を手で触らない:

```bash
# 1. grants.yml を編集
# 2. 意図差分を確認(live settings と集合比較)
python3 garden/runtime/render-claude-settings.py --check /path/to/live/settings.json
# 3. 生成して VPS へ反映
python3 garden/runtime/render-claude-settings.py -o settings.json
rsync settings.json harappa:/home/vps-harappa/.claude/settings.json
```

## 軸の注意

ここは「**OS 権限**(Bash/Read/Write/Edit allowlist)」の正本。
[`garden-gaku-co/capabilities.py`](../services/garden-gaku-co/capabilities.py) の
「**LLM tool の scope 認可**」とは別軸 — 混ぜない。
