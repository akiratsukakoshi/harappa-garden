---
type: seed
name: saturday-image-select
plot: sns_manager
description: 毎週土曜朝、ガクチョが金曜までに Google Drive に置いた候補画像から翌週の火(B)・土(A/C)用 2 枚を Garden が意図を汲んで選定し、board 剪定依頼にする種。ガクチョが日曜夜までに編集・一言コメント追記・承認。
status: draft
phase: 3a
execution_host: vps
hmc_dependency: none               # Garden services/sns-manager/ 経由
version: 1
created: 2026-06-15
created_by: claude (with ガクチョ, セッション45)
last_updated: 2026-06-15
linked_skills:
  - "garden/plots/sns_manager/SKILL.md"   # Mode A1
linked_services:
  - "garden/services/sns-manager/processor.py"

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 9 * * 6"            # 毎週土曜 09:00 JST(翌週の火・土の投稿に向けセレクト)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「今週の画像セレクトして」

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/sns-manager
  timeout_minutes: 20             # 画像 DL + Claude の画像 Read 判断
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    next_monday: "$(date -d 'next monday' +%Y-%m-%d)"      # 投稿週の月曜
    next_tuesday: "$(date -d 'next monday + 1 day' +%-m/%d)"
    next_saturday: "$(date -d 'next monday + 5 day' +%-m/%d)"
  prompt: |
    あなたは sns_manager 区画の種「saturday-image-select」です。

    まず以下3ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/sns_manager/SKILL.md(Mode A1 + 文体・3目的)
      3. /home/vps-harappa/garden/plots/sns_manager/SNS_STRATEGY.md(A/B/C 目的の定義)

    今回の動的入力:
      - today: {today}
      - next_monday: {next_monday}(投稿週の月曜)
      - 火曜(B 既存共感)= {next_tuesday} / 土曜(A 新規 or C 哲学・前週と交互)= {next_saturday}

    べき等性(最初に確認):
      - 同週の board(pending/processed)が既存なら新規発火しない:
        garden/board/{pending,processed}/*-sns-select.md を grep し
        frontmatter `week: {next_monday}` を含むファイルがあれば log に「skipped: already exists」と書いて exit 0

    ⚠️ コマンドは絶対パス + cd なしで実行:
      PY=/home/vps-harappa/garden/services/sns-manager/.venv/bin/python
      PROC=/home/vps-harappa/garden/services/sns-manager/processor.py

    Step 1 候補画像を DL:
      {PY} {PROC} fetch-images --week {next_monday}
      → 出力が "no candidate images" の場合は board を作らず、log に `==NOTIFY==` で
        「📸 来週の SNS 候補画像がまだ Drive にありません。金曜までに設置をお願いします。」を append → exit 0
      → "downloaded" なら各画像のローカルパスを控える

    Step 2 画像を見て選定:
      - DL した各画像ファイルを Read で実際に見る
      - 火(B 既存共感 = 参加者・フォロワーが「あの感覚だ」と共鳴する写真)用に 1 枚
      - 土(A 新規獲得 or C 哲学共有。前週と交互 = 直近の processed board の frontmatter `saturday_purpose` を見て今週を決める)用に 1 枚
      - 計 2 枚を選ぶ。候補が 1 枚しかないなら選べた分だけ + board に「候補不足」と明示

    Step 3 board 起草: garden/board/pending/{today}-sns-select.md に:
      - frontmatter(承認時に月曜の文案種が読むため):
        ---
        type: pruning_request
        from_seed: sns_manager/saturday-image-select
        week: {next_monday}
        saturday_purpose: A   # この週の土曜が A か C か(交互判定の結果)
        status: pending
        created: {today}T09:00:00+09:00
        ---
      - 本文に各投稿の「画像ファイル名 / 簡易な描写(何が写っているか)/ 選定理由(なぜこの目的に合うか)」
      - ⭐ ガクチョが各画像に**一言コメント**を書き込む欄を必ず設ける(月曜の文案の起点):
        例)
        ## 火 {next_tuesday}(B: 既存共感)
        - 画像: xxxx.jpg
        - 描写: (Garden の描写)
        - 選定理由: (Garden の理由)
        - 🖊 一言コメント(ガクチョ記入):

    Step 4 庭師通知: log に `==NOTIFY==` で append:
      「📸 来週({next_monday}週)の SNS 画像を 2 枚セレクトしました(火=B / 土={saturday_purpose})。
        → board/pending/{today}-sns-select.md
        画像の差し替え・一言コメントの記入をして「承認」してください(日曜夜まで)。
        月曜朝に承認内容から文案を作ります。」

    失敗時: on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-sns-select.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-sns-select.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # log の ==NOTIFY==(send-pending が Discord master へ)
    group: master
    template: |
      📸 来週の SNS 画像 2 枚をセレクト → board/pending/{today}-sns-select.md
      差し替え・一言コメント記入して「承認」を

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct         # 月曜の monday-caption-draft 種が承認済 board を読んで文案化
  note: |
    承認は Discord master でガクチョが board を編集(画像差し替え・一言コメント追記)→ status: approved。
    月曜 07:30 の monday-caption-draft が approved board を読み、一言コメントを起点に文案を作る。

# === ⑥ べき等性 ===
idempotency:
  key: sns-select-{week}
  guard: 同週(week)の board が pending/processed に既存なら skip

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ sns saturday-image-select 失敗 / 週: {next_monday} / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/sns-manager/ デプロイ済 + venv 構築済"
    - "secrets(SA[Drive read]/ SNS_DRIVE_FOLDER_ID)配置済"
    - "ガクチョが金曜までに SNS_DRIVE_FOLDER_ID のフォルダへ候補画像を設置"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# saturday-image-select — 土曜の画像セレクト

## 目的(不変)

ガクチョの作業を「画像を Drive に置く(金)」と「文案を構成する(月)」に分け、その間の**画像セレクト(複数候補から SNS の意図を汲んで火・土用 2 枚を選ぶ)を Garden が肩代わり**する。選定は必ず board でガクチョの剪定(差し替え・一言コメント・承認)を通す。

## 現状の方法

frontmatter 参照。要約: 土 09:00 発火 → `fetch-images` で Drive 候補を DL → Claude が画像を Read して火(B)・土(A/C 交互)用に 2 枚選定 → board 起草(描写・理由・一言コメント欄)→ Discord 通知 → ガクチョが日曜夜まで編集・承認。

## 関連

- 区画 SKILL: [garden/plots/sns_manager/SKILL.md](../../plots/sns_manager/SKILL.md) Mode A1
- 次段の種: `sns_manager/monday-caption-draft`(承認済 board → 文案)

## active 化条件

1. [ ] VPS デプロイ + venv + secrets(SA / Drive folder)
2. [ ] dry-run(fetch-images で実フォルダの候補 DL)GREEN
3. [ ] cron 登録 + 初回土曜発火 → 承認まで見届け
