# 2026-06-25 権限正本を repo 内に置く(`.claude/settings.json` を生成物に降格)

## ステータス

採用(S60 / 測量士 2026-06-24 提案3)

## 文脈

VPS の `/home/vps-harappa/.claude/settings.json` が、サブプロセス全権エージェント
(`claude -p` = launcher seed / master bot / 定時あいさつ)の **OS 権限正本**だった:

- `permissions.allow` に Read/Write/Edit の path glob と、サービス別 `.venv/bin/python` の
  Bash allowlist、計 23 エントリ。
- このファイルは **repo 外(VPS runtime)** にあり、手編集で維持されていた。

問題(測量士 P1):

- 権限の意図が repo 内の機械可読データに無い → 別 LLM(codex/gemini)はこの権限契約を読めない。
- 手編集ゆえ S57 の SNS temp 権限漏れ(`sns-manager/temp/**` の付け忘れ)が起きた。
- [[2026-06-25-vps-claude-auth-setup-token]] 同様、「repo=正本・VPS=実行状態」の原則からずれていた。

## 決定

**権限の意図を repo 内の宣言的正本に置き、`.claude/settings.json` はそこから生成される側にする。**

- 正本: [`garden/runtime/grants.yml`](../../garden/runtime/grants.yml)
  - `host` / `home` / 全体 `read` / 全体 `write`(Write+Edit 生成)/ サービス別 `bash`・`write` を宣言。
  - 各サービスは default-deny。挙げた python だけ Bash 可、working/temp だけ書込可。
- 生成器: [`garden/runtime/render-claude-settings.py`](../../garden/runtime/render-claude-settings.py)
  - `grants.yml` → `permissions.allow` を決定的順序で生成。
  - `--check LIVE` で既存 settings.json と**集合比較**(順序非依存)。差分があれば exit 1。
- 生成ホスト(D2): **repo 側で render → settings.json を VPS へ rsync**(VPS は dumb のまま)。

### 軸の分離(重要)

`grants.yml` は「**サブプロセス全権エージェントの OS 権限**(Bash/Read/Write/Edit allowlist)」の正本。
[`garden-gaku-co/capabilities.py`](../../garden/services/garden-gaku-co/capabilities.py) の
「**LLM tool の scope 認可**(どの registry tool を呼べるか)」とは**別軸**。混ぜない
(だから既存 `capabilities.py` の拡張ではなく新ファイル `grants.yml` を選んだ。命名衝突も回避)。

## 検証

初回 render が現 live settings.json を**完全再現**することを確認(no-op で安全に移行):

```
$ render-claude-settings.py --check <live settings.json>
[check] IDENTICAL — grants と … の allow は完全一致(23 entries)
```

## 運用(今後)

権限を変えるときは settings.json を手で触らない:

1. `garden/runtime/grants.yml` を編集
2. `render-claude-settings.py --check <live>` で意図差分を確認
3. `render-claude-settings.py -o settings.json` → VPS `~/.claude/settings.json` に rsync

## 却下した代替案

- **`capabilities.py` を seed/command まで拡張**(測量士の別案): OS 権限と LLM tool scope を
  同一ファイルに混ぜると 2 つの関心が濁る。別軸として分離する方が後で LLM を替えても読みやすい。
- **`capabilities.yml` という名前**: 既存 `capabilities.py`(別軸)と紛らわしいため `grants.yml` に。

## 関連

- 測量士の手紙 [2026-06-24](../surveyor/letters/2026-06-24.md) 提案3
- [[repo-authoring-vps-runtime]] — repo=正本 / VPS=実行状態の原則
- 同提案の第一弾: [Garden Runtime 抽象化(提案1+2)](#) = launcher engine / bot AgentRunner(S60 commit `c8e48a0`)
