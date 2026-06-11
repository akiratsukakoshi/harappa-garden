---
type: seed
name: monthly-furikae-check
plot: field_assistant
description: 毎月末日に当月の月謝未消化者(振替チケット発行対象)を LINE core_team グループへ通知し、名簿ワークブックの全タブをクリアする種(通知のみ。発行作業は STORES 管理画面)
status: draft                     # スモーク + LINE 1:1 テストで test、初回月末見届けで active
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-11
created_by: claude (with ガクチョ, セッション42)
last_updated: 2026-06-11
linked_workflows:
  - "[[monthly-cycle]]"
linked_skills:
  - "garden/plots/field_assistant/SKILL.md"   # Mode 3
linked_services:
  - "garden/services/field-assistant/processor.py"

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 19 28-31 * *"     # 毎月 28-31 日 19:30 JST → processor の --if-last-day で末日のみ実行
  timezone: Asia/Tokyo            # (expense month-end-reminder 19:00 と同型・時間帯は分散)

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    this_month: "$(date +%Y-%m)"
  prompt: |
    あなたは field_assistant 区画の種「monthly-furikae-check」です。

    まず以下2ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/field_assistant/SKILL.md(Mode 3)

    今回の動的入力:
      - today: {today}
      - this_month: {this_month}

    やること(2コマンド、順に):
      1. /home/vps-harappa/garden/services/field-assistant/.venv/bin/python /home/vps-harappa/garden/services/field-assistant/processor.py furikae --if-last-day
      2. 1 が "pushed" を出力した場合のみ:
         /home/vps-harappa/garden/services/field-assistant/.venv/bin/python /home/vps-harappa/garden/services/field-assistant/processor.py clear-sheets
         (名簿ワークブックの月末掃除。furikae が "not last day — skip" なら実行しない)

    実行後:
      - skip → log に「skipped: not last day」
      - 成功 → log に「sent: 月謝チェック {this_month} / cleared sheets」
      - 失敗(非0 exit / traceback)なら log にエラー全文を残す(番人が拾う)

    べき等性: 当月の sent 行が log に既にあれば再実行しない。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-field-furikae.log
  - kind: file
    path: /home/vps-harappa/garden/services/field-assistant/output/月謝振替チェック_{this_month}.csv

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: notify_only            # 通知のみ。振替発行は人間が STORES 管理画面で(API 参照系のみ)
  notify:
    via: line
    group: core_team

# === ⑤ 承認後の振る舞い ===
post_approval: {}

# === ⑥ べき等性 ===
idempotency:
  key: field-furikae-{YYYY-MM}
  guard: --if-last-day で末日以外 skip。当月 sent 行があれば再実行しない

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ field monthly-furikae-check 失敗 / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "field-assistant/.env に STORES_API_TOKEN + FIELD_LINE_TO + LINE_CORE_TEAM_ACCESS_TOKEN + FIELD_ROSTER_SHEET_ID 設定済"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
---

# monthly-furikae-check — 月末の月謝未消化チェック + 名簿シート掃除

## 目的(不変)

月謝会員のうち**当月に月謝を 1 回も消費していない人**(チェックインしても回数券・現地決済のみの人を含む)を月末に漏れなく洗い出し、振替チケット発行(STORES 管理画面での手作業)につなげる。従来「管理画面で一人ずつ確認」していた作業の自動化(storesyoyaku ツールの cron 化 = ガクチョ依頼 S42)。

あわせて名簿ワークブックの全タブを削除し、スプシの増殖と PII の滞留を防ぐ(ガクチョ決定 S42)。

## 現状の方法

cron 28-31 日 19:30 → `processor.py furikae --if-last-day`(末日のみ実行)→ LINE push + 監査 CSV → `clear-sheets`。

## active 化条件

1. [ ] VPS スモーク(`furikae --month {先月} --dry-run`)GREEN
2. [ ] ガクチョ 1:1 LINE テスト配信 OK
3. [ ] cron 登録 + 初回月末(6/30)見届け
