---
type: seed
name: monthly-shift-finalize
plot: shift_manager
description: 毎月8日にシフト募集(翌月分)の回答集計を board に立て、庭師承認後に aggregate_responses.py を発火する種(Mode 4 Step 1。締切7日 → 8日集計 → 10日確定)
status: draft                     # cron 登録 + 初回見届けで active へ
phase: 3a                         # Garden 完結
execution_host: vps
hmc_dependency: none              # Garden services/shift-manager/ 経由
version: 1
created: 2026-06-10
created_by: claude (with ガクチョ, セッション40)
last_updated: 2026-06-10
linked_workflows:
  - "[[monthly-cycle]]"           # ステップ 3 — 8日集計 → 10日シフト確定
linked_skills:
  - "garden/plots/shift_manager/SKILL.md"
linked_services:
  - "garden/services/shift-manager/aggregate_responses.py"
linked_seeds:
  - "shift_manager/monthly-shift-survey"   # 前段:月初1日に翌月分の募集フォームを配信済み
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 8 * *"           # 毎月8日 08:00 JST(アンケート締切 = 7日の翌朝。10日のシフト確定に間に合わせる)
  timezone: Asia/Tokyo
  # 手動ルートもあり: ガクチョが Discord master で「シフト集計まわして」→ ガクコが scoped Bash で
  # aggregate_responses.py を直接実行(遅れ回答の再集計に使う。マージ安全なので何度でも可)

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    target_month: "$(date -d '+1 month' +%Y-%m)"   # 翌月(月初1日に募集した対象月)
    target_month_jp: "$(date -d '+1 month' +%-m月)"   # 月は $() 内で付与(launcher は値全体が $(...) の時のみ展開)
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは shift_manager 区画の種「monthly-shift-finalize」です。

    まず以下2ファイルを Read で読み込み、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/plots/shift_manager/SKILL.md(本区画の Mode 4)

    その上で、SKILL の **"Mode 4: Month-day-10 Finalize"** の Step 1(回答集計)に向けた
    剪定依頼を board に立てます(集計実行は庭師承認後、本種では実行しない)。

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}(翌月 = 月初1日 monthly-shift-survey が募集した対象月)
      - target_month_jp: {target_month_jp}

    操作対象:
      - board 起草先: /home/vps-harappa/garden/board/pending/{today}-monthly-shift-finalize.md
      - log: /home/vps-harappa/garden/log/{today}-monthly-shift-finalize.log
      - 集計コマンド(庭師承認後に発火、本種では実行しない):
          /home/vps-harappa/garden/services/shift-manager/.venv/bin/python /home/vps-harappa/garden/services/shift-manager/aggregate_responses.py --month {target_month}

    前段確認(soft check、blocked にはしない):
      - 同月の monthly-shift-survey board が processed/ に存在するか確認
        (グロブ: garden/board/processed/*-monthly-shift-survey.md で target_month: {target_month})
      - 見つからない場合は board に「⚠️ 前段の募集配信記録が見つからない(手動配信だった可能性)」と
        注記する(集計自体は Forms に回答があれば成立するため、blocked にはしない)

    べき等性:
      - 同月の board(pending/processed)が既存なら **新規発火しない**
        グロブ: garden/board/{pending,processed}/*-monthly-shift-finalize.md を grep し
        frontmatter `target_month: {target_month}` を含むファイルがあれば
        log に「skipped: already exists」と書いて exit 0

    完了時:
      - board ファイルに以下のチェックリストを含む剪定依頼を起草:
        - [ ] 募集フォーム({target_month_jp}分)の回答が出揃っているか確認(締切は昨日 = 7日)
              → 未回答者がいれば LINE で個別リマインドしてから集計でも可(再実行安全 = 既存タブにマージ)
              → 集計後に遅れ回答が来たら、Discord で「シフト集計まわして」と言えば再集計できます
        - [ ] **集計実行(承認)** ← frontmatter status を approved に変更 → 保存

      - frontmatter に必ず含める:
        ---
        type: pruning_request
        from_seed: shift_manager/monthly-shift-finalize
        target_month: {target_month}
        status: pending
        created: {today}T08:00:00+09:00   # 8日 08:00 発火
        execute_command: "/home/vps-harappa/garden/services/shift-manager/.venv/bin/python /home/vps-harappa/garden/services/shift-manager/aggregate_responses.py --month {target_month}"
        ---

      - **庭師アクション セクションを board 末尾に必ず追加(S24 統一テンプレ)**:
        ```markdown
        ---

        ## 🌱 庭師アクション(承認 = 集計実行の発火)

        確認完了後、 **frontmatter の `status:` フィールドを書き換えて保存** してください:

        - `status: pending` → `status: approved` に変更 → 保存
          → 約1分以内に send_pending.py が `aggregate_responses.py --month {target_month}` を発火
          → シフト調整シートの `Shift_Work_{target_month}` タブに NG マトリクスが書き出されます
          → 再実行安全(既存タブの手動行・既存データは保持してマージ)

        - `status: rejected` に変更 → 保存 → 集計実行せず却下

        ⚠️ チェックボックス `[ ]` → `[x]` は備忘録(自分の確認記録)です。 **発火条件は frontmatter の `status:` のみ**。
        ```

      - 庭師通知は当面モック化: log の末尾に `==NOTIFY==` ブロックで append
        「🗓 {target_month_jp}シフトの回答集計、承認お願いします → board/pending/{today}-monthly-shift-finalize.md」

    失敗時:
      - board 書き込み失敗 → on_failure に従う

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-monthly-shift-finalize.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-monthly-shift-finalize.log
  # 集計結果(Shift_Work_{target_month} タブ)は承認後の post_approval 発火で生成

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log(==NOTIFY== は send_pending.py:notify_pending が拾う)
    # via: gaku-co
    group: master
    template: |
      🗓 {target_month_jp}シフトの回答集計、承認お願いします
      → board/pending/{today}-monthly-shift-finalize.md
      承認で Shift_Work_{target_month} タブに NG マトリクス生成

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: shell                  # 配信ではなく集計実行(month-end-working-hours-prep と同経路)
  body:
    command_from: frontmatter.execute_command   # S39 allowlist 準拠(services/ 配下の絶対パス)
    timeout: 300
  on_send_success:
    - board ファイルを garden/board/processed/ へ移動
    - audit.last_outcome = "executed"
    - 庭師通知(Discord master、シフト調整シート URL = config_ids.json の shift_work_id)
    - 以降の人員配置調整(複雑な調整は人手前提)はシフト調整シート上で庭師が実施
  on_send_failure:
    - board は pending 残置
    - audit.last_outcome = "exec_failed"
    - 庭師通知(エラー詳細つき)

# === ⑥ べき等性 ===
idempotency:
  key: monthly-shift-finalize-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。
    集計スクリプト自体も再実行安全(既存タブにマージ)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: gaku-co
    group: master
    template: |
      ❌ monthly-shift-finalize 失敗
      対象月: {target_month}
      理由: {error_summary}
      詳細: {log_path}
      → 手動実行: /home/vps-harappa/garden/services/shift-manager/.venv/bin/python aggregate_responses.py --month {target_month}

# === ⑧ 依存 ===
depends_on:
  workflow: monthly-cycle
  state:
    - "Google Forms(shift_form_id)に {target_month} 分の回答が集まっている"
    - "/home/vps-harappa/garden/services/shift-manager/ が稼働(SA に forms.responses.readonly scope + フォーム共有済)"
    - "garden-gaku-co/send_pending.py(cron 1分毎)が稼働(endpoint: shell サポート済)"
  seeds:
    - "shift_manager/monthly-shift-survey(月初1日、募集フォーム配信の前段)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-07-08T08:00:00+09:00
---

# monthly-shift-finalize — 月初8日 シフト回答集計(Mode 4 Step 1)

## 目的(不変)

毎月8日、月初1日に募集した **翌月シフトの Forms 回答**(締切 = 7日)を集計し、NG マトリクスをシフト調整シートに書き出して「**10日のシフト確定**作業を始められる状態」を作る。複雑な人員配置の調整自体は人手前提(庭師の領分)。庭師の手作業介入は **集計実行の承認1ステップだけ**。

月内の流れ: **1日 アンケート開始 → 7日 締切 → 8日 とりまとめ(本種)→ 10日 シフト確定**

## 現状の方法

frontmatter の `execute` / `pruning` / `post_approval` を参照。要約:

1. cron 毎月8日 08:00 発火
2. Garden CHARTER + shift_manager SKILL を読み込んだ Claude Code が Mode 4 Step 1 に向けて:
   a. 回答出揃い確認 + 集計実行承認のチェックリストを board/pending/ に起草
3. 庭師がガクコ(Discord master)で通知を受け、確認 → status: approved
   (Discord で「集計まわして」でも可 = Mode 5 承認応答ルート)
4. send_pending.py(cron 1分毎)が approved を検知 → `aggregate_responses.py --month {target_month}` を shell 実行
5. `Shift_Work_{target_month}` タブに NG マトリクス(NG=赤・◎=青・ヘッダ固定)生成 → 庭師に URL 通知

## 集計スクリプトの挙動(S37 移植・実証済)

- Google Forms(`shift_form_id`)の回答 → シフト調整シート(`shift_work_id`)の `Shift_Work_{YYYY-MM}` タブ
- 既定 cutoff は前月1日 UTC(翌月募集の回答は前月に集まる前提)
- 回答者名は設問「お名前」優先、無ければ Staff Master の Email→Name で補完
- **既存タブがあれば手動行・既存データを保持してマージ(再実行安全)**
- `--output_suffix _test` で `Shift_Work_{YYYY-MM}_test` タブに書ける(dry-run 相当)
- S37 実績: 7月分 12 件 / 11 名 → `Shift_Work_2026-07` 生成 GREEN

## 手動実行(遅れ回答対応、S40)

アンケートに遅れて回答する人がいるため、cron(8日)以外にいつでも手動で集計・再集計できる:

1. **Discord ルート(推奨)**: ガクチョが master チャンネルで「**シフト集計まわして**」
   (対象月を変えるなら「8月分のシフト集計まわして」)
   → ガクコが scoped Bash で `aggregate_responses.py --month {対象月}` を直接実行し、結果を報告。
   既存タブにマージするので、集計済みの月に遅れ回答を取り込む再実行も安全。
2. **コンソールルート**: `ssh harappa` して
   `/home/vps-harappa/garden/services/shift-manager/.venv/bin/python /home/vps-harappa/garden/services/shift-manager/aggregate_responses.py --month YYYY-MM`

※ 種の再発火(launcher 手動起動)は同月 board のべき等ガードで skip されるため、再集計はコマンド直実行(上記 1 or 2)で行う。

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| 💡 | 回答出揃い確認は庭師の目視 | 種が Forms 回答数 vs 募集対象スタッフ数を突き合わせて「未回答者リスト」を board に自動記載 | 構想中 |
| 💡 | 未回答者リマインドは手動 LINE | staff グループ or 個人 LINE への自動リマインド(LINE 個人 ID 取得後) | 構想中 |
| 💡 | Step 2(精算 3 ルート集約状況の通知) | 業務委託請求書 / freee 精算 / 外部 LINE 申請の到着状況を Discord 通知。invoice_processor の Garden 化後に設計 | 構想中 |
| ✋ | 遅れ回答の取り込み | Discord「シフト集計まわして」で手動再集計(マージ安全) | **実装済 S40** |
| ❓ | 発火時刻 8日 08:00 | 締切(7日)翌朝の発火で回答が出揃うかは初回運用で検証 | 未検証 |

## 関連

- 区画 SKILL: [garden/plots/shift_manager/SKILL.md](../../plots/shift_manager/SKILL.md) Mode 4
- workflow: [[monthly-cycle]] ステップ3
- Python service: [garden/services/shift-manager/aggregate_responses.py](../../services/shift-manager/aggregate_responses.py)
- 前段種: [shift_manager/monthly-shift-survey](monthly-shift-survey.md)(月初1日、募集フォーム配信)

## active 化条件

1. [x] **aggregate_responses.py の Garden 移植 + 実集計実証**(S37、7月分 12件/11名)
2. [x] **send_pending.py の endpoint: shell + allowlist 対応**(S24/S39)
3. [x] **VPS cron 登録**(`0 8 8 * *`、S40)
4. [ ] **初回発火の見届け**(board 起草 → 承認 → 集計 → タブ生成まで)
