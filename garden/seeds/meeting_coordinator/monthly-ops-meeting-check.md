---
type: seed
name: monthly-ops-meeting-check
plot: meeting_coordinator
description: 前月第3週の月曜日に、翌月5〜9日の平日からガクチョの空き時間を抽出し、運営会議の候補を core_team LINE に投げる種。
status: test                      # cron 登録済。初回自動発火見届けで active
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-27
created_by: codex (with ガクチョ)
last_updated: 2026-06-27
linked_workflows:
  - "[[monthly-cycle]]"
linked_skills:
  - "garden/plots/meeting_coordinator/SKILL.md"
linked_services:
  - "garden/services/meeting-coordinator/processor.py"

trigger:
  type: cron
  schedule: "30 8 15-21 * 1"     # 毎月第3月曜 08:30 JST = 翌月運営会議の調整開始
  timezone: Asia/Tokyo

engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは meeting_coordinator 区画の種「monthly-ops-meeting-check」です。

    まず以下2ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/meeting_coordinator/SKILL.md(Mode 1)

    今回の動的入力:
      - today: {today}

    やること(1コマンドだけ):
      /home/vps-harappa/garden/services/garden-gaku-co/venv/bin/python /home/vps-harappa/garden/services/meeting-coordinator/processor.py monthly-ops --today {today} --month 来月
    を Bash で実行する。候補抽出・state 保存・LINE push は processor が行う。

    実行後:
      - exit 0 + "pushed" が出力されていれば、log に「sent: 月次運営会議調整」と1行追記して終了
      - 失敗(非0 exit / traceback)なら log にエラー全文を残す(番人が拾う)

    べき等性: 同月の open/confirmed な operations_monthly が既にあれば新規作成しない。

outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-meeting-monthly-ops.log

pruning:
  channel: notify_only
  notify:
    via: line
    group: core_team

post_approval: {}

idempotency:
  key: meeting-operations-monthly-next-{YYYY-MM}
  guard: 翌月の open/confirmed state があれば skip

on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ meeting_coordinator monthly-ops-meeting-check 失敗 / 詳細: {log_path}

depends_on:
  state:
    - "meeting-coordinator/.env に LINE / Zoom / Calendar 関連 env を設定済"
    - "garden/services/calendar/token.json が有効"
  seeds: []

audit:
  last_fired: null
  last_outcome: null
---

# monthly-ops-meeting-check — 月次運営会議の調整

## 目的(不変)

毎月の運営会議が自然消滅しないよう、前月第3週の月曜日に候補日を出して core_team LINE で調整を始める。

## 現状の方法

毎月第3月曜 08:30 に発火し、翌月5日〜9日の平日からガクチョの空き時間を抽出する。午前優先、夜も候補可。少佐・ゆーじさんの空きは LINE 返信ベースで集める。確定はガクチョの「確定」で行う。

## active 化条件

1. [x] dry-run で候補抽出と state 作成が通る
2. [x] core_team グループへのテスト通知が通る
3. [x] Zoom URL 発行の本番疎通が通る(7月運営会議)
4. [x] Google Calendar 招待作成が通る(7月運営会議)
5. [x] VPS cron 登録
6. [ ] 初回月次自動発火を見届ける(第3月曜 08:30)
