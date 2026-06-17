---
type: seed
name: monthly-sales-import
plot: finance
description: 毎月6日に Drive の売上CSV(STORES/Square)を取得・解析し、Freee 振替伝票の登録候補を board 剪定依頼にする種。部門はルール推定(空欄は要レビュー)。空ならスキップ通知。手動「売上記帳まわして」でも同フローが回る。
status: test                     # S47 VPS デプロイ + cron 登録 + launcher dry-run GREEN
phase: 3a                         # Garden 完結(取得 → board。登録は Mode I 承認後)
execution_host: vps
hmc_dependency: none              # Garden services/finance/ 経由
version: 1
created: 2026-06-17
created_by: claude (with ガクチョ, セッション47)
last_updated: 2026-06-17
linked_skills:
  - "garden/plots/finance/SKILL.md"   # Mode I
linked_services:
  - "garden/services/finance/importer.py"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 6 * *"           # 毎月6日 08:00 JST(ガクチョ指定。5日アップ → 6日記帳)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「売上記帳まわして」→ ガクコが SKILL Mode I を on-demand 実行

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/finance
  timeout_minutes: 15
  computed_inputs:
    target_month: "$(date -d 'last month' +%Y-%m)"   # 前月(6日に処理するのは前月の売上)
    target_month_jp: "$(date -d 'last month' +%-m月)"
    target_tab: "$(date -d 'last month' +%Y%m)"
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは finance 区画の種「monthly-sales-import」です。

    まず以下2ファイルを Read し、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/finance/SKILL.md(本区画の "Mode I: 売上記帳")

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}(前月 = 処理対象)
      - target_month_jp: {target_month_jp}
      - target_tab: {target_tab}

    べき等性(最初に確認):
      - 同月の board(pending/processed)が既存なら新規発火しない
        グロブ: garden/board/{pending,processed}/*-sales-import.md を grep し
        frontmatter `target_month: {target_month}` を含むファイルがあれば log に「skipped: already exists」と書いて exit 0

    ⚠️ コマンドはすべて絶対パス + cd なしで実行(Bash 権限は絶対パス `:*` 形式にのみ scoped allow):
      PY=/home/vps-harappa/garden/services/finance/.venv/bin/python
      IMP=/home/vps-harappa/garden/services/finance/importer.py

    Step 1 fetch(Drive → input/):
      {PY} {IMP} fetch
      → 標準出力 `FETCHED_FILES: N`

    Step 2 generate(解析 + 部門ルール推定。★入金ベース = 全行を入金月末に起票):
      {PY} {IMP} generate --month {target_month}
      → 標準出力の REVIEW_CSV / EXTRACT_ROWS / SECTION_MISSING を控える
      ※ --month で取引日時に関係なく {target_month} 月末起票(STORES の前月取引が混ざっても入金月で計上)

    Step 3 空判定(★重要):
      - EXTRACT_ROWS: 0 → board を作らず、log に `==NOTIFY==` で
        「💴 {target_month_jp}分の売上CSV、まだ届いていないようです(input が空)。今月はスキップします。
        Drive にアップしたら『売上記帳まわして』と言ってください。」を append して exit 0
      - 1 件以上 → Step 4 へ

    Step 4 レビュー用 Sheets 化:
      {PY} {IMP} to-sheet {REVIEW_CSV} --tab {target_tab}
      → REVIEW_SHEET_URL / REVIEW_TAB / REVIEW_ROWS を控える(部門列プルダウン・部門空は黄色)

    Step 5 board 起草: garden/board/pending/{today}-sales-import.md に SKILL Mode I のとおり:
      - サマリ(売上 {EXTRACT_ROWS}件 / 合計¥{計} / 部門未設定 {SECTION_MISSING}件)
      - frontmatter に必ず(承認時に from-sheet で読み戻すため):
        ---
        type: pruning_request
        from_seed: finance/monthly-sales-import
        target_month: {target_month}
        status: pending
        created: {today}T08:00:00+09:00
        review_csv: {REVIEW_CSV の絶対パス}
        review_sheet_url: {REVIEW_SHEET_URL}
        review_tab: {target_tab}
        ---
      - ⚠️ 承認 = Freee 記帳は Mode I で Discord ガクコが from-sheet → register --dry-run → 本登録。
        配信ではないので send_pending には載せない(master/Discord 完結)。

    Step 6 庭師通知: log に `==NOTIFY==` で append(Sheet URL を必ず含める):
      「💴 {target_month_jp}分の売上 {EXTRACT_ROWS}件 を記帳候補にしました(部門未設定 {SECTION_MISSING}件は黄色)。
        直接編集できる表 → {REVIEW_SHEET_URL}
        部門を埋めて『承認』で振替伝票を作ります。」

    失敗時: fetch/generate が落ちたら on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-sales-import.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-sales-import.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock
    group: master
    template: |
      💴 {target_month_jp}分の売上 {N}件を記帳候補に起草(部門未設定 {k}件)
      → board/pending/{today}-sales-import.md
      表で部門を埋めて「承認」で振替伝票

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct
  note: |
    承認は Discord master でガクチョ → ガクコが (1) from-sheet {review_tab} で読み戻し →
    (2) register --dry-run で件数・合計を提示 → (3) OK で本登録(manual_journal)→
    (4) Drive 原本を processed へ自動退避 + board を processed/ へ。詳細は SKILL Mode I。

# === ⑥ べき等性 ===
idempotency:
  key: monthly-sales-import-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。
    register 成功後に Drive 原本を processed/YYYYMMDD/ へ退避(再 fetch されない)。
    手動「売上記帳まわして」の再実行はマージ安全(generate は input/ を読むだけ)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ monthly-sales-import 失敗 / 対象月: {target_month} / 詳細: {log_path}
      → 手動で importer.py fetch / generate を確認

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/finance/ デプロイ済 + venv 構築済"
    - "secrets(Freee 共有 token / SA credentials)配置済"
    - "FINANCE_SALES_DRIVE_FOLDER_ID 設定済(⭐ガクチョ: 売上CSVアップ用フォルダ作成 → SA 共有)"
    - "FINANCE_REVIEW_SHEET_ID 設定済(⭐ガクチョ: レビュー用ワークブック作成 → SA Editor 共有)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# monthly-sales-import — 毎月6日の売上CSV取得 → 振替伝票候補 board 起草

## 目的(不変)

毎月6日(ガクチョが5日に売上CSVをアップした翌日)に、Drive の STORES/Square 売上CSVを取得・解析し、月末起票の Freee 振替伝票の登録候補をガクチョに提示する。**部門はルール推定**(当たらなければ空欄でガクチョがレビューで埋める)。**空なら board を作らずスキップ通知**。6日でなくても **手動「売上記帳まわして」で何度でも安全に回る**。

## 現状の方法

frontmatter 参照。要約: cron 6日 08:00 発火 → CHARTER + finance SKILL(Mode I)を読んだ Claude Code が fetch → generate(空ならスキップ通知)→ to-sheet → board 起草 + Discord 通知(Sheet URL)。ガクチョが Sheet で部門を埋め →「承認」→ ガクコが from-sheet → dry-run → 本登録。

## 関連

- 区画 SKILL: [garden/plots/finance/SKILL.md](../../plots/finance/SKILL.md) Mode I
- Python service: `garden/services/finance/importer.py`
- 類似の種: `invoice_processor/monthly-invoice-draft`(同パターンの先行例)

## active 化条件

1. [ ] VPS デプロイ(rsync + venv + .env + secrets 600)
2. [ ] ⭐ Drive 売上フォルダ(`FINANCE_SALES_DRIVE_FOLDER_ID`)+ レビュー WB(`FINANCE_REVIEW_SHEET_ID`)
3. [ ] スモーク(fetch / generate / to-sheet ラウンドトリップ + launcher --dry-run の `$()` 展開)
4. [ ] 6日 08:00 cron 登録 + bot「売上記帳まわして」配線
5. [ ] 初回実走(fetch → board → 承認 → Freee 記帳の1周)→ **active 昇格**
