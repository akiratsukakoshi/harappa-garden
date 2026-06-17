---
type: seed
name: monthly-data-audit
plot: finance
description: 毎月9日に Freee のデータ整合性を地ならしする種(analyzer の前処理)。部門振り分け漏れ + 未登録明細(口座同期済だが取引化されていない = PL未反映)を検出 → 部門漏れは Sheets レビュー → 承認で PUT 修正。未登録明細は当面検出・報告まで。手動「部門監査まわして」でも回る。
status: test                     # S47 VPS デプロイ + cron 登録 + launcher dry-run GREEN
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-17
created_by: claude (with ガクチョ, セッション47)
last_updated: 2026-06-17
linked_skills:
  - "garden/plots/finance/SKILL.md"   # Mode D
linked_services:
  - "garden/services/finance/auditor.py"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 9 * *"           # 毎月9日 08:00 JST(記帳6日 → 監査9日 → 分析10日 の地ならし役)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「部門監査まわして」「データ整合性チェックして」→ ガクコが Mode D を実行

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/finance
  timeout_minutes: 15
  computed_inputs:
    target_month: "$(date -d 'last month' +%Y-%m)"   # 前月分のデータを整地
    target_month_jp: "$(date -d 'last month' +%-m月)"
    target_tab: "audit$(date -d 'last month' +%Y%m)"
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは finance 区画の種「monthly-data-audit」です。analyzer が走る前に、
    Freee のデータ整合性をある程度自動で整える「地ならし役」です(ガクチョ S47 役割定義)。

    まず以下2ファイルを Read し、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/finance/SKILL.md(本区画の "Mode D: データ整合性の地ならし")

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}(前月 = 整地対象)
      - target_month_jp: {target_month_jp}
      - target_tab: {target_tab}

    べき等性: 同月の board(pending/processed)*-data-audit.md が既存なら
      log に「skipped: already exists」を書いて exit 0。

    ⚠️ コマンドは絶対パス + cd なし:
      PY=/home/vps-harappa/garden/services/finance/.venv/bin/python
      AUD=/home/vps-harappa/garden/services/finance/auditor.py

    Step 1 scan(部門漏れ + 未登録明細):
      {PY} {AUD} scan --month {target_month}
      → AUDIT_MISSING / AUDIT_CSV / UNREGISTERED_TXNS / UNREGISTERED_STATUS_BREAKDOWN を控える
      ※ 未登録明細(wallet_txns)の status 内訳は初回キャリブレーション材料。必ず board に残す。

    Step 2 判定:
      - AUDIT_MISSING: 0 かつ UNREGISTERED_TXNS: 0 → board を作らず log に `==NOTIFY==` で
        「✅ {target_month_jp}分のデータ整合性 OK(部門漏れ0・未登録明細0)。analyzer はクリーンな状態で走れます。」
        を append して exit 0
      - どちらか 1 以上 → Step 3 へ

    Step 3 部門漏れがあれば Sheets 化(AUDIT_MISSING >= 1 のとき):
      {PY} {AUD} to-sheet {AUDIT_CSV} --tab {target_tab}
      → REVIEW_SHEET_URL / REVIEW_TAB を控える(部門列プルダウン・空は黄色)

    Step 4 board 起草: garden/board/pending/{today}-data-audit.md に:
      - サマリ(部門未設定 {AUDIT_MISSING}件 / 未登録明細 {UNREGISTERED_TXNS}件[PL未反映])
      - 未登録明細の status 内訳(初回はここを見て『どの status が未登録か』をガクチョと確定する)
      - frontmatter(部門漏れがある場合、承認時に from-sheet で読み戻すため):
        ---
        type: pruning_request
        from_seed: finance/monthly-data-audit
        target_month: {target_month}
        status: pending
        created: {today}T08:00:00+09:00
        review_csv: {AUDIT_CSV の絶対パス}
        review_sheet_url: {REVIEW_SHEET_URL}
        review_tab: {target_tab}
        ---
      - ⚠️ 部門の一括修正(PUT)は破壊的・ロールバック無し。承認 = Mode D で from-sheet →
        apply --dry-run → 本適用。未登録明細の自動登録は当面しない(検出・報告のみ)。

    Step 5 庭師通知: log に `==NOTIFY==` で append:
      「🔧 {target_month_jp}分のデータ整合性: 部門未設定 {AUDIT_MISSING}件 / 未登録明細 {UNREGISTERED_TXNS}件。
        {部門漏れがあれば→ 表で部門を埋めて『承認』で反映: {REVIEW_SHEET_URL}}
        {未登録明細があれば→ 取引化されていない口座のお金の動きが {U}件あります(board 参照)。}」

    失敗時: scan が落ちたら on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-data-audit.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-data-audit.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock
    group: master
    template: |
      🔧 {target_month_jp}分のデータ整合性: 部門未設定 {m}件 / 未登録明細 {u}件
      → board/pending/{today}-data-audit.md
      部門は表を埋めて「承認」で反映(PUT)

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct
  note: |
    承認は Discord master でガクチョ → ガクコが (1) from-sheet {review_tab} で読み戻し →
    (2) apply --dry-run で各行の部門を提示 → (3) OK で本適用(PUT /deals。ロールバック無し)→
    (4) board を processed/ へ。未登録明細の自動登録は当面しない(SKILL Mode D の TODO)。

