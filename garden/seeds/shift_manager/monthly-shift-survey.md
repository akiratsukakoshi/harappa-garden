---
type: seed
name: monthly-shift-survey
plot: shift_manager
description: 月初1日に翌々月のシフト募集フォームを下書き → 庭師剪定 → staff LINE 配信する種
status: draft
phase: 3c                    # HMC 依存種(seeds/README.md「実装ロードマップ」参照)
execution_host: vps          # cron 起動・Claude Code ヘッドレスはすべて VPS
hmc_dependency: required     # HMC のスクリプト + credentials が必要
version: 1
created: 2026-05-25
created_by: claude (with 塚越さん, セッション7)
last_updated: 2026-05-25
linked_workflows:
  - "[[monthly-cycle]]"   # ステップ 2(a) 翌々月シフトアンケート送信
linked_skills:
  - "shift_manager (HMC)"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "0 8 1 * *"           # 毎月1日 08:00 JST
  timezone: Asia/Tokyo
  # 議論余地: 06:30 morning-briefing と同じ朝枠に寄せるか、もう少し後にずらすか

# === ② 何を実行するか ===
engine: claude-code
execute:
  skill: shift_manager (HMC)
  working_dir: /home/tukapontas/harappa-cockpit
  computed_inputs:
    target_month: "$(date -d '+2 months' +%Y-%m)"   # 翌々月。月初1日に発火するため、当月+2 = N+2月分
    target_month_jp: "$(date -d '+2 months' +%-m)月"
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは原っぱ大学の庭師(塚越さん)を支える種「monthly-shift-survey」です。
    目的: 翌々月({target_month_jp})のスタッフシフトを集めるための募集フォームを
          下書きまで自動化し、staff LINE への配信は庭師の剪定承認を経て行う。

    手順:
      1. **前提確認**
         - HMC の月次シート(プログラムカレンダー新)で {target_month} の Q列「アンケート」が
           募集対象プログラムに正しくチェック済みか確認する
         - 未チェック or 不明な場合は、本種は処理を中断し、board に
           「Q列チェック未完了」の剪定依頼を出して終了(generate_shift_form.py は実行しない)
         - 参照: garden/soil/workflows/monthly-cycle.md ステップ2(a) の改善余地表

      2. **フォーム生成(HMC SKILL 利用)**
         - HMC の shift_manager SKILL の手順に従い、以下を実行:
           ```bash
           cd /home/tukapontas/harappa-cockpit
           source venv/bin/activate
           python apps/shift_manager/logic/generate_shift_form.py --month {target_month}
           ```
         - 生成された Google フォーム URL を取得・記録する

      3. **board に剪定依頼を起草**
         - garden/board/pending/{today}-monthly-shift-survey.md を作成
         - 内容(後述のテンプレ参照):
           a. 配信予定の LINE 本文(編集可)
           b. フォーム URL
           c. 配信先(staff グループ)
           d. 配信タイミング(承認後すぐ / 時刻指定)
           e. 庭師の承認/修正/却下の操作ガイド

      4. **庭師への通知**
         - pruning.notify(後述)に従い、ガクコ /send で personal グループに LINE 通知

    失敗時:
      - HMC コマンドが失敗 → on_failure に従う
      - フォーム URL 取得失敗 → board ファイルにエラー記載 + 庭師通知
      - Q列未完了が3ヶ月連続 → warning レベルで MAP.md に「Q列運用未確定」を再掲

# === ③ 結果をどこに置くか ===
outputs:
  - kind: board_draft
    path: garden/board/pending/{today}-monthly-shift-survey.md
  - kind: log
    path: garden/seeds/.log/{today}-monthly-shift-survey.log
  # フォーム生成は副作用として Google Sheets / Forms に直接書き込まれる
  # (HMC SKILL の責務)

# === ④ 誰に剪定依頼するか ===
pruning:
  channel: board_with_notify       # 配信文の確認が要るので「中」の重さ
  approver: "[[akira-tsukakoshi]]"
  notify:
    via: gaku-co
    group: personal
    template: |
      📋 {target_month_jp}シフトアンケート 下書きあります
      → board/pending/{today}-monthly-shift-survey.md
      確認 → 承認で staff LINE 配信

