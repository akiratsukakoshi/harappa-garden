---
type: seed
name: daily-event-brief
plot: field_assistant
description: 毎朝 D+2 にイベントがあれば「企画・担当・参加者名簿サマリ・天気」のブリーフを LINE core_team グループへ送る種(無ければ無言スキップ。通知のみ)
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
  - "garden/plots/field_assistant/SKILL.md"   # Mode 2
linked_services:
  - "garden/services/field-assistant/processor.py"

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 7 * * *"          # 毎朝 07:30 JST。種内で D+2 のイベント有無を判定(イベント駆動の cron 代替)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    target_date: "$(date -d '+2 days' +%Y-%m-%d)"
  prompt: |
    あなたは field_assistant 区画の種「daily-event-brief」です。

    まず以下2ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/field_assistant/SKILL.md(Mode 2)

    今回の動的入力:
      - today: {today}
      - target_date: {target_date}(D+2 = ブリーフ対象の活動日)

    やること(1コマンドだけ):
      /home/vps-harappa/garden/services/field-assistant/.venv/bin/python /home/vps-harappa/garden/services/field-assistant/processor.py brief
    を Bash で実行する(対象日の算出・イベント有無判定・名簿・天気・push はすべて processor が行う)。

    実行後:
      - 出力に "no events" → log に「skipped: no events on {target_date}」と1行(正常)
      - 出力に "pushed" → log に「sent: D-2 ブリーフ {target_date}」と1行
      - 失敗(非0 exit / traceback)なら log にエラー全文を残す(番人が拾う)

    べき等性: 同日 log に sent/skipped 行が既にあれば再実行しない。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-field-brief.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: notify_only
  notify:
    via: line
    group: core_team

# === ⑤ 承認後の振る舞い ===
post_approval: {}

# === ⑥ べき等性 ===
idempotency:
  key: field-brief-{YYYY-MM-DD}
  guard: 同日 log に sent/skipped 行があれば skip

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ field daily-event-brief 失敗 / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "field-assistant/.env に STORES_API_TOKEN + FIELD_LINE_TO + LINE_CORE_TEAM_ACCESS_TOKEN 設定済"
    - "シフトカレンダーに対象月タブが存在"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
---

# daily-event-brief — 活動日 D-2 の当日ブリーフ

## 目的(不変)

活動日の 2 日前の朝に、現場責任者(+ グループ全員)が**当日の全体像を 1 通で把握**できるようにする: 企画タイトル・会場・時間 / 担当 4 役 / 参加者(苗字・子ども・チケット)/ 会場の天気(降水確率・風)。[program-execution](../../soil/workflows/program-execution.md) の「天気判断は前日まで」の手前で材料を揃えるのが狙い。

## 現状の方法

cron 毎朝 07:30 → `processor.py brief` が D+2 のシフトカレンダーを判定。イベントがあれば STORES 名簿 + Open-Meteo 天気を取得して LINE push、無ければ無言スキップ(log のみ)。

## active 化条件

1. [ ] VPS スモーク(dry-run、実イベント日指定)GREEN
2. [ ] ガクチョ 1:1 LINE テスト配信 OK
3. [ ] cron 登録 + 実イベントでの初回発火見届け
