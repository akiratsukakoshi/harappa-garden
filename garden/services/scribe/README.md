# scribe service(会議録の番人・水面下)

scribe 区画([SKILL](../../plots/scribe/SKILL.md))の実装層。**判定の本体(主体・種別・タイトルの推定)は LLM(種 [daily-recording-sweep](../../seeds/scribe/daily-recording-sweep.md) の prompt)が担う**ため、ここに置く Python は薄い:状態管理(watermark)と、必要なら入力の整形だけ。

## 役割分担(なぜ Python が薄いか)

| やること | 担い手 |
|---|---|
| Plaud 録音の取得(list/note/transcript) | **Plaud MCP**(read-only)。LLM が対話/run 中に呼ぶ |
| Google カレンダーの照合 | 既存カレンダー OAuth(morning-briefing 流用)。LLM が読む |
| 主体・クライアント・会議タイトルの判定 | **LLM**(SKILL の判定ルール) |
| soil への meeting MD 起こし | **LLM**(soil/clients/README の粒度に従って書く) |
| 処理済み watermark(べき等) | **この service**(`state/processed.jsonl`) |

## 状態(state/)

- `state/processed.jsonl` — 処理済み録音の台帳。1行 = `{plaud_file_id, date, 主体, soil_path|null, processed_at}`。
  - 差分起動(date_from)とべき等性(再処理防止)の根拠。
  - soil への取り込み有無もここで追える(`soil_path: null` = リネーム提案のみ)。

## Plaud アクセスのブリッジ(S54 解決 = 案 b)

Plaud MCP の OAuth トークンは `~/.plaud/tokens-mcp.json` に **refresh_token 付きで保存され自動更新される**。これを持つホスト(ガクチョが認証済の**ローカル WSL**)でなら、ヘッドレス `claude -p` が非対話で Plaud に到達できる(S54 実測)。

- refresh_token はローテートし得るので **トークン所有ホストは1つに固定**(VPS にコピーしない)→ scribe はローカル WSL が所有ホスト。
- 日次自動化 = **ローカル WSL の crontab**(`30 7 * * *` → [run-local.sh](run-local.sh))。
  - run-local.sh: launcher(MCP フラグ付きで claude -p)→ soil/board をローカル repo に書く → soil-sync push + board rsync で VPS へ。
- 手動「録音スイープして」= VPS の bot は Plaud に届かないので、**bot がマーカー(`inbox/scribe/requested.flag`)を置く → ローカル poll cron(`*/10` → [scribe-poll.sh](scribe-poll.sh))が atomic に拾って run-local.sh を実行**。
- launcher の MCP 対応 = 種 frontmatter `execute.mcp`(config/strict/permission_mode/allowed_tools)→ `--mcp-config`/`--strict-mcp-config`/`--permission-mode`/`--allowedTools`。**prompt は -p 直後の positional**(allowedTools 可変長が末尾 prompt を飲む S54 バグ回避)。

## ファイル

- [run-local.sh](run-local.sh) — ローカル日次/手動実行(launcher → soil/board push)
- [scribe-poll.sh](scribe-poll.sh) — 手動依頼マーカーの poll(ローカル cron `*/10`)
- `state/processed.jsonl` — 処理済み録音台帳(べき等の根拠)
