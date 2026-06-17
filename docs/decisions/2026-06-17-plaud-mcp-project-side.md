# ADR 2026-06-17 — Plaud MCP はプロジェクト側に持つ(ベンダー中立)

## ステータス
採択(S48)

## 背景

クライアント案件のナレッジ蓄積(soil/clients)で、打合せ録音 a/b の取り込みに **Plaud** を使う。Plaud は MCP を提供している([docs](https://docs.plaud.ai/plaud-mcp-cli/mcp))。

これまで Plaud MCP は **Claude デスクトップ / claude.ai のコネクタ経由**(ツール名 `mcp__claude_ai_plaud__*`)で繋がっていた。これは「Claude を使っているから動く」状態で、当プロジェクトの根幹方針 **ベンダーロックイン回避**([CLAUDE.md ベンダー中立の方針](../../CLAUDE.md) / [S31 ADR](2026-06-03-vendor-neutral-interaction-layer.md))に反する。

## 決定

**Plaud MCP の設定をプロジェクト(repo)側に持つ。** repo ルートの [`.mcp.json`](../../.mcp.json) に `mcpServers.plaud` を定義し、`npx -y @plaud-ai/mcp@latest` で起動する。これにより:

- Claude Code はもちろん、**他の LLM を API で叩く自前ランタイムからも、同じ `.mcp.json` を読めば Plaud を使える**(MCP は標準プロトコル)。
- 設定が repo にあるため、環境差・端末差で「ここでは Plaud が使えない」が起きない。

```json
{ "mcpServers": { "plaud": { "command": "npx", "args": ["-y", "@plaud-ai/mcp@latest"] } } }
```

## 認証(ガクチョの一度きりの操作)

- **API キー不要**。OAuth(ブラウザ同意)。トークンは `~/.plaud/tokens-mcp.json` にローカル保存。
- 初回のみ:Plaud にサインイン → 同意ページで **Authorize**。以後はトークンで自動。
- WSL/リモートはブラウザ手動 or `ssh -L 8199:localhost:8199` のポートフォワードでサインイン可。
- AI クライアント内からは「log me into Plaud」で再認証できる。

## 移行メモ

- `.mcp.json` の plaud は `mcp__plaud__*` という名前空間で現れる(claude.ai コネクタの `mcp__claude_ai_plaud__*` とは別)。
- 当面は両方が共存しうる。**正本はプロジェクト側 `.mcp.json`**。claude.ai コネクタは将来外してよい(ベンダー中立の観点では外すのが望ましい)。
- データは Plaud の US サーバを経由するが「リクエスト完了後は保存しない」と明記(ドキュメント)。クライアント機密を扱うため、取り込み後の soil への保存粒度は [soil/clients/README.md](../../garden/soil/clients/README.md) のデータ分類に従う(全文 transcript は soil に常駐させず、サマリ note + file_id 参照を正本とする)。

## 実装メモ(S48 実行結果)

- `npx -y @plaud-ai/mcp@latest install --yes` で OAuth 完了。トークン `~/.plaud/tokens-mcp.json`(access + refresh、自動更新)。**chmod 600 で権限を絞った**(secret 衛生)。token は repo 外なので git 漏洩リスクなし。
- インストーラは **Claude Code(user スコープ)/ Codex(`~/.codex/config.toml`)/ Cursor(`~/.cursor/mcp.json`)** にも plaud MCP を登録した。3ツールで動く=ベンダー中立を補強。ただし **携帯用の正本は repo の `.mcp.json`**(マシンを変えても repo を clone すれば設定が付いてくる)。user スコープ登録は重複だが無害なため放置。
- ⚠️ **副作用の後始末**: インストーラが `~/.claude/CLAUDE.md`(グローバル正本)に Plaud スキル 388 行を注入 → **除去した**。Plaud の使い方ガイドはグローバル CLAUDE.md でなく本 repo([soil/clients/README.md](../../garden/soil/clients/README.md))に置く方針。再 install すると再注入されるので、その都度除去すること(`sed -i '/<!-- plaud-skills:start -->/,/<!-- plaud-skills:end -->/d' ~/.claude/CLAUDE.md`)。
- `mcp__plaud__*`(プロジェクト側)は Claude Code の再起動後に有効。当面は claude.ai コネクタ(`mcp__claude_ai_plaud__*`)も併存。

## 関連
- [.mcp.json](../../.mcp.json)
- [soil/clients/README.md](../../garden/soil/clients/README.md) — クライアント区画の構造(Plaud 取り込みの動線を含む)
- [CLAUDE.md ベンダー中立の方針](../../CLAUDE.md)
