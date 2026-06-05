---
type: seed
name: monthly-expense-draft
plot: expense_processor
description: 毎月2日に input フォルダの明細・レシートを抽出し、Freee 登録候補を board 剪定依頼にする種。空ならスキップ通知。手動「経費まわして」でも同フローが回る。
status: draft
phase: 3a                         # Garden 完結(抽出 → board。登録は Mode 3 で承認後)
execution_host: vps
hmc_dependency: none              # Garden services/expense-processor/ 経由(Phase 2 移植後)
version: 1
created: 2026-06-05
created_by: claude (with ガクチョ, セッション35)
last_updated: 2026-06-05
linked_skills:
  - "garden/plots/expense_processor/SKILL.md"   # Mode 2
linked_services:
  - "garden/services/expense-processor/processor.py"   # Phase 2 移植後
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 2 * *"           # 毎月2日 08:00 JST
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「経費まわして」→ Discord ガクコが SKILL Mode 2 を on-demand 実行
  #          (2日に間に合わなくても任意のタイミングで同じフローが回る)

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/expense-processor
  computed_inputs:
    target_month: "$(date +%Y-%m)"          # 当月(= 前月分の明細が出揃うのが2日)
    target_month_jp: "$(date +%-m)月"
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは expense_processor 区画の種「monthly-expense-draft」です。

    まず以下2ファイルを Read し、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/expense_processor/SKILL.md(本区画の "Mode 2: Extract & Draft")

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}
      - target_month_jp: {target_month_jp}

    べき等性(最初に確認):
      - 同月の board(pending/processed)が既存なら新規発火しない
        グロブ: garden/board/{pending,processed}/*-expense-draft.md を grep し
        frontmatter `target_month: {target_month}` を含むファイルがあれば log に「skipped: already exists」と書いて exit 0

    Step 1 抽出:
      cd /home/vps-harappa/garden/services/expense-processor
      .venv/bin/python processor.py extract
      → working/expenses_YYYYMMDD_HHMMSS.csv が生成される(最新のものを使う)

    Step 2 空判定(★重要):
      - 抽出 0 件(中間 CSV のデータ行が 0、または input が空)→ board を作らず、
        log に `==NOTIFY==` で「🧾 {target_month_jp}の経費、input フォルダが空でした。今月は処理なしでスキップします。
        明細が出たら『経費まわして』と言ってください。」を append して exit 0
      - 1 件以上 → Step 3 へ

    Step 3 board 起草: garden/board/pending/{today}-expense-draft.md に SKILL Mode 2 Step 3 のとおり起草:
      - 抽出候補一覧(発生日 / 費目 / 内容 / 金額 / ソース)+ 費目別件数サマリ
      - 要確認フラグ([要確認:日付不明] / 消耗品費フォールバックの疑い)
      - frontmatter に必ず:
        ---
        type: pruning_request
        from_seed: expense_processor/monthly-expense-draft
        target_month: {target_month}
        status: pending
        created: {today}T08:00:00+09:00
        working_csv: /home/vps-harappa/garden/services/expense-processor/working/expenses_XXXXXXXX_XXXXXX.csv
        execute_command: "cd /home/vps-harappa/garden/services/expense-processor && .venv/bin/python processor.py upload {working_csv} --dry-run"
        ---
      - ⚠️ execute_command は **dry-run**。本登録(--dry-run なし)は Mode 3 でガクチョ確認後に Discord ガクコが叩く。
        承認 = 配信ではなく Freee 登録なので send_pending には載せない(master/Discord 完結)。

    Step 4 庭師通知: log に `==NOTIFY==` で append
      「🧾 {target_month_jp}の経費候補、{N}件を board に起草 → board/pending/{today}-expense-draft.md
        費目内訳: …。確認して『承認』で Freee 登録します。」

    失敗時: extract が落ちたら on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-expense-draft.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-expense-draft.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log の ==NOTIFY==
    group: master
    template: |
      🧾 {target_month_jp}の経費候補 {N}件を board に起草
      → board/pending/{today}-expense-draft.md
      確認して「承認」で Freee 登録

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct         # ★ send_pending を経由しない。Discord ガクコ(Claude Code)が SKILL Mode 3 で直接 upload
  note: |
    承認は Discord master でガクチョ → ガクコが (1) working_csv を --dry-run で確認 →
    (2) 件数・合計額をガクチョに提示 → (3) OK で本登録(--dry-run なし)→
    (4) input/中間CSV を proceeded/ にアーカイブ + board を processed/ へ移動。
    詳細は SKILL Mode 3。

# === ⑥ べき等性 ===
idempotency:
  key: monthly-expense-draft-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。
    proceeded/ にアーカイブ済みの明細は再処理しない(upload 成功時に input→proceeded 移動で二重登録防止)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ monthly-expense-draft 失敗 / 対象月: {target_month} / 詳細: {log_path}
      → 手動で processor.py extract を確認

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/expense-processor/ が移植済 + venv 構築済(Phase 2)"
    - "secrets(Freee OAuth / GEMINI_API_KEY / Google Drive OAuth)配置済"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null         # Phase 2 で cron 登録後に確定
---

# monthly-expense-draft — 毎月2日の経費抽出 → board 起草

## 目的(不変)

毎月2日(前月分の明細が出揃うタイミング)に input フォルダの明細・レシートを抽出し、Freee 登録候補を board(剪定依頼)にしてガクチョに提示する。**空なら board を作らず「スキップ」を通知**。2日に間に合わなくても **手動「経費まわして」で任意のタイミングに同じフローが回る**。

## 現状の方法

frontmatter 参照。要約:

1. cron 毎月2日 08:00 発火(or 手動声がけ)
2. CHARTER + expense_processor SKILL(Mode 2)を読んだ Claude Code が:
   a. `processor.py extract` で中間 CSV 生成
   b. 空なら「スキップ」通知、1 件以上なら board/pending/ に候補一覧を起草
3. ガクチョが Discord master で確認 → 「承認」→ Discord ガクコが Mode 3 で dry-run → 本登録(send_pending 非経由)

## 関連

- 区画 SKILL: [garden/plots/expense_processor/SKILL.md](../../plots/expense_processor/SKILL.md) Mode 2 / Mode 3
- 対の種: `expense_processor/month-end-reminder`(月末の投入リマインド)
- Python service: `garden/services/expense-processor/processor.py`(Phase 2 移植)

## active 化条件

1. [ ] Phase 2: service 移植 + secret + venv
2. [ ] dry-run 検証(extract → upload --dry-run)
3. [ ] 2日 08:00 cron 登録
4. [ ] 手動「経費まわして」経路の Discord 動作確認
5. [ ] 初回実走(board → 承認 → Freee 登録)
