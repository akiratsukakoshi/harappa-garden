---
type: seed
name: monthly-working-hours-confirmation
plot: shift_manager
description: 月初1日に前月稼働シートの URL + 案内文を staff LINE に送る種(月末 prep の集計実行後が前提)
status: draft                     # 6/1 cron 仕込み + send_pending.py + credentials で active へ
phase: 3a                         # Garden 完結
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-05-30
created_by: claude (with ガクチョ, セッション21)
last_updated: 2026-05-30
linked_workflows:
  - "[[monthly-cycle]]"           # ステップ 2(b) 前月稼働の確認依頼送信
linked_skills:
  - "garden/plots/shift_manager/SKILL.md"
linked_services:
  - "garden/services/shift-manager/generate_working_hours.py"
linked_seeds:
  - "shift_manager/month-end-working-hours-prep"   # 前段:稼働シートを完成させておく必要
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 1 * *"           # 毎月1日 08:00 JST(monthly-shift-survey と同時刻起草、scheduled_send で 19:00 配信)
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    target_month: "$(date -d '-1 month' +%Y-%m)"   # 前月
    target_month_jp: "$(date -d '-1 month' +%-m)月"
    today: "$(date +%Y-%m-%d)"
    deadline: "$(date -d '10 days' +%Y-%m-%d)"     # 月初1日 + 10日 = 11日が当月10日締切に該当
  prompt: |
    あなたは shift_manager 区画の種「monthly-working-hours-confirmation」です。

    まず以下2ファイルを Read で読み込み、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/plots/shift_manager/SKILL.md(本区画の Mode 3)

    その上で、SKILL の **"Mode 3: Month-start Confirmation"** に従って、
    前月({target_month_jp}・{target_month})の稼働確認依頼の配信文を board に起草します。

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}(前月)
      - target_month_jp: {target_month_jp}
      - deadline: 当月10日(配信文に明示)

    重要な前段確認:
      - 前段種(shift_manager/month-end-working-hours-prep)が前月最終日 22:00 に board 起草 →
        庭師承認後に generate_working_hours.py が実行され、Working Hours Sheet に
        `{target_month}_稼働時間` タブが生成されている前提。
      - タブ未生成の場合(garden-mirror から確認できない場合):
        a. board に「前段の稼働表生成が未完了」と記載 + 庭師通知
        b. 自動配信せず pending 配置で停止
      - タブ生成済の場合:
        Working Hours Sheet URL を以下から取得:
          - garden/services/shift-manager/config/config_ids.json の `working_hours_id`
          - URL = https://docs.google.com/spreadsheets/d/{working_hours_id}/edit
          (#gid= 部分は board 起草時にはまだ不明 = 省略可。スタッフはタブを自分で選ぶ)

    操作対象:
      - board 起草先: /home/vps-harappa/garden-mirror/garden/board/pending/{today}-monthly-working-hours-confirmation.md
      - log: /home/vps-harappa/garden-mirror/garden/log/{today}-monthly-working-hours-confirmation.log

    べき等性:
      - 同月の board(pending/processed)が既存なら新規発火しない
        グロブ: garden/board/{pending,processed}/*-monthly-working-hours-confirmation.md を grep し
        frontmatter `target_month: {target_month}` を含むファイルがあれば
        log に「skipped: already exists」と書いて exit 0

    完了時:
      - board ファイルに frontmatter:
        ---
        type: pruning_request
        from_seed: shift_manager/monthly-working-hours-confirmation
        target_month: {target_month}
        working_hours_url: https://docs.google.com/spreadsheets/d/<working_hours_id>/edit
        status: pending
        created: {today}T08:00:00+09:00
        scheduled_send: {today}T19:00:00+09:00   # send_pending.py が この時刻まで待機して staff 配信
        ---

      - 配信本文(編集可)をコードブロックで囲む。テンプレ:
        ```
        📊 {target_month_jp}の稼働時間表ができました

        → <working_hours_url>(該当月のタブ「{target_month}_稼働時間」)

        各自、ご自身の行を確認お願いします。
        締切: {当月10日}まで

        - 業務委託 → 請求書を harappa まで(メール)
        - 給与 → freee で経費精算
        - 外部スタッフ → 交通費は LINE コメントで
        ```

      - 庭師通知は当面モック化: log の末尾に `==NOTIFY==` ブロックで append
        「📊 {target_month_jp}稼働確認の下書きあります → board/pending/{today}-monthly-working-hours-confirmation.md」

    失敗時:
      - working_hours_id が config に未設定 → board に「config_ids.json 未設定」と記載 + pending 配置 + 庭師通知

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden-mirror/garden/board/pending/{today}-monthly-working-hours-confirmation.md
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-monthly-working-hours-confirmation.log

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock
    # via: gaku-co
    group: master
    template: |
      📊 {target_month_jp}稼働確認の下書きあります
      → board/pending/{today}-monthly-working-hours-confirmation.md
      確認 → 承認で staff LINE 配信

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: /send
  body:
    group: staff
    require_approval: false
    message_from: |
      board ファイルの `## 配信本文` セクション内のコードブロック全文を message として送信。
      Working Hours Sheet URL を含む。
  on_send_success:
    - board ファイルを garden/board/processed/ へ移動
    - audit.last_outcome = "sent"
    - 庭師通知(Discord master、完了)
  on_send_failure:
    - board は pending 残置
    - audit.last_outcome = "send_failed"
    - 庭師通知(エラー詳細つき)

# === ⑥ べき等性 ===
idempotency:
  key: monthly-working-hours-confirmation-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: gaku-co
    group: master
    template: |
      ❌ monthly-working-hours-confirmation 失敗
      対象月: {target_month}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で稼働シートを確認して staff LINE 配信検討

# === ⑧ 依存 ===
depends_on:
  workflow: monthly-cycle
  state:
    - "前月の稼働シートタブ {target_month}_稼働時間 が Working Hours Sheet に存在"
    - "/home/vps-harappa/garden/services/shift-manager/config/config_ids.json の working_hours_id 設定済"
    - "garden-gaku-co/send_pending.py が稼働"
  seeds:
    - "shift_manager/month-end-working-hours-prep(前月最終日 22:00、稼働表生成の前段)"

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-06-01T09:00:00+09:00
---

# monthly-working-hours-confirmation — 前月稼働確認(URL 配信)

## 目的(不変)

毎月1日朝、**前月稼働表のスプシ URL** を staff LINE に送り、スタッフが自分の稼働を確認して精算ルートに乗れる状態を作る。庭師の手作業介入は **配信文の剪定承認の1ステップだけ**。

## 現状の方法(セッション21 で URL 方式採用)

1. cron 月初1日 09:00 発火(monthly-shift-survey の 1 時間後)
2. Garden CHARTER + shift_manager SKILL を読み込んだ Claude Code が Mode 3 に従って:
   a. 前段(month-end-working-hours-prep)の集計実行で生成済の稼働シート URL を config から取得
   b. 配信文ドラフト(URL + 案内文 + 3 ルート動線)を board/pending/ に起草
3. 庭師が Discord master で通知を受け、board 確認・編集 → status: approved
4. send_pending.py(cron 1分毎)が approved を検知 → staff LINE 配信

## 採用した見せ方(セッション21 議論)

- **URL 投稿方式** を採用(スプシ URL を staff LINE に投稿)
- 候補から (a) 個別テキスト・(b) 個人タブ権限・(c) スクショ を比較
- (c) スクショ自動化は技術的に可能だがフォント・改ページ問題で6/1までに品質保証が困難
- LINE Bot API は PDF (file) を直接送れず、画像変換も同様の品質リスクあり
- **URL 投稿は「過去月比較もできる」「自分のタブを開ける」など、スクショより便利な側面あり**
- 中長期で (a) 個別送信 + LINE 個人ID 取得後に切り替え検討

## board ファイルのテンプレ

`garden/board/pending/{today}-monthly-working-hours-confirmation.md`:

```markdown
---
type: pruning_request
from_seed: shift_manager/monthly-working-hours-confirmation
target_month: 2026-05
working_hours_url: https://docs.google.com/spreadsheets/d/1nevys4etwvn4NQToetsj6GLAVrtJT4Y4rj5pn30yZ84/edit
status: pending
created: 2026-06-01T09:00:00+09:00
---

# 2026年5月 稼働確認 配信下書き

## 配信本文

(↓ ここをスタッフへの LINE 本文として配信します。編集可。コードブロック内の全文を配信します。)

​```
📊 5月の稼働時間表ができました

→ https://docs.google.com/spreadsheets/d/.../edit(該当月のタブ「2026-05_稼働時間」)

各自、ご自身の行を確認お願いします。
締切: 6/10(水)まで

- 業務委託 → 請求書を harappa まで(メール)
- 給与 → freee で経費精算
- 外部スタッフ → 交通費は LINE コメントで
​```

## 配信先

- group: staff(全スタッフLINE)

## 庭師アクション

**テスト配信(ガクチョ個人 LINE、何度でも繰り返し可)**:
  frontmatter `status: pending` → `test` に変更 → 保存
  → 約1分以内にガクチョ個人 LINE に配信、status は自動で pending に戻る + 末尾に履歴追記

**本配信(staff グループ)**:
  本文を編集して納得したら `status: pending` → `approved` に変更 → 保存
  → `scheduled_send` の時刻(デフォルト 19:00)に staff グループへ配信

**却下**: `status: rejected` に変更 → 保存

**配信タイミング変更**: frontmatter `scheduled_send: 2026-06-01T19:00:00+09:00` を書き換え → 保存
```

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| 💡 | URL 投稿 | 中長期: スタッフ全員 LINE 個人 ID 取得後に (a) 個別送信に切り替え | 構想中 |
| 💡 | スクショ | (c) スクショは PDF 化 + 画像化が技術的に可能。フォント崩れ問題が解決すれば追加可 | **検討済 → 6/1 不採用**(画像変換リスク) |
| 💡 | 締切日表記 | 「当月10日」を動的計算しているが、休日は前倒し等の調整が必要なら slack 対応 | 構想中 |
| 💡 | 3 ルート動線 | 業務委託・給与・外部の境界は `DB_Master_Nicknames` の PaymentType 列。動的に「あなたは業務委託です」と各自に注釈付加は (a) 個別化と同期 | 構想中 |
| ❓ | 配信時刻 09:00 | monthly-shift-survey(08:00) と 1 時間ずれているが、staff の朝の閲覧帯と合うか未検証 | 未検証 |

## 関連

- 区画 SKILL: [garden/plots/shift_manager/SKILL.md](../../plots/shift_manager/SKILL.md)
- workflow: [[monthly-cycle]] ステップ2(b)
- 前段種: [shift_manager/month-end-working-hours-prep](month-end-working-hours-prep.md)(本種の前提となる稼働表生成)
- Python service: [garden/services/shift-manager/generate_working_hours.py](../../services/shift-manager/generate_working_hours.py)
- ガクコ INTERFACE: [/home/tukapontas/gaku-co5.0/INTERFACE.md](file:///home/tukapontas/gaku-co5.0/INTERFACE.md) `/send`

## TODO(本種に固有)

- [ ] **6/1 09:00 cron 仕込み**
- [ ] **send_pending.py 実装**(/send 経路、セッション21 で実装)
- [ ] **前段との順序保証**(5/31 22:00 の月末 prep → 6/1 朝までに庭師承認 + 集計実行 → 6/1 09:00 本種発火)
- [ ] 6/1 当日: 前段の集計実行が間に合わなかった場合の庭師判断(手動で時刻ずらすか / 翌日にするか)

## active 化条件

1. [x] **garden/services/shift-manager/ コード移植**(セッション21)
2. [ ] **credentials VPS 配置**(secrets/credentials.json + .env)
3. [ ] **send_pending.py 実装**
4. [ ] **6/1 09:00 cron 登録**
5. [ ] **前段(month-end-working-hours-prep)の動作確認 + 稼働シートタブ生成済の検証**