# === ⑤ 承認後の振る舞い ===
post_approval:
  via: gaku-co
  endpoint: /send
  body:
    group: staff
    require_approval: false         # 既に剪定承認済み
    message_from: |
      board ファイル `## 配信本文` セクション全文を message として送信。
      フォーム URL を含む。
  on_send_success:
    - board ファイルを garden/board/processed/ へ移動
    - audit.last_outcome = "sent"
    - LINE で庭師に完了通知(personal)
  on_send_failure:
    - board ファイルは pending に残置
    - audit.last_outcome = "send_failed"
    - LINE で庭師にエラー通知(personal)

# === ⑥ べき等性 ===
idempotency:
  key: monthly-shift-survey-{target_month}
  guard: |
    既に board/pending/ or board/processed/ に {target_month} 用の本種ファイルが
    あれば、新規発火しない(2重実行防止)。

# === ⑦ 失敗時の振る舞い ===
on_failure:
  retry:
    max: 2
    backoff: 30m
  fallback:
    via: gaku-co
    group: personal
    template: |
      ❌ monthly-shift-survey 失敗
      対象月: {target_month}
      理由: {error_summary}
      詳細: {log_path}
      → 手動で SKILL 実行を検討

# === ⑧ 依存 ===
depends_on:
  workflow: monthly-cycle
  state:
    - "月次シートの Q列(アンケート)が募集対象にチェック済み"
    - "HMC の venv が起動可能"
    - "ガクコ /send が利用可能(personal/staff 両方)"
  seeds: []

# === ⑨ 監査 ===
audit:
  last_fired: null
  last_outcome: null
  next_fire_estimate: 2026-06-01T08:00:00+09:00
---

# monthly-shift-survey — 翌々月シフトアンケート

## 目的(不変)

毎月1日朝、**翌々月の staff LINE グループにシフト募集フォームが届く** 状態を作る。庭師の手作業介入は **配信文の剪定承認の1ステップだけ** に絞る。

## 現状の方法

frontmatter の `execute` / `pruning` / `post_approval` を参照。要約:

1. cron 月初1日 08:00 発火
2. Claude Code が HMC の shift_manager SKILL を呼び、`generate_shift_form.py --month {N+2}` を実行
3. 生成された Google フォーム URL を取り、board/pending/ に下書きを置く
4. 庭師にガクコ経由で LINE 通知(personal)
5. 庭師が board を確認・編集 → 承認 → ガクコ /send で staff へ配信

## board ファイルのテンプレ(後述)

`garden/board/pending/{today}-monthly-shift-survey.md`:

```markdown
---
type: pruning_request
from_seed: shift_manager/monthly-shift-survey
target_month: 2026-07
form_url: https://docs.google.com/forms/d/.../viewform
status: pending
created: 2026-05-25T08:00:00+09:00
---

# 2026年7月 シフトアンケート 配信下書き

## 配信本文

(↓ ここをスタッフへの LINE 本文として配信します。編集可)

```
📅 2026年7月のシフト募集のお知らせ
回答期限: 6/10(水) まで
フォーム: https://docs.google.com/forms/...
不明点は LINE で塚越まで
```

## 配信先

- group: staff(全スタッフLINE)

## 配信タイミング

- [ ] 今すぐ
- [x] 09:00 に予約
- [ ] その他: ____

## 庭師アクション

承認(staff 配信実行): board ファイル上部 status を `approved` に変更 → 保存
修正: 本文を編集 → status を `approved` に変更 → 保存
却下: status を `rejected` に変更 → 保存

LINE 短文返信なら:
  「OK」 → approved(本文・タイミング既定値で実行)
  「NG」 → rejected
  「9時にして」 → 配信タイミングを 09:00 に変更して approved
```

## 改善余地(Improvement Hints)