# === ⑥ べき等性 ===
idempotency:
  key: monthly-data-audit-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。
    scan は read-only でべき等。apply は部門 ID を上書きするだけなので再実行マージ安全
    (同じ部門を再設定するだけ)。手動「部門監査まわして」も安全。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ monthly-data-audit 失敗 / 対象月: {target_month} / 詳細: {log_path}
      → 手動で auditor.py scan --month {target_month} を確認

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/finance/ デプロイ済 + venv 構築済"
    - "secrets(Freee 共有 token / SA credentials)配置済"
    - "FINANCE_REVIEW_SHEET_ID 設定済"
  seeds:
    - "finance/monthly-sales-import(6日。記帳後に整地するのが理想だが、承認が遅れていても scan は走る)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# monthly-data-audit — 毎月9日のデータ整合性の地ならし(analyzer 前処理)

## 目的(不変)

毎月9日(記帳6日 → 監査9日 → 分析10日)に、Freee のデータ整合性をある程度自動で整える。**部門振り分け漏れ**と**未登録明細**(口座と同期済みだが取引化されていない = PL に未反映のお金の動き)を検出し、部門漏れはガクチョの承認で一括修正、未登録明細は当面検出・報告する。これにより 10日の analyzer がクリーンなデータで着地予測・戦略議論できる状態にする。

## 現状の方法

frontmatter 参照。要約: cron 9日 08:00 発火 → CHARTER + finance SKILL(Mode D)を読んだ Claude Code が scan(部門漏れ + 未登録明細)→ 漏れゼロ・未登録ゼロなら「整合 OK」通知でスキップ → どちらかあれば部門漏れを to-sheet + board 起草 + Discord 通知。ガクチョが部門を埋め →「承認」→ ガクコが from-sheet → apply --dry-run → 本適用(PUT)。

## ⚠️ 初回キャリブレーション

未登録明細(`wallet_txns`)の `status` の**どの値が「未登録(取引化されていない)」か**は初回 scan の status 内訳を実データで見て確定する。確定後 `auditor.py _scan_unregistered` に filter を入れる。それまでは全明細の内訳を board に出してガクチョと境界を決める。

## 関連

- 区画 SKILL: [garden/plots/finance/SKILL.md](../../plots/finance/SKILL.md) Mode D
- Python service: `garden/services/finance/auditor.py`

## active 化条件

1. [ ] VPS デプロイ + secrets + レビュー WB
2. [ ] スモーク(scan 実 API[部門漏れ + 未登録明細 status 内訳]/ to-sheet ラウンドトリップ / apply --dry-run / launcher --dry-run)
3. [ ] 9日 08:00 cron 登録 + bot「部門監査まわして」配線
4. [ ] 初回実走(scan → board → 承認 → PUT の1周 + 未登録明細 status 確定)→ **active 昇格**
