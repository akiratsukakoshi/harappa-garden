---
type: seed
name: weekly-prep-reminder
plot: field_assistant
description: 毎週月曜朝に、当該週の現場責任者へ準備チェック + 翌週の企画者へ企画MTG確認を LINE core_team グループにメンション通知する種(通知のみ・承認境界なし)
status: draft                     # スモーク + LINE 1:1 テストで test、グループ投入 + 初回見届けで active
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-11
created_by: claude (with ガクチョ, セッション42)
last_updated: 2026-06-11
linked_workflows:
  - "[[program-execution]]"
linked_skills:
  - "garden/plots/field_assistant/SKILL.md"   # Mode 1
linked_services:
  - "garden/services/field-assistant/processor.py"

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "10 8 * * 1"          # 毎週月曜 08:10 JST(ガクチョ「8時前後」指定。08:00 帯の月次種と分散)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは field_assistant 区画の種「weekly-prep-reminder」です。

    まず以下2ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/field_assistant/SKILL.md(Mode 1)

    今回の動的入力:
      - today: {today}

    やること(1コマンドだけ):
      /home/vps-harappa/garden/services/field-assistant/.venv/bin/python /home/vps-harappa/garden/services/field-assistant/processor.py weekly
    を Bash で実行する。本文の組み立て・LINE push は processor が行う(あなたは整形しない)。

    実行後:
      - exit 0 + "pushed" が出力されていれば、log に「sent: 週初めリマインド」と1行追記して終了
      - 失敗(非0 exit / traceback)なら log にエラー全文を残す(番人が拾う)

    べき等性: 同日 log に sent 行が既にあれば再実行しない。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-field-weekly.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: notify_only            # 通知のみ。承認不要(read-only 区画)
  notify:
    via: line                     # LINE core_team グループ(投入前は FIELD_LINE_TO のテスト宛先)
    group: core_team

# === ⑤ 承認後の振る舞い ===
post_approval: {}

# === ⑥ べき等性 ===
idempotency:
  key: field-weekly-{YYYY-MM-DD}
  guard: 同日 log に sent 行があれば skip

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ field weekly-prep-reminder 失敗 / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "field-assistant/.env に FIELD_LINE_TO + LINE_CORE_TEAM_ACCESS_TOKEN 設定済"
    - "シフトカレンダー(Monthly UI Sheet)に当月タブが存在"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
---

# weekly-prep-reminder — 週初めの準備リマインド

## 目的(不変)

[program-execution](../../soil/workflows/program-execution.md) の準備(物品・スタッフスレ・体験者案内・天気判断)と企画MTG(開催2週前)を、現場責任者・企画者へ**担当が自分だと分かる形(メンション)**で毎週月曜に思い出させる。準備忘れ・確認漏れの防止が唯一の目的。

## 現状の方法

cron 月曜 08:10 → `processor.py weekly` がシフトカレンダー(当該週 + 翌週)を読み、LINE core_team グループへ push。企画MTG確認は**リマインドのみ(完了判定しない)** = ガクチョ決定 S42。

## active 化条件

1. [ ] VPS スモーク(dry-run)GREEN
2. [ ] ガクチョ 1:1 LINE テスト配信 OK
3. [ ] cron 登録 + 初回月曜発火の見届け
