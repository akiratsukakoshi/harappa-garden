---
type: seed
name: monday-caption-draft
plot: sns_manager
description: 毎週月曜朝、土曜に承認された画像 + ガクチョの一言コメントを起点に、火・土のフィード文案(ガクチョー文体)を作成して board 剪定依頼にする種。承認後に ig_scheduler へ予約。
status: draft
phase: 3a
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-15
created_by: claude (with ガクチョ, セッション45)
last_updated: 2026-06-15
linked_skills:
  - "garden/plots/sns_manager/SKILL.md"   # Mode A2
linked_services:
  - "garden/services/sns-manager/processor.py"

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "30 7 * * 1"          # 毎週月曜 07:30 JST(週次レポート 07:00 の後)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「今週の投稿の文案作って」

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/sns-manager
  timeout_minutes: 20
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
    this_monday: "$(date -d 'monday' +%Y-%m-%d)"          # 今週の月曜(= 投稿週)
    this_tuesday: "$(date -d 'monday + 1 day' +%Y-%m-%dT20:00:00)"   # 火 20:00 投稿
    this_saturday: "$(date -d 'monday + 5 day' +%Y-%m-%dT08:00:00)"  # 土 08:00 投稿
    this_tuesday_jp: "$(date -d 'monday + 1 day' +%-m/%d)"
    this_saturday_jp: "$(date -d 'monday + 5 day' +%-m/%d)"
  prompt: |
    あなたは sns_manager 区画の種「monday-caption-draft」です。

    まず以下3ファイルを Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/sns_manager/SKILL.md(Mode A2 + 文体ルール)
      3. /home/vps-harappa/garden/plots/sns_manager/SNS_STRATEGY.md(文体・3目的)

    今回の動的入力:
      - today: {today}
      - this_monday: {this_monday}(今週 = 投稿週)
      - 火 {this_tuesday_jp} 20:00 投稿 / 土 {this_saturday_jp} 08:00 投稿

    Step 0 セレクト board の確認(★前提):
      - garden/board/{pending,processed}/*-sns-select.md から frontmatter `week: {this_monday}` の board を探す
      - 見つからない or status が approved でない → 文案を作らず、log に `==NOTIFY==` で
        「📝 今週({this_monday}週)の画像セレクトがまだ承認されていません。board を承認いただければ文案を作ります。」を append → exit 0
      - approved の board を読む(画像ファイル名・A/C 割り当て・ガクチョの一言コメント)

    べき等性: 同週の caption board(*-sns-caption.md, frontmatter week: {this_monday})が既存なら skip。

    Step 1 文案作成(★この種の本体。Claude が書く):
      - 火(B 既存共感)・土(A or C、セレクト board の saturday_purpose に従う)の 2 本
      - ⭐ 各画像に付いたガクチョの一言コメントを必ず起点にする(ゼロから創作しない)
      - ガクチョー文体(語尾「〜でございます」等 / 身体感覚の具体描写 / ユーモア・逆張り / 綺麗にまとめすぎない)
      - 150〜300字 + ハッシュタグ 5〜8 個(必ず #原っぱ大学 を含む)
      - 一言コメントが無い画像はスキップし board にその旨を明示

    Step 2 board 起草: garden/board/pending/{today}-sns-caption.md に:
      - frontmatter:
        ---
        type: pruning_request
        from_seed: sns_manager/monday-caption-draft
        week: {this_monday}
        status: pending
        created: {today}T07:30:00+09:00
        posts:
          - day: 火
            purpose: B
            image: (ファイル名)
            image_path: (temp/candidates-{this_monday}/ のローカル絶対パス)
            publish_at: {this_tuesday}
          - day: 土
            purpose: (A or C)
            image: (ファイル名)
            image_path: (ローカル絶対パス)
            publish_at: {this_saturday}
        ---
      - 本文に火・土それぞれの「画像 / 本文 / ハッシュタグ / 投稿日時」
      - 末尾に「承認 = この内容で Instagram + Facebook に予約します(火 20:00 / 土 8:00)」と明記

    Step 3 庭師通知: log に `==NOTIFY==` で append:
      「📝 今週の投稿文案(火 B / 土)ができました → board/pending/{today}-sns-caption.md
        赤入れ・修正して「承認」で Instagram + Facebook に予約します。」

    ⚠️ 承認 = 予約は Mode A2 で Discord ガクコが各投稿について
      {PY} {PROC} schedule --image {image_path} --caption-file <本文ファイル> --publish-at {publish_at}
      を実行(承認前に予約しない)。配信ではないので send_pending には載せない(master/Discord 完結)。
      PY=/home/vps-harappa/garden/services/sns-manager/.venv/bin/python
      PROC=/home/vps-harappa/garden/services/sns-manager/processor.py

    失敗時: on_failure に従い log + fallback 通知。

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-sns-caption.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-sns-caption.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock
    group: master
    template: |
      📝 今週の投稿文案 → board/pending/{today}-sns-caption.md
      修正して「承認」で IG + FB に予約

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: discord_direct
  note: |
    承認は Discord master でガクチョ → ガクコが SKILL Mode A2 に従い、各投稿について
    processor.py schedule(--image / --caption-file / --publish-at)で ig_scheduler + FB に予約 →
    job_id を board に記録 → board を processed/ へ。詳細は SKILL Mode A2。
    schedule 成功時に使った画像の Drive 原本は自動で 使用済み/ サブフォルダへ move される
    (候補置き場に再掲しないため)。差し替えで不採用の候補は残る。

# === ⑥ べき等性 ===
idempotency:
  key: sns-caption-{week}
  guard: 同週の caption board が pending/processed に既存なら skip。予約は job 単位で重複させない。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 1
    backoff: 30m
  fallback:
    via: mock
    group: master
    template: |
      ❌ sns monday-caption-draft 失敗 / 週: {this_monday} / 詳細: {log_path}

# === ⑧ 依存 ===
depends_on:
  state:
    - "garden/services/sns-manager/ デプロイ済 + venv 構築済"
    - "secrets(Meta token / ig_scheduler key)配置済"
    - "前段 saturday-image-select の board が approved(画像 + 一言コメント)"
  seeds:
    - "sns_manager/saturday-image-select"
  # 候補画像のローカルファイル(temp/candidates-{week}/)は土曜の fetch-images で DL 済み

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: null
---

# monday-caption-draft — 月曜の文案作成

## 目的(不変)

土曜に承認された画像と**ガクチョの一言コメント**を起点に、火・土のフィード文案を**ガクチョー文体**で作成する。塚越さんが著者・Garden が整形者の原則を守り、必ず board でガクチョの赤入れ・承認を通してから予約する。

## 現状の方法

frontmatter 参照。要約: 月 07:30 発火 → 承認済セレクト board(画像 + 一言)を読む → Claude が文案 2 本を作成 → board 起草 → Discord 通知 → ガクチョが修正・承認 → ガクコが `processor.py schedule` で IG + FB に予約(火 20:00 / 土 8:00)。

## 関連

- 区画 SKILL: [garden/plots/sns_manager/SKILL.md](../../plots/sns_manager/SKILL.md) Mode A2
- 前段の種: `sns_manager/saturday-image-select`(画像セレクト)

## active 化条件

1. [ ] VPS デプロイ + secrets(Meta / ig_scheduler)
2. [ ] dry-run(schedule --dry-run)GREEN
3. [ ] cron 登録 + 初回月曜発火 → 承認 → 予約まで見届け
