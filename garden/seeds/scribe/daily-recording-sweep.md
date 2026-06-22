---
type: seed
name: daily-recording-sweep
plot: scribe
description: 1日1回、Plaud の新規録音を Google カレンダー × 会議内容 × 過去履歴と照らして主体・会議タイトルを判定し、(1) クライアント関連の会議は soil/clients の該当案件 meetings/ に取り込み(漏れ防止)、(2) 全録音に正規タイトル `MM-DD 【主体】会議タイトル` を提案して Discord master に出す(ガクチョが Plaud アプリで手動リネーム)。リネーム・フォルダ操作は API 不可のため自動化しない(提案のみ)。
status: test                     # S53 手動スイープ GREEN → S54 でブリッジ解決(headless claude -p が Plaud に到達)。active = ローカル cron 初回発火の見届け後
phase: 1
execution_host: local           # ★Plaud MCP トークン(~/.plaud/tokens-mcp.json)を持つローカル WSL でのみ headless 到達可。VPS には置かない(refresh_token ローテートのため所有ホストを1つに固定)。実行は run-local.sh 経由(launcher → soil/board をローカルに書く → VPS へ push)
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
  schedule: "30 7 * * *"           # 毎朝 07:30 JST(朝ブリーフィングの後)。★ローカル WSL の crontab に登録(VPS ではない)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「録音スイープして」「会議録まわして」→ bot が
  #   リクエストマーカーを置く → ローカル poll cron が run-local.sh を実行(scribe service README 参照)

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/tukapontas/harappa-garden   # ★ローカル WSL の repo(Plaud トークン所有ホスト)。.mcp.json / garden/ 相対パスはここ基準
  timeout_minutes: 15
  mcp:                              # S54: launcher が claude -p に MCP フラグを渡す(buildMcpArgs)
    config: ".mcp.json"
    strict: true
    permission_mode: "acceptEdits"  # soil/board の Write/Edit を自動承認(Plaud MCP は allowed_tools で明示許可)
    allowed_tools:
      - "mcp__plaud__list_files"
      - "mcp__plaud__get_note"
      - "mcp__plaud__get_transcript"
      - "mcp__plaud__get_file"
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    # board の住所は VPS 一箇所(/home/vps-harappa/garden/board/pending/)。
    # ローカルでは board を「scribe 内部の一時 outbox」に書き、run-local.sh が VPS へ
    # push したのち outbox を空にする。repo に board コンテンツのディレクトリは持たない。
    outbox: "garden/services/scribe/outbox"
  prompt: |
    あなたは scribe 区画の種「daily-recording-sweep」です。Plaud の録音を取りこぼさず
    soil に収め、正しいタイトルを提案する「会議録の番人」です。

    まず以下を Read し、指示に従ってください:
      1. garden/CHARTER.md
      2. garden/plots/scribe/SKILL.md(Mode D / タイトル表記ルール / 主体判定 / 承認境界)
      3. garden/soil/clients/README.md(Plaud 取り込みの動線 a/b・soil 固定の粒度)

    今回の動的入力:
      - today: {today}
      - outbox: {outbox}

    Step 1 新規録音を拾う(watermark 差分・べき等):
      - state ファイル garden/services/scribe/state/processed.jsonl を読み、処理済み plaud_file_id を確認
        (ファイルが無ければ空=初回)。
      - mcp__plaud__list_files で録音一覧を取得。processed.jsonl に file_id がある録音はスキップ。
      - 念のため、取り込み先候補の soil に同じ plaud_file_id の meeting が既にあれば二重取り込みしない。

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
      - 全録音について `{月日} 【主体】会議タイトル` を完成。
      - ★今回のスイープで新規録音が 1 件も無い(全て processed.jsonl 済)なら board を書かない。
        log に「新規なし: board 書かない」と残して Step 5 へ(空振り通知を出さないため)。
      - 新規録音がある時のみ、digest を board ファイル 1 枚にまとめて
        {outbox}/{today}-recording-sweep.md に書く(run-local.sh が VPS の
        board/pending/ へ push → send_pending が Discord master に投稿)。形式:

        ---
        type: pruning_request
        from_seed: scribe/daily-recording-sweep
        status: pending
        created: {today}T07:30:00+09:00
        ---

        # {today} 録音スイープ

        ## 配信本文

        ```
        🎙️ 録音スイープ {today}

        📥 soil 取り込み(済):
        - {主体} {会議タイトル} → soil パス

        ✏️ リネーム提案(Plaud アプリで手動リネームしてください):
        - Before「{原題}」→ After「{月日} 【主体】会議タイトル」

        ❓ 主体に迷い(要確認):
        - {原題} … {迷った理由}

        (新規録音なし / 全て処理済みなら「新規なし」と一行)
        ```

      - 主体に迷った録音・新規クライアント候補は、上の「❓」に加えて board 本文(配信本文の外)に
        「主体確認の根拠」を残す(ガクチョが後で判断できるように)。
      - べき等性は processed.jsonl(file_id)で担保する。当日同一録音の再処理はしない。
        当日内に後から新規録音が見つかった場合は、その新規分の digest で board を
        書き直してよい(VPS で上書き → send_pending が更新版で再通知。新情報なので再通知は妥当)。
        ローカルに notified_at は存在しない(VPS 側のフラグ)。ここでローカルの notified_at は見ない。

    Step 5 state 追記:
      - 今回処理した各録音を garden/services/scribe/state/processed.jsonl に 1 行 JSON で追記:
        {"plaud_file_id": "...", "date": "MM-DD", "主体": "...", "soil_path": "..."|null, "processed_at": "{today}"}
      - soil 取り込みしなかった(リネーム提案のみ)録音も記録する(soil_path: null)。

    べき等性: processed.jsonl に file_id がある録音は再処理しない。soil 既存 meeting は上書きしない。
    soil/board の書き込みはこの claude -p が行い、VPS への push は run-local.sh が後段で行う(ここでは push しない)。

    注意: 録音内容はクライアント機密 + 個人を含む。scope=master のみ。core_team/LINE には一切出さない。

# === ③ 失敗時 ===
on_failure:
  notify: discord
  note: |
    Plaud MCP 到達不可(token 失効 / ~/.plaud/tokens-mcp.json 無し / 認証ホスト外)を最も疑う。
    カレンダー token 失効時は内容のみで判定し続行(精度低下を通知に添える)。
---

# daily-recording-sweep(scribe / 会議録の番人)

ローカル WSL の crontab から [run-local.sh](../../services/scribe/run-local.sh) 経由で発火する日次の録音スイープ。
launcher が MCP フラグ付きで `claude -p` を起動 → Plaud を読み、soil(meetings)はローカル repo に、
board(digest)は `garden/services/scribe/outbox/` に書く → wrapper(run-local.sh)が soil を VPS へ、
board を VPS `board/pending/` へ push し outbox を空にする → send_pending が Discord master に配信。

> board の住所は VPS 一箇所。repo に board コンテンツのディレクトリは無い(混乱防止)。
> 詳細: [garden/board/README.md](../../board/README.md) 「board の実体はどこにあるか(ホスト)」。

詳細な作法は [scribe SKILL](../../plots/scribe/SKILL.md)(Mode D)。
