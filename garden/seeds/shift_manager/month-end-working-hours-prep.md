---
type: seed
name: month-end-working-hours-prep
plot: shift_manager
description: 月末最終日に当月稼働表のチェックリストを board に立て、庭師承認後に generate_working_hours.py を発火する種
status: draft
phase: 3a                         # Garden 完結
execution_host: vps
hmc_dependency: none              # Garden services/shift-manager/ 経由
version: 1
created: 2026-05-30
created_by: claude (with ガクチョ, セッション21)
last_updated: 2026-05-30
linked_workflows:
  - "[[monthly-cycle]]"           # ステップ 1 月末 — 当月稼働表の作成
linked_skills:
  - "garden/plots/shift_manager/SKILL.md"
linked_services:
  - "garden/services/shift-manager/generate_working_hours.py"
linked_concepts:
  - "[[kodomon]]"                 # 放サボ稼働のソース

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 22 L * *"          # 毎月最終日 22:00 JST(crontab `L` が VPS で動かなければ workaround あり、後述)
  # workaround: `0 22 28-31 * *` で起動 → 種内で「明日が翌月か」チェックして当日のみ実行
  timezone: Asia/Tokyo

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden-mirror
  computed_inputs:
    target_month: "$(date +%Y-%m)"          # 当月
    target_month_jp: "$(date +%-m)月"
    today: "$(date +%Y-%m-%d)"
    tomorrow: "$(date -d 'tomorrow' +%Y-%m-%d)"
    is_last_day: "$(if [ \"$(date -d 'tomorrow' +%d)\" = \"01\" ]; then echo true; else echo false; fi)"
  prompt: |
    あなたは shift_manager 区画の種「month-end-working-hours-prep」です。

    まず以下2ファイルを Read で読み込み、両方の指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)
      2. /home/vps-harappa/garden/plots/shift_manager/SKILL.md(本区画の Mode 1)

    その上で、SKILL の **"Mode 1: Month-end Preparation"** の全 Step(Step 1〜3)に従って、
    {target_month}({target_month_jp})の稼働表チェックリストを board に立てます。

    今回の動的入力:
      - today: {today}
      - tomorrow: {tomorrow}
      - is_last_day: {is_last_day}    # crontab `L` workaround 用、true なら実行・false なら skip
      - target_month: {target_month}
      - target_month_jp: {target_month_jp}

    最初に is_last_day を確認:
      - is_last_day == "false" → log に「skipped: not last day」と書いて exit 0
      - is_last_day == "true" → 以下を続行

    操作対象:
      - 月次シート: Monthly UI Sheet({target_month} タブ)
      - board 起草先: /home/vps-harappa/garden-mirror/garden/board/pending/{today}-working-hours-prep.md
      - 集計コマンド(庭師承認後に発火、本種では実行しない):
          .venv/bin/python /home/vps-harappa/garden/services/shift-manager/generate_working_hours.py --month {target_month}

    べき等性:
      - 同月の board(pending/processed)が既存なら **新規発火しない**
        グロブ: garden/board/{pending,processed}/*-working-hours-prep.md を grep し
        frontmatter `target_month: {target_month}` を含むファイルがあれば
        log に「skipped: already exists」と書いて exit 0

    完了時:
      - board ファイルに以下のチェックリストを含む剪定依頼を起草:
        - [ ] 月次カレンダー Sheet 点検
          - 開催されなかった日程が残っていないか
          - 稼働時間とスタッフ名の誤りがないか
          - 突き合わせ先: Notion フィールドレポート + 運営LINE
        - [ ] [[kodomon]] 勤怠 CSV エクスポート + 配置 (garden-mirror/garden/inbox/kodomon/{当月}.csv に置く)
              → 集計実行時に自動取り込み(放サボセルに業務時間が入る)
        - [ ] **翌日 monthly-shift-survey の対象月タブ(月末から +2 ヶ月先 = Mode 2 から見て翌月)の Q列(アンケート)チェック確認**
              → TRUE が立っている募集対象プログラムが正しいか確認(空のままだと翌朝の shift-survey が「No events selected」で空振り)
              → 動的に計算: target_month の年月から +2 ヶ月(例: 当月=2026-05 なら 2026-07 タブ)
        - [ ] すべての項目確認完了(備忘録 = 自分の確認記録用)

      - frontmatter に必ず含める:
        ---
        type: pruning_request
        from_seed: shift_manager/month-end-working-hours-prep
        target_month: {target_month}
        status: pending
        created: {today}T22:00:00+09:00
        execute_command: "/home/vps-harappa/garden/services/shift-manager/run_month_end_collect.sh {target_month}"
        ---

      - **庭師アクション セクションを board 末尾に必ず追加(S24 統一テンプレ)**:
        ```markdown
        ---

        ## 🌱 庭師アクション(承認 = 集計実行の発火)

        チェックリストの確認完了後、 **frontmatter の `status:` フィールドを書き換えて保存** してください:

        - `status: pending` → `status: approved` に変更 → 保存
          → 約1分以内に send_pending.py が `generate_working_hours.py --month {target_month}` を発火
          → 成功時、自動で `monthly-working-hours-confirmation` board の blocked が外れて配信予約に進む

        - `status: rejected` に変更 → 保存 → 集計実行せず却下

        ⚠️ チェックボックス `[ ]` → `[x]` は備忘録(自分の確認記録)です。 **発火条件は frontmatter の `status:` のみ**。
        ```

      - 庭師通知は当面モック化: log の末尾に `==NOTIFY==` ブロックで append
        「📊 {target_month_jp}稼働表のチェックお願いします → board/pending/{today}-working-hours-prep.md」

    失敗時:
      - board 書き込み失敗 → on_failure に従う

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: /home/vps-harappa/garden-mirror/garden/board/pending/{today}-working-hours-prep.md
  - kind: log
    path: /home/vps-harappa/garden-mirror/garden/log/{today}-working-hours-prep.log
  # 集計結果(Working Hours Sheet)は送信後の post_approval 発火で更新

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify       # チェック作業 + 集計実行承認、確認重い
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: mock                      # 当面: log
    # via: gaku-co
    group: master
    template: |
      📊 {target_month_jp}稼働表のチェックお願いします
      → board/pending/{today}-working-hours-prep.md
      チェック完了 + 「集計実行」承認で稼働表生成

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: shell                  # /send ではなく shell 実行(本種は配信ではなく集計実行)
  body:
    command_from: frontmatter.execute_command   # board frontmatter に書かれたコマンドを実行
    timeout: 300                                # 5分(API quota 待ちを考慮)
  on_send_success:
    - 標準出力から Working Hours Sheet URL を抽出 → board frontmatter `result_url` に追記
    - board ファイルを garden/board/processed/ へ移動
    - audit.last_outcome = "executed"
    - 庭師通知(Discord master、URL つき)+ 放サボ列の手入力依頼
  on_send_failure:
    - board は pending 残置
    - audit.last_outcome = "exec_failed"
    - 庭師通知(エラー詳細つき)

# === ⑥ べき等性 ===
idempotency:
  key: month-end-working-hours-prep-{target_month}
  guard: |
    同月の board(pending/processed)が既存なら新規発火しない。
    is_last_day == "false" なら即 skip(crontab `L` workaround)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: gaku-co
    group: master
    template: |
      ❌ month-end-working-hours-prep 失敗
      対象月: {target_month}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で /home/vps-harappa/garden/services/shift-manager/generate_working_hours.py 実行検討

# === ⑧ 依存 ===
depends_on:
  workflow: monthly-cycle
  state:
    - "Monthly UI Sheet の {target_month} タブが全フィールド開催後の値で完成している"
    - "/home/vps-harappa/garden/services/shift-manager/ が稼働"
    - "garden-gaku-co/send_pending.py(cron 1分毎)が稼働(post_approval 経路の shell サポート要)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-05-31T22:00:00+09:00
---

# month-end-working-hours-prep — 月末稼働表の準備

## 目的(不変)

翌月1日朝の「稼働確認依頼」で使う **当月稼働表** を完成させる前段として、庭師に「チェック → 集計実行」を促すチェックリストを月末最終日 22:00 に board に立てる。集計実行は庭師承認後。

## 現状の方法

frontmatter の `execute` / `pruning` / `post_approval` を参照。要約:

1. cron 毎月最終日 22:00 発火(crontab `L` or `28-31 * *` + 種内 is_last_day チェック)
2. Garden CHARTER + shift_manager SKILL を読み込んだ Claude Code が Mode 1 に従って:
   a. 当月稼働表のチェックリスト(月次シート点検 + 放サボ反映 + 集計実行承認)を board/pending/ に起草
3. 庭師がガクコ(Discord master)で通知を受け、チェック完了 + `[x] 集計実行` を承認
4. send_pending.py(cron 1分毎)が approved を検知 → `generate_working_hours.py --month {target_month}` を shell 実行
5. 結果 Sheet URL を庭師に通知 + 放サボ列(オレンジセル)の手入力依頼

## board ファイルのテンプレ

`garden/board/pending/{today}-working-hours-prep.md`:

```markdown
---
type: pruning_request
from_seed: shift_manager/month-end-working-hours-prep
target_month: 2026-05
status: pending
created: 2026-05-31T22:00:00+09:00
execute_command: "/home/vps-harappa/garden/services/shift-manager/.venv/bin/python /home/vps-harappa/garden/services/shift-manager/generate_working_hours.py --month 2026-05"
---

# 2026年5月 稼働表 準備チェックリスト

## チェックリスト

- [ ] 月次カレンダー Sheet({target_month} タブ)点検
  - 開催されなかった日程が残っていないか
  - 稼働時間とスタッフ名の誤りがないか
  - 突き合わせ先: [Notion フィールドレポート](https://www.notion.so/5dab98a40ae443849e3804c0b431abe2) + 運営LINE
- [ ] [[kodomon]] 勤怠 CSV エクスポート + 所定パスに配置:
  - 配置先: `/home/vps-harappa/garden-mirror/garden/inbox/kodomon/{当月 YYYY-MM}.csv`
  - 例: 5月分なら `garden-mirror/garden/inbox/kodomon/2026-05.csv`
  - エンコーディング: Shift-JIS(コドモン書き出し既定)
  - 集計実行時に **自動取り込み** されます(放サボ列のオレンジセルに業務時間が入る)
  - CSV が無い場合は警告のみで続行(放サボ列は手入力のまま)
- [ ] **翌日 monthly-shift-survey の対象月タブ(月末から +2 ヶ月先 = Mode 2 から見て翌月)の Q列(アンケート)チェック確認** ← 明日 8:00 の monthly-shift-survey が見にいくタブ
  - 例: 当月 2026-05 → 2026-07 タブの Q列に募集対象プログラムが TRUE になっているか
  - 空のままだと翌朝の monthly-shift-survey が「No events selected」で空振り(エラーにはならず、フォームが更新されない)
- [ ] **集計実行(承認)** ← この行を `[x]` にして status を approved に変更 → 保存

## 庭師アクション

すべてのチェックが完了したら:
1. 「集計実行(承認)」 を `[x]` にする
2. frontmatter `status: pending` → `approved` に変更
3. 保存

→ send_pending.py が検知して generate_working_hours.py を発火、URL を Discord master に通知
```

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | Notion 突き合わせは目視 | Notion MCP 開放済(2026-05-23)。突き合わせの一部自動化候補 | 未検証 |
| ❓ | 運営 LINE 突き合わせも目視 | 運営LINE 取り込み手段が未確立(将来 ガクコ `/queue` 経由?) | 構想中 |
| ✋ | [[kodomon]] CSV 手入力 | CSV パーサ実装で自動化(garden/services/shift-manager/import_kodomon.py)。コドモン API/MCP は未調査だが、ガクチョが CSV を所定パスに置けば自動取り込み | **実装済 セッション21** |
| 💡 | チェックリストの粒度 | 「全プログラムごとに点検済」リストを動的生成(月次シートの行数 × プログラム数) | 構想中 |
| ❓ | 発火時刻 22:00 | 月末日のフィールド最終時間と被らないか?(早朝にする選択肢) | 未検証 |
| ❓ | crontab `L` の対応 | VPS の cron 実装が `L` をサポートしていない場合 `28-31` + 種内チェックに切替 | **未検証**(セッション21 で要確認) |

## 関連

- 区画 SKILL: [garden/plots/shift_manager/SKILL.md](../../plots/shift_manager/SKILL.md)
- workflow: [[monthly-cycle]] ステップ1
- Python service: [garden/services/shift-manager/generate_working_hours.py](../../services/shift-manager/generate_working_hours.py)
- 関連種: `shift_manager/monthly-working-hours-confirmation`(本種で完成した稼働表を 翌月1日朝にスタッフ配信、構想中)

## TODO(本種に固有)

- [ ] **VPS cron の `L` サポート確認**(workaround 採否判断)
- [ ] **send_pending.py の `endpoint: shell` 対応**(generate_working_hours.py 実行経路)
- [ ] **5/31 22:00 cron 仕込み**(本セッション内)
- [ ] **dry-run 検証**(generate_working_hours.py の手動実行で URL 取得確認)

## active 化条件

1. [x] **garden/services/shift-manager/ コード移植**(セッション21)
2. [ ] **credentials + .env VPS 配置**(secrets/credentials.json + secrets/token.json + .env)
3. [ ] **send_pending.py 実装 + shell endpoint サポート**
4. [ ] **5/31 cron 登録**
5. [ ] **dry-run 検証**