| # | 現状の方法 | 改善余地 | ステータス |
|---|---|---|---|
| ❓ | 月次シートの Q列チェックが手動 + 誰がいつ入れるか未確定 | Q列入力担当・タイミングの確定 → 自動チェック化 → 種側で「未完了なら処理中断」の自動判定が機能する | **未検証**(monthly-cycle ステップ2(a) と同期) |
| ❓ | post_approval.body.message_from = board ファイル本文 | board ファイルの「配信本文」セクション切り出し規約(コードブロック内 / セクション全体 / frontmatter フィールド) | 未検証 |
| 💡 | 配信は剪定承認後に1回 | 5日経過しても回答が一定数に満たない → リマインド送信種(`monthly-shift-survey-reminder`)を別途 | 構想中 |
| ✋ | Q列の見せ方(スタッフ稼働確認の見せ方とは別議論) | 別種(monthly-working-hours-confirmation)の改善余地表で塚越さん検討中。重複提案禁止 | 検討中(workflow 側で進行) |
| ❓ | 発火時刻 08:00 | 6:30 morning-briefing と同枠に統合? もしくは 9:00 等に遅らせるか? 早すぎると HMC 起動が間に合わない可能性 | **未検証** |
| ❓ | computed_inputs の `$(date ...)` 評価主体 | ランチャー側(シェル)で評価 vs Claude Code 側で評価。前者がシンプル(prompt 渡し時には値が確定) | 未検証 |

## 関連

- workflow: [[monthly-cycle]] ステップ2(a)
- HMC SKILL: `shift_manager` → `generate_shift_form.py`
- HMC マニュアル: [/home/tukapontas/harappa-cockpit/docs/manuals/shift_manager.md](file:///home/tukapontas/harappa-cockpit/docs/manuals/shift_manager.md) 「3.シフト管理」
- ガクコ INTERFACE: [/home/tukapontas/gaku-co5.0/INTERFACE.md](file:///home/tukapontas/gaku-co5.0/INTERFACE.md) `/send` `require_approval`
- ADR セッション4: 種設計の方針(剪定振り分け)
- ADR セッション5: workflow 正本性
- ADR セッション6: Claude Code ヘッドレス + LINE+board ハイブリッド
- 関連種: `shift_manager/monthly-working-hours-confirmation`(同タイミング・別責務)

## TODO(本種に固有)

- [ ] 月次シートの Q列チェック運用の確定(workflow 側に依存)
- [ ] board ファイルの「配信本文」セクション切り出し規約
- [ ] 発火時刻の最終決定(現状 08:00 暫定)
- [ ] post_approval の garden → gaku-co `/send` 接続実装(セッション6 宿題と同期)
- [ ] computed_inputs の評価主体(ランチャー vs Claude Code)
- [ ] active 化に必要なインフラ: 種ランチャー / board ディレクトリ / ガクコ連携

## active 化条件(Phase 3c の入口)

本種は **HMC 依存種**(`hmc_dependency: required`)なので、Phase 3a の Garden 内完結種より一段あとに位置する。draft → active に移すために必要なもの:

### Phase 3a 由来の前提(全種共通)

1. 種ランチャー(VPS cron → `claude -p` 起動 + ログ + on_failure)
2. `garden/board/pending/` と `garden/board/processed/` ディレクトリの構造設計と作成
3. ガクコ `/send` 経由配信の最小ループ(LINE 短文返信→board 書き戻しは後追い可)

### Phase 3b 由来の前提(本種固有)

4. **HMC の VPS 移植 or 必要部分切り出し** — `generate_shift_form.py` が VPS から実行可能
5. **HMC credentials の VPS 配置** — Google OAuth(Drive/Sheets/Forms)・section_mapping.json 等
6. **secret 管理設計の確定** — セッション7 議論 B の結論を反映(保管方式・rotation・信頼境界)
7. HMC venv の VPS 上での再現(Python バージョン・依存パッケージ)

### 本種固有

8. Q列チェック運用の確定(workflow 側 — 欠けるとガード条件で常に中断する)
9. board ファイルの「配信本文」セクション切り出し規約
