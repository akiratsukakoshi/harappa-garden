---
type: seed
name: monthly-shift-survey
plot: shift_manager
description: 月初1日に翌月のシフト募集フォームを Garden 内で生成 → board に剪定依頼 → 庭師承認後に staff LINE 配信する種
status: draft                     # 6/1 cron 仕込み + post_approval 経路 + credentials VPS 配置で active へ
phase: 3a                         # Garden 完結化(セッション21 で HMC 依存を撤廃)
execution_host: vps
hmc_dependency: none              # Garden services/shift-manager/ に移植済み(セッション21)
version: 2                        # v1: HMC 直叩き / v2: Garden 完結
created: 2026-05-25
created_by: claude (with ガクチョ, セッション7)
last_updated: 2026-05-30
linked_workflows:
  - "[[monthly-cycle]]"           # ステップ 2(a) 翌月シフトアンケート送信
linked_skills:
  - "garden/plots/shift_manager/SKILL.md"
linked_services:
  - "garden/services/shift-manager/generate_shift_form.py"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 1 * *"           # 毎月1日 08:00 JST
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    target_month: "$(date -d '+1 months' +%Y-%m)"
    target_month_jp: "$(date -d '+1 months' +%-m)月"
    target_year: "$(date -d '+1 months' +%Y)"
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは shift_manager 区画の種「monthly-shift-survey」です。

    まず以下2ファイルを Read で読み込み、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/plots/shift_manager/SKILL.md(本区画の Mode 2)
    SKILL は CHARTER を継承して書かれています。両方を参照してください。

    その上で、SKILL の **"Mode 2: Month-start Survey"** の全 Step(Step 1〜5)に従って、
    {target_year}年{target_month_jp}(= {target_month})のシフト募集フォーム生成と
    board 剪定依頼の起草を行います。

    今回の動的入力:
      - today: {today}
      - target_month: {target_month}(翌月、generate_shift_form.py に渡す)
      - target_month_jp: {target_month_jp}

    操作対象ファイル / コマンド:
      - 月次シート Q列チェック確認: Monthly UI Sheet({target_month} タブ・Q列)
        ※ Q列確認は Google Sheets 側のため、種内では「未確認の前提」で扱い、Step 3 の board に
           「Q列チェック実施済か?」のチェック項目を必ず含める(SKILL Mode 2 Step 1 の判断ルール参照)
      - フォーム生成コマンド:
          .venv/bin/python /home/vps-harappa/garden/services/shift-manager/generate_shift_form.py --month {target_month}
        ※ コマンドが成功すれば最終行に `Shift Form URL: https://...` が出力される
        ※ 失敗時は on_failure に従う
      - board 起草先: /home/vps-harappa/garden/board/pending/{today}-monthly-shift-survey.md
      - log: /home/vps-harappa/garden/log/{today}-monthly-shift-survey.log

    べき等性:
      - 同月の board(pending or processed)が既存なら **新規発火しない**
        グロブ: garden/board/pending/*-monthly-shift-survey.md と garden/board/processed/*-monthly-shift-survey.md を
        ともに grep し、frontmatter `target_month: {target_month}` を含むファイルがあれば
        log に「skipped: already exists」と書いて exit 0
      - フォーム生成は冪等(既存 shift_form_id を上書き)。実行重複は board レイヤで止める

    完了時:
      - board ファイルに frontmatter を必ず含める:
        ---
        type: pruning_request
        from_seed: shift_manager/monthly-shift-survey
        target_month: {target_month}
        form_url: <generate_shift_form.py の出力 URL>
        status: pending
        created: {today}T08:00:00+09:00
        scheduled_send: {today}T19:00:00+09:00   # send_pending.py が この時刻まで待機して staff 配信
        ---
      - 配信本文(編集可)を `## 配信本文` セクション内のコードブロックで囲む(SKILL Mode 2 Step 3 のテンプレ参照)
      - **庭師アクション セクションを board 末尾に必ず追加(S24 統一テンプレ)**:
        ```markdown
        ---

        ## 🌱 庭師アクション(承認 = 配信の発火)

        配信本文を確認・編集後、 **frontmatter の `status:` フィールドを書き換えて保存** してください:

        - `status: pending` → `status: test` に変更 → 保存
          → 約1分以内に **ガクチョ個人 LINE にテスト配信**(本配信前の確認用、何度でも可)
          → status は自動で pending に戻る

        - `status: pending` → `status: approved` に変更 → 保存
          → `scheduled_send` の時刻に **staff グループに本配信**(dummy モード時は Discord master へ流れます)

        - `status: rejected` に変更 → 保存 → 配信せず却下

        ⚠️ 事前確認チェックボックスは備忘録です。 **発火条件は frontmatter の `status:` のみ**。
        ```
      - 庭師通知は当面モック化: log の末尾に `==NOTIFY==` ブロックで append
        「📋 {target_month_jp}シフトアンケートの下書きあります → board/pending/{today}-monthly-shift-survey.md」

    失敗時:
      - generate_shift_form.py が exit !=0 → on_failure に従う
      - Q列が空 = 0 件 target だった場合 → フォームは未更新で警告ログ、board に「Q列未チェックの可能性」と記載 + pending 配置(庭師判断)

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden/board/pending/{today}-monthly-shift-survey.md
  - kind: log
    path: /home/vps-harappa/garden/log/{today}-monthly-shift-survey.log
  # フォーム生成の副作用は Google Forms / Sheets に直接(generate_shift_form.py の責務)

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify       # 配信文確認が要るので「中」の重さ
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log に書き出すだけ(garden-gaku-co/send 連携後に切替)
    # via: gaku-co
    group: master                  # Discord master channel(個人 LINE ではなく Discord)
    template: |
      📋 {target_month_jp}シフトアンケートの下書きあります
      → board/pending/{today}-monthly-shift-survey.md
      確認 → 承認で staff LINE 配信

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co                     # garden-gaku-co/send_pending.py(cron 1分毎)が検知
  endpoint: /send                  # LINE Bot 経由 staff グループ送信
  body:
    group: staff
    require_approval: false        # board 段階で剪定承認済み
    message_from: |
      board ファイルの `## 配信本文` セクション内のコードブロック全文を message として送信。
      フォーム URL を含む。
  on_send_success:
    - board ファイルを garden/board/processed/ へ移動
    - audit.last_outcome = "sent"
    - log に完了記録 + 庭師通知(Discord master)
  on_send_failure:
    - board ファイルは pending 残置
    - audit.last_outcome = "send_failed"
    - 庭師通知(Discord master、エラー詳細つき)

# === ⑥ べき等性 ===
idempotency:
  key: monthly-shift-survey-{target_month}
  guard: |
    garden/board/pending/*-monthly-shift-survey.md または garden/board/processed/*-monthly-shift-survey.md に
    frontmatter `target_month: {target_month}` を含むファイルが既存なら新規発火しない(2重実行防止)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: gaku-co
    group: master
    template: |
      ❌ monthly-shift-survey 失敗
      対象月: {target_month}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で /home/vps-harappa/garden/services/shift-manager/generate_shift_form.py を実行検討

# === ⑧ 依存 ===
depends_on:
  workflow: monthly-cycle
  state:
    - "Monthly UI Sheet の {target_month} タブの Q列(アンケート)が募集対象にチェック済み"
    - "/home/vps-harappa/garden/services/shift-manager/ が稼働(venv + secrets/credentials.json + secrets/token.json)"
    - "garden-gaku-co/send_pending.py(cron 1分毎)が稼働(post_approval 経路、Phase 3a 後半で実装)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-06-01T08:00:00+09:00
---

# monthly-shift-survey — 翌月シフトアンケート(Garden 完結 v2)

## 目的(不変)

毎月1日朝、**翌月の staff LINE グループにシフト募集フォームが届く** 状態を作る。庭師の手作業介入は **配信文の剪定承認の1ステップだけ** に絞る。

## 現状の方法

frontmatter の `execute` / `pruning` / `post_approval` を参照。要約:

1. cron 月初1日 08:00 発火
2. Garden CHARTER + shift_manager SKILL を読み込んだ Claude Code が、Mode 2 の手順に従って:
   a. `garden/services/shift-manager/generate_shift_form.py --month {翌月}` を実行
   b. 生成された Google フォーム URL を取得
   c. `garden/board/pending/{today}-monthly-shift-survey.md` に剪定依頼を起草
3. 庭師がガクコ(Discord master)で通知を受け、board を確認・編集 → status: approved に変更
4. `garden/services/garden-gaku-co/send_pending.py`(cron 1分毎)が approved を検知 → staff LINE 配信

## board ファイルのテンプレ

`garden/board/pending/{today}-monthly-shift-survey.md`:

```markdown
---
type: pruning_request
from_seed: shift_manager/monthly-shift-survey
target_month: 2026-07
form_url: https://docs.google.com/forms/d/.../viewform
status: pending
created: 2026-06-01T08:00:00+09:00
---

# 2026年7月 シフトアンケート 配信下書き

## 配信本文

(↓ ここをスタッフへの LINE 本文として配信します。編集可。コードブロック内の全文を配信します。)

​```
📅 2026年7月のシフト募集のお知らせ
回答期限: 6/10(水) まで
フォーム: https://docs.google.com/forms/.../viewform
不明点は LINE で塚越まで
​```

## 配信先

- group: staff(全スタッフLINE)

## 配信タイミング

- [ ] 今すぐ
- [x] 09:00 に予約
- [ ] その他: ____

## 庭師アクション

**テスト配信(ガクチョ個人 LINE、何度でも繰り返し可)**:
  frontmatter `status: pending` → `test` に変更 → 保存
  → 約1分以内にガクチョ個人 LINE に配信、status は自動で pending に戻る + 末尾に `<!-- test_sent_at: ... -->` 履歴追記

**本配信(staff グループ)**:
  本文を編集して納得したら `status: pending` → `approved` に変更 → 保存
  → `scheduled_send` の時刻(デフォルト 19:00)に staff グループへ配信
  → 配信後 board は `garden/board/processed/` へ移動

**却下**: `status: rejected` に変更 → 保存

**配信タイミング変更**: frontmatter `scheduled_send: 2026-06-01T19:00:00+09:00` を書き換え → 保存(approved の前後どちらでも OK)
```

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 月次シートの Q列チェックが手動 + 誰がいつ入れるか未確定 | Q列入力担当・タイミングの確定 → 自動チェック化 → 種側で「未完了なら処理中断」の自動判定が機能する | **未検証**(monthly-cycle ステップ2(a) と同期) |
| ❓ | post_approval.body.message_from = board ファイル本文 | board ファイルの「配信本文」セクション切り出し規約(コードブロック内 / セクション全体 / frontmatter フィールド)→ コードブロック内採用予定 | **未検証**(send_pending.py 実装と同期) |
| 💡 | 配信は剪定承認後に1回 | 5日経過しても回答が一定数に満たない → リマインド送信種(`monthly-shift-survey-reminder`)を別途 | 構想中 |
| ✋ | Q列の見せ方(スタッフ稼働確認の見せ方とは別議論) | 別種(monthly-working-hours-confirmation)の改善余地表で塚越さん検討中。重複提案禁止 | 検討中(workflow 側で進行) |
| ❓ | 発火時刻 08:00 | 6:30 morning-briefing と同枠に統合? もしくは 9:00 等に遅らせるか? | 未検証 |
| ✋ | HMC 直叩き | セッション21 で Garden 完結化(`garden/services/shift-manager/`) | **済 v2** |

## 関連

- 区画 SKILL: [garden/plots/shift_manager/SKILL.md](../../plots/shift_manager/SKILL.md)
- workflow: [[monthly-cycle]] ステップ2(a)
- Python service: [garden/services/shift-manager/generate_shift_form.py](../../services/shift-manager/generate_shift_form.py)
- 配信経路: [garden/services/garden-gaku-co/](../../services/garden-gaku-co/) `/send`
- ガクコ INTERFACE: [/home/tukapontas/gaku-co5.0/INTERFACE.md](file:///home/tukapontas/gaku-co5.0/INTERFACE.md) `/send` `require_approval`
- 関連種: `shift_manager/month-end-working-hours-prep`(月末・前段準備)

## TODO(本種に固有)

- [ ] **VPS への garden/services/shift-manager/ 配置 + secrets/.env 配置**(ガクチョ作業、手順書要)
- [ ] **garden-gaku-co/send_pending.py 実装**(post_approval 経路、cron 1分毎)
- [ ] **6/1 08:00 cron 仕込み**(`garden/services/launcher/launcher.js` に登録 + crontab 確認)
- [ ] Q列チェック運用の確定(workflow 側依存)
- [ ] 発火時刻の最終決定

## active 化条件

セッション21 で以下を満たせば active へ:

1. [x] **garden/services/shift-manager/ コード移植**(セッション21)
2. [ ] **credentials VPS 配置**(secrets/credentials.json + secrets/token.json + .env)
3. [ ] **send_pending.py 実装**(post_approval 経路)
4. [ ] **6/1 cron 登録**
5. [ ] **dry-run 検証**(`--dry-run` 相当の手動実行で URL 取得確認)
