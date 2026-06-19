---
type: seed
name: daily-recording-sweep
plot: scribe
description: 1日1回、Plaud の新規録音を Google カレンダー × 会議内容 × 過去履歴と照らして主体・会議タイトルを判定し、(1) クライアント関連の会議は soil/clients の該当案件 meetings/ に取り込み(漏れ防止)、(2) 全録音に正規タイトル `MM-DD 【主体】会議タイトル` を提案して Discord master に出す(ガクチョが Plaud アプリで手動リネーム)。リネーム・フォルダ操作は API 不可のため自動化しない(提案のみ)。
status: test                     # S53。手動スイープが実録音9件で GREEN(判定/べき等/新規炙り出し/実取り込み)。active = 日次自動化「Plaud アクセスのブリッジ」解決後。それまで手動運用
phase: 1
execution_host: local           # ★Plaud MCP は OAuth 対話前提 → ヘッドレス VPS cron 不可。MVP は MCP が認証済の環境(対話/ローカル)で実行。日次自動化は「Plaud アクセスのブリッジ」解決が前提(SKILL 末尾)
hmc_dependency: none
version: 1
created: 2026-06-19
created_by: claude (with ガクチョ, セッション53)
last_updated: 2026-06-19
linked_skills:
  - "garden/plots/scribe/SKILL.md"   # Mode D
linked_services:
  - "garden/services/scribe/"        # watermark/state ヘルパ(薄い。判定本体は LLM)
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 7 * * *"           # 毎朝 07:30 JST(朝ブリーフィングの後)。★日次自動化はブリッジ解決後に有効化
  timezone: Asia/Tokyo
  # 手動起動(MVP の主経路): ガクチョが「会議録まわして」「録音整理して」→ ガクコ/エージェントが Mode D を実行
  #   (Plaud MCP が認証済のセッションで動く前提)

# === ② 何を実行するか ===
engine: claude-code
execute:
  timeout_minutes: 15
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは scribe 区画の種「daily-recording-sweep」です。Plaud の録音を取りこぼさず
    soil に収め、正しいタイトルを提案する「会議録の番人」です。

    まず以下を Read し、指示に従ってください:
      1. garden/CHARTER.md
      2. garden/plots/scribe/SKILL.md(Mode D / タイトル表記ルール / 主体判定 / 承認境界)
      3. garden/soil/clients/README.md(Plaud 取り込みの動線 a/b・soil 固定の粒度)

    今回の動的入力:
      - today: {today}

    Step 1 新規録音を拾う(watermark 差分・べき等):
      - state(garden/services/scribe/state/processed.jsonl 等)で処理済み file_id を確認。
      - mcp__plaud__list_files(date_from = 前回処理日)で新着を取得。処理済みはスキップ。

    Step 2 各録音の主体・種別を判定:
      - mcp__plaud__get_note で内容サマリを取得。
      - Google カレンダー(start_at に重なる予定 → 参加者・件名)と soil/clients の既存案件・
        担当者名を突き合わせ、category(クライアント関連 / 社内 / メンタリング / 個人 / イベント)・
        主体・会議タイトルを決める。Plaud 既存タイトルに主体が既にあれば尊重。

    Step 3 soil 取り込み(クライアント関連のみ・factual は自動):
      - 該当案件の meetings/YYYY-MM-DD_{会議名}.md を起こす(AI サマリ note + frontmatter。
        全文 transcript は soil に常駐させず file_id 参照)。
      - 解釈(新規案件の確定 / 新規クライアントの登録 / confidential 判断)は soil に直接書かず board 提案。

    Step 4 リネーム提案 + board + 通知:
      - 全録音について `{月日} 【主体】会議タイトル` を完成 → Discord master に「リネームチェックリスト」
        として投稿(ガクチョが Plaud アプリで手動リネーム。自動リネームはしない=API 不可)。
      - 取り込んだ録音は「📥 取り込み済み(→ soil パス)」を明示(台帳)。
      - 主体に迷った録音は board(pending)に「{録音} の主体確認」を起草し、通知の先頭に立てる。

    べき等性: 同日の processed 記録が既存の録音は再処理しない。soil 既存 meeting は上書きしない。

    注意: 録音内容はクライアント機密 + 個人を含む。scope=master のみ。core_team/LINE には一切出さない。

# === ③ 失敗時 ===
on_failure:
  notify: discord
  note: |
    Plaud MCP 到達不可(OAuth 対話前提のためヘッドレスで落ちる/ token 失効)を最も疑う。
    カレンダー token 失効時は内容のみで判定し続行(精度低下を通知に添える)。
