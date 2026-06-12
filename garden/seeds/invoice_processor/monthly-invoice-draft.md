---
type: seed
name: monthly-invoice-draft
plot: invoice_processor
description: 毎月12日に Gmail の請求書を取得・解析し、スタッフ照合 + 稼働突合(請求漏れ検出)つきの Freee 登録候補を board 剪定依頼にする種。空ならスキップ通知。手動「請求書まわして」でも同フローが回る。
status: draft
phase: 3a                         # Garden 完結(取得 → board。登録は Mode 2 で承認後)
execution_host: vps
hmc_dependency: none              # Garden services/invoice-processor/ 経由
version: 1
created: 2026-06-10
created_by: claude (with ガクチョ, セッション41)
last_updated: 2026-06-10
linked_skills:
  - "garden/plots/invoice_processor/SKILL.md"   # Mode 1
linked_services:
  - "garden/services/invoice-processor/processor.py"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 12 * *"          # 毎月12日 08:00 JST(ガクチョ指定。前月分の請求書が出揃う頃)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「請求書まわして」→ Discord ガクコが SKILL Mode 1 を on-demand 実行
  #          (遅れて届いた請求書の再処理もこれ。fetch/extract はラベル・Drive 移動でべき等)

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/invoice-processor
  timeout_minutes: 30             # Gemini PDF 解析×件数で 10 分超え(S43 初回発火 exit 143 の教訓)
  computed_inputs:
    target_month: "$(date -d 'last month' +%Y-%m)"        # 前月(12日に処理するのは前月分)
    target_month_jp: "$(date -d 'last month' +%-m月)"      # ⚠️ 月は $() 内で完結(S37/S40 型の未展開バグ防止)
    target_tab: "$(date -d 'last month' +%Y%m)"
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは invoice_processor 区画の種「monthly-invoice-draft」です。

    まず以下2ファイルを Read し、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/invoice_processor/SKILL.md(本区画の "Mode 1: Monthly Draft")

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}(前月 = 処理対象)
      - target_month_jp: {target_month_jp}
      - target_tab: {target_tab}

    べき等性(最初に確認):
      - 同月の board(pending/processed)が既存なら新規発火しない
        グロブ: garden/board/{pending,processed}/*-invoice-draft.md を grep し
        frontmatter `target_month: {target_month}` を含むファイルがあれば log に「skipped: already exists」と書いて exit 0

    ⚠️ コマンドはすべて絶対パス + cd なしで実行(Bash 権限は絶対パス `:*` 形式にのみ scoped allow):
      PY=/home/vps-harappa/garden/services/invoice-processor/.venv/bin/python
      PROC=/home/vps-harappa/garden/services/invoice-processor/processor.py

    Step 1 fetch(Gmail → Drive Inbox):
      {PY} {PROC} fetch
      → 標準出力 `FETCHED_FILES: N`(取得済みスレッドはラベルで自動スキップされる)

    Step 2 extract(解析 + スタッフ照合):
      {PY} {PROC} extract
      → 標準出力の REVIEW_CSV / EXTRACT_ROWS / EXTRACT_STAFF_FILES / EXTRACT_OUTSIDE_FILES を控える

    Step 3 空判定(★重要):
      - EXTRACT_ROWS: 0 → まず {PY} {PROC} external --month {target_month} を実行(★S43。
        請求書ゼロの月でも外部スタッフの稼働分はあり得る):
        - external も 0 行 → board を作らず、log に `==NOTIFY==` で
          「🧾 {target_month_jp}分の請求書、新着がありませんでした。今月は処理なしでスキップします。
          届いたら『請求書まわして』と言ってください。」を append して exit 0
        - external 1 行以上 → {PY} {PROC} to-sheet {EXTERNAL_CSV} --tab {target_tab} でタブを作り
          Step 4 → Step 6 へ(Step 5.5 は済み。board は外部スタッフ分のみと明記)
      - 1 件以上 → Step 4 へ

    Step 4 check(稼働突合 — 請求漏れ検出):
      {PY} {PROC} check --month {target_month}
      → CHECK_MISSING(稼働があるのに請求書が無い業務委託スタッフ)/ NO_WORKTIME_SHEET を控える
      ※ 突合対象 = 稼働シートの区分=業務委託 + soil の invoice_monthly: true(大阪の守田・安藤、
        稼働シート外でも毎月請求が来る)。contract=経営(ガクチョ)は自動除外(S43)。

    Step 5 レビュー用 Sheets 化:
      {PY} {PROC} to-sheet {REVIEW_CSV} --tab {target_tab}
      → REVIEW_SHEET_URL / REVIEW_TAB / REVIEW_ROWS を控える

    Step 5.5 外部スタッフの稼働金額を追記(★S43 新設):
      {PY} {PROC} external --month {target_month} --append-sheet {target_tab}
      → EXTERNAL_ROWS / EXTERNAL_UNMATCHED を控える(稼働シート区分=追加 の人の
        部門別稼働金額をレビュータブ末尾に薄緑で追記。請求書を出さない人の支払い分)
      → NO_WORKTIME_SHEET / 0 行なら何もせず次へ(board にその旨を一行)

    Step 6 board 起草: garden/board/pending/{today}-invoice-draft.md に SKILL Mode 1 Step 6 のとおり:
      - サマリ(スタッフ請求 n名 / リスト外 m件 / 外部スタッフ稼働分 e行 ¥計 / 請求漏れ疑い k名[名前+稼働時間] / 警告 w件)
      - 支払先別の候補一覧(支払先 / 金額 / 勘定科目 / 部門 / グループ)
      - frontmatter に必ず(承認時に from-sheet で読み戻すため):
        ---
        type: pruning_request
        from_seed: invoice_processor/monthly-invoice-draft
        target_month: {target_month}
        status: pending
        created: {today}T08:00:00+09:00
        working_csv: {REVIEW_CSV の絶対パス}
        review_sheet_url: {REVIEW_SHEET_URL}
        review_tab: {target_tab}
        ---
      - ⚠️ 承認 = Freee 登録は Mode 2 で Discord ガクコが from-sheet → dry-run → 本登録。
        配信ではないので send_pending には載せない(master/Discord 完結)。

    Step 7 庭師通知: log に `==NOTIFY==` で append(Sheet URL を必ず含める):
      「🧾 {target_month_jp}分の請求書 {総件数}件を処理(スタッフ {n}名 / リスト外 {m}件 / 外部スタッフ稼働分 {e}行)。
        ⚠️ 稼働があるのに請求書が無い人: {names or なし}
        直接編集できる表 → {REVIEW_SHEET_URL}
        確認して『承認』で Freee 登録します。漏れの人には催促をお願いします。」

    失敗時: fetch/extract が落ちたら on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-invoice-draft.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-invoice-draft.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log の ==NOTIFY==(send-pending が Discord master へ)
    group: master
    template: |
      🧾 {target_month_jp}分の請求書候補 {N}件を board に起草(請求漏れ疑い {k}名)
      → board/pending/{today}-invoice-draft.md
      確認して「承認」で Freee 登録

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct         # send_pending を経由しない。Discord ガクコが SKILL Mode 2 で直接 register
  note: |
    承認は Discord master でガクチョ → ガクコが (1) from-sheet {review_tab} で読み戻し →
    (2) register --dry-run で件数・合計額を提示 → (3) OK で本登録 →
    (4) Gmail 処理済ラベル + Drive Processed 移動(service が自動)+ board を processed/ へ。
    詳細は SKILL Mode 2。

# === ⑥ べき等性 ===
idempotency:
  key: monthly-invoice-draft-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。
    fetch は Invoice_Fetched ラベル、register 済みは 処理済 ラベル + Drive Processed 移動で
    多重処理を防ぐ(手動「請求書まわして」の再実行はマージ安全)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ monthly-invoice-draft 失敗 / 対象月: {target_month} / 詳細: {log_path}
      → 手動で processor.py fetch / extract を確認

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/invoice-processor/ デプロイ済 + venv 構築済"
    - "secrets(user OAuth token[gmail/drive/sheets] / Freee 共有 token / GEMINI_API_KEY)配置済"
    - "INVOICE_REVIEW_SHEET_ID 設定済(⭐ガクチョ: ワークブック作成)"
    - "前月の {target_month}_稼働時間 シート(shift-manager 生成。無ければ突合スキップで続行)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null         # VPS cron 登録後に確定
---

# monthly-invoice-draft — 毎月12日の請求書取得 → 照合 → board 起草

## 目的(不変)

毎月12日(前月分の請求書が出揃う頃)に Gmail の請求書を取得・解析し、**スタッフリスト照合**(リスト外は分ける)と **稼働突合**(稼働があるのに請求書が来ていない業務委託スタッフの検出)つきで Freee 登録候補をガクチョに提示する。**空なら board を作らずスキップ通知**。12日に揃わなくても **手動「請求書まわして」で何度でも安全に回る**。

## 現状の方法

frontmatter 参照。要約:

1. cron 毎月12日 08:00 発火(or 手動声がけ)
2. CHARTER + invoice_processor SKILL(Mode 1)を読んだ Claude Code が:
   a. `processor.py fetch` で Gmail → Drive Inbox
   b. `processor.py extract` で解析 + スタッフ照合(空ならスキップ通知)
   c. `processor.py check` で前月稼働と突合(請求漏れ検出)
   d. `processor.py to-sheet` でレビュー用 Sheets タブ作成
   e. board/pending/ に剪定依頼を起草 + Discord 通知(Sheet URL + 請求漏れリスト)
3. ガクチョが Sheet 確認 → 「承認」→ ガクコが Mode 2 で from-sheet → dry-run → 本登録

## 関連

- 区画 SKILL: [garden/plots/invoice_processor/SKILL.md](../../plots/invoice_processor/SKILL.md) Mode 1 / Mode 2
- Python service: `garden/services/invoice-processor/processor.py`
- 類似の種: `expense_processor/monthly-expense-draft`(同パターンの先行例)

## active 化条件

1. [x] VPS デプロイ(rsync + venv + .env + secrets 600)(S41)
2. [x] ⭐ user OAuth token 発行(issue_token.py → ガクチョ同意 → VPS scp)(S41)
3. [x] ⭐ レビュー用ワークブック作成 → `INVOICE_REVIEW_SHEET_ID`(S41)
4. [x] スモーク検証(Gmail 検索 / Drive Inbox / check 実シート[請求漏れ 7 名検出・0h 除外] / Sheets ラウンドトリップ + launcher --dry-run の `$()` 展開)(S41)
5. [x] 12日 08:00 cron 登録(S41)+ bot.py に「請求書まわして」話題検知配線(S41。Discord 実発話での動作確認は残)
6. [ ] 初回実走(fetch → extract → board → 承認 → Freee 登録の 1 周)→ **active 昇格**
