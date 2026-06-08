---
type: seed
name: month-end-reminder
plot: expense_processor
description: 毎月最終日に「カード明細・レシートを input フォルダに置いて」とガクチョにリマインドする種(Drive フォルダ URL つき)。通知のみ・実処理なし。
status: active
phase: 3a                         # Garden 完結(通知のみ)
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-05
created_by: claude (with ガクチョ, セッション35)
last_updated: 2026-06-05
linked_skills:
  - "garden/plots/expense_processor/SKILL.md"   # Mode 1
linked_services: []
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 19 28-31 * *"      # 毎月 28-31 日 19:00 JST → 種内で is_last_day チェックして当日のみ実行
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    next_month_jp: "$(date -d 'next month' +%-m | sed 's/$/月/')"   # 月は $() 内で付与(launcher は値全体が $(...) の時のみ展開)
    today: "$(date +%Y-%m-%d)"
    is_last_day: "$(if [ \"$(date -d 'tomorrow' +%d)\" = \"01\" ]; then echo true; else echo false; fi)"
    drive_folder_id: "$(grep '^EXPENSE_DRIVE_FOLDER_ID=' /home/vps-harappa/garden/services/expense-processor/.env | cut -d= -f2)"   # .env から直引き(launcher は $(...) 形式のみ展開。${VAR} は不可)
  prompt: |
    あなたは expense_processor 区画の種「month-end-reminder」です。

    まず以下2ファイルを Read し、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/expense_processor/SKILL.md(本区画の "Mode 1: Month-end Reminder")

    今回の動的入力:
      - today: {today}
      - is_last_day: {is_last_day}      # crontab `L` 代替。true なら実行・false なら skip
      - next_month_jp: {next_month_jp}
      - drive_folder_id: {drive_folder_id}

    最初に is_last_day を確認:
      - "false" → log に「skipped: not last day」と書いて exit 0
      - "true"  → 以下を続行

    やること: Discord master に **1 通だけ** リマインド通知。**Drive の input フォルダ URL を必ず含める**。
      - input フォルダ URL = https://drive.google.com/drive/folders/{drive_folder_id}
        (drive_folder_id が空なら URL 行は省き「経費フォルダ」と書く + log に warning)
      - 文面(SKILL Mode 1 の例に準拠):
        🧾 来月2日に経費処理します。今月のカード明細(PayPay / イオン)とレシート画像を経費フォルダに置いておいてください。
        📁 {input フォルダ URL}
        空なら処理はスキップします。間に合わなくても「経費まわして」で後からいつでも回せます。

    通知は当面モック化: log の末尾に `==NOTIFY==` ブロックで append(send_pending / morning-briefing が拾う)。

    べき等性: 当月分のリマインドを既に送っていれば(同月 log に該当行があれば)再送しない。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-expense-reminder.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: notify_only             # リマインドのみ。承認待ちではない
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log の ==NOTIFY==
    group: master
    template: |
      🧾 来月2日に経費処理します。カード明細・レシートを経費フォルダに置いてください。
      📁 {drive_folder_url}

# === ⑤ 承認後の振る舞い ===
post_approval: {}                  # 承認不要(通知のみ)

# === ⑥ べき等性 ===
idempotency:
  key: expense-month-end-reminder-{YYYY-MM}
  guard: |
    is_last_day == "false" なら即 skip。
    当月の reminder log が既存なら再送しない。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ expense month-end-reminder 失敗 / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "EXPENSE_DRIVE_FOLDER_ID が .env に設定済(URL 組み立て用)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null         # Phase 2 で cron 登録後に確定
---

# month-end-reminder — 月末の経費フォルダ投入リマインド

## 目的(不変)

翌月2日の自動抽出(`monthly-expense-draft`)に間に合うよう、月末最終日に「今月のカード明細・レシートを input フォルダに置いて」とガクチョにリマインドする。**Drive フォルダ URL を併記**してその場で開けるようにする。通知のみで実処理はしない。

## 現状の方法

frontmatter の `trigger` / `execute` / `pruning` 参照。要約:

1. cron 毎月 28-31 日 19:00 発火 → 種内 `is_last_day` チェックで最終日のみ実行(crontab `L` 代替)
2. CHARTER + expense_processor SKILL(Mode 1)を読んだ Claude Code が、Drive フォルダ URL つきリマインドを Discord master に通知(当面 log の `==NOTIFY==` モック)

## 関連

- 区画 SKILL: [garden/plots/expense_processor/SKILL.md](../../plots/expense_processor/SKILL.md) Mode 1
- 対の種: `expense_processor/monthly-expense-draft`(翌月2日の抽出)

## active 化条件

1. [ ] EXPENSE_DRIVE_FOLDER_ID を .env に配置(Phase 2)
2. [ ] 28-31 日 19:00 cron 登録
3. [ ] 初回モック通知が log に出ることを確認
