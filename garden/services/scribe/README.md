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

## ★Plaud アクセスの未確定事項(test/active の前提)

Plaud MCP は OAuth が**対話前提**でヘッドレス cron(VPS)から到達できない(client_steward の「Plaud は対話時に引く」homework と同根)。日次自動化には次のいずれかの解決が要る:

- **(a)** Plaud MCP の token をローカル/VPS の launcher run に持ち出せるか検証
- **(b)** ローカル cron(Plaud MCP が認証済の端末でスケジュール)
- **(c)** read-only の Plaud consumer API クライアントを Python 実装(email+pass の約300日トークンを secret 化。plaud-toolkit 方式)→ MCP に依存せず VPS cron 可

MVP は**手動「会議録まわして」**(MCP が生きるセッション)で価値を出し、上記を解いてから日次へ。
