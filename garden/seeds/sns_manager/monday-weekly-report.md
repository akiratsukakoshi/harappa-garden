---
type: seed
name: monday-weekly-report
plot: sns_manager
description: 毎週月曜朝、先週(月〜日)の Meta インサイトを取得して Google スプレッドシートに記録し、週次振り返りレポートを Discord master に通知する種(通知のみ・承認境界なし)。
status: draft
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-15
created_by: claude (with ガクチョ, セッション45)
last_updated: 2026-06-15
linked_skills:
  - "garden/plots/sns_manager/SKILL.md"   # Mode B
linked_services:
  - "garden/services/sns-manager/processor.py"

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 7 * * 1"           # 毎週月曜 07:00 JST(文案 07:30 の前に先週成績を届ける)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「先週の SNS レポート見せて」

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/sns-manager
  timeout_minutes: 15
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは sns_manager 区画の種「monday-weekly-report」です。

    まず以下2ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/sns_manager/SKILL.md(Mode B)

    今回の動的入力:
      - today: {today}

    やること(1コマンドだけ):
      /home/vps-harappa/garden/services/sns-manager/.venv/bin/python \
        /home/vps-harappa/garden/services/sns-manager/processor.py report
    を Bash で実行する。インサイト取得・Sheet 記録・MD 生成は processor が行う(あなたは整形しない)。

    実行後:
      - exit 0 → processor が標準出力した MD レポート全文を、log に `==NOTIFY==` で append
        (先頭に「📊 SNS 週次レポート」を添える)。send-pending が Discord master に流す
      - 失敗(非0 exit / traceback)→ log にエラー全文を残す(番人が拾う)

    べき等性: 同日 log に「==NOTIFY==」のレポート行が既にあれば再実行しない。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-sns-report.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: notify_only            # 通知のみ。承認不要(read-only レポート)
  notify:
    via: mock
    group: master

# === ⑤ 承認後の振る舞い ===
post_approval: {}

# === ⑥ べき等性 ===
idempotency:
  key: sns-report-{today}
  guard: 同日 log にレポート ==NOTIFY== があれば skip

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ sns monday-weekly-report 失敗 / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/sns-manager/ デプロイ済 + venv 構築済"
    - "secrets(Meta token / SA[Sheets write] / SNS_SHEET_ID)配置済"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# monday-weekly-report — 週次振り返りレポート

## 目的(不変)

先週(月〜日)の SNS 成績(リーチ・保存・シェア・フォロワー増減・Reels フォロワー外リーチ率)を毎週月曜朝に自動で届け、次週の投稿判断の材料にする。承認は不要(read-only の通知)。

## 現状の方法

frontmatter 参照。要約: 月 07:00 発火 → `processor.py report`(Meta Insights 取得 → Google スプレッドシート追記 → MD レポート生成)→ Claude が MD を `==NOTIFY==` で Discord master に流す。

## 関連

- 区画 SKILL: [garden/plots/sns_manager/SKILL.md](../../plots/sns_manager/SKILL.md) Mode B
- 同時刻帯の種: `sns_manager/monday-caption-draft`(07:30、レポートの後)

## active 化条件

1. [ ] VPS デプロイ + secrets(Meta / SA / SNS_SHEET_ID)
2. [ ] dry-run(report --dry-run、Sheets 書き込みskip)GREEN
3. [ ] cron 登録 + 初回月曜発火の見届け
