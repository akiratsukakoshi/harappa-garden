---
name: shift_manager
description: 月次のシフト募集・稼働集計・シフト確定を担う区画。月末・月初・月中の3点で発火し、Garden 内のスクリプトと Google Sheets/Forms を橋渡しする。
plot: shift_manager
topics: [シフト, 稼働, 稼働時間, 集計, シフト募集, アンケート, シフト確定, 給与, 業務委託, 精算, 請求書, freee, スタッフ稼働, 翌月, 月初, 月末, 10日締切]
inherits_from:
  - garden/CHARTER.md
  - shift_manager (HMC)
  - garden/soil/workflows/monthly-cycle.md
requires_soil_index: true
created: 2026-05-30
last_updated: 2026-05-30
created_by: claude (with ガクチョ, セッション21)
linked_seeds:
  - shift_manager/monthly-shift-survey
  - shift_manager/month-end-working-hours-prep
  - shift_manager/monthly-working-hours-confirmation (構想)
  - shift_manager/monthly-shift-finalize (構想)
linked_services:
  - garden/services/shift-manager (Python scripts)
  - garden-gaku-co (配信経路)
linked_workflows:
  - monthly-cycle
linked_soil:
  - soil/people/staff/
  - soil/business/
---

# shift_manager — 月次シフトと稼働精算の橋渡し

shift_manager 区画は、原っぱ大学の **翌月シフトの募集・確定** と **当月稼働の集計・精算動線** を担う区画です。月末・月初1日・月初10日の3点で発火し、Garden 内のスクリプト([garden/services/shift-manager/](../../services/shift-manager/))と Google Sheets/Forms の橋渡しを行います。

> 共通の業務観・呼称・トーン・Output Style 質感は [garden/CHARTER.md](../../CHARTER.md) を参照。本 SKILL は shift_manager 固有の手順・ファイル・判断ルールに集中します。
> 業務の正本(目的・現状の方法・改善余地)は [garden/soil/workflows/monthly-cycle.md](../../soil/workflows/monthly-cycle.md)。

---

## SSOT(本 plot の正本)

CHARTER の SSOT 原則を本 plot に適用:

- **Monthly UI Sheet**(`config_ids.monthly_ui_id` = `1_RMAQuSb3eWV30WGQ_gsJI5M6Ll1WHvbM4ifkGDuNkM`) = **当月稼働の正本**(プログラムカレンダー新)
- **Working Hours Sheet**(`config_ids.working_hours_id` = `1nevys4etwvn4NQToetsj6GLAVrtJT4Y4rj5pn30yZ84`) = 月別稼働時間集計タブ群(`YYYY-MM_稼働時間`)
- **Shift Form**(`config_ids.shift_form_id`)= 翌月シフト募集フォーム(月次再生成)
- **Backend DB Sheet**(`config_ids.backend_db_id`)= スタッフマスター(`DB_Master_Nicknames` 等)。`PaymentType` 列が精算ルート分岐の根拠
- soil 側の正本: [staff マスター 29 名](../../soil/people/staff/index.md)。**Backend DB との同期** は当面 backend が支配的(staff master は HMC 側)

正本は Google Sheets 側にあり、Garden は **読み書きの橋渡し** を担います。LLM Wiki 化(soil への移植)は将来検討事項。

---

## ファイルと役割

| ファイル | 役割 | 編集方向 |
|---|---|---|
| `garden/services/shift-manager/generate_shift_form.py` | 翌月シフト募集フォーム生成スクリプト | 月初1日 cron が呼ぶ |
| `garden/services/shift-manager/generate_working_hours.py` | 月別稼働時間集計シート生成スクリプト | 月末 cron(または手動)が呼ぶ |
| `garden/services/shift-manager/config/config_ids.json` | Google Sheet ID 集 | 手動更新(滅多に変わらない) |
| `garden/services/shift-manager/config/section_mapping.json` | 部門名マッピング + 時給 + 既定勘定科目 | 手動更新 |
| `garden/board/pending/{today}-monthly-shift-survey.md` | アンケート配信文の剪定依頼 | 種が生成 / 庭師が編集・承認 |
| `garden/board/pending/{today}-working-hours-prep.md` | 稼働表チェックリストの剪定依頼 | 種が生成 / 庭師がチェック |
| `garden/board/processed/{date}-{name}.md` | 承認後の保管庫 | post_approval が転記 |
| `garden/log/{today}-{seed}.log` | 種の実行ログ | 種が追記 |
| `garden/services/shift-manager/secrets/` | Google OAuth + Freee OAuth credentials(VPS 600 perm) | 手動配置・git 除外 |

---

## Mode 1: Month-end Preparation(月末 — 稼働表の準備)

**起動**: 種 `shift_manager/month-end-working-hours-prep`(cron 毎月最終日 22:00 想定、要合意)。

### 目的
翌月1日朝の「稼働確認依頼」で使う **当月稼働表** を完成させるための **チェックリスト剪定依頼** を board に置きます。実集計(`generate_working_hours.py`)はチェック完了後に庭師承認で発火。

### Step 1: チェックリストを board に生成
1. 当月対象月を確定(`YYYY-MM` = 今月)+ 翌日 Mode 2 の対象月を計算(`YYYY-MM` + 2 ヶ月 = 月末から見て 2 ヶ月先 = 月初 Mode 2 から見て翌月)
2. `garden/board/pending/{today}-working-hours-prep.md` に剪定依頼を起草:
   - 月次カレンダー Sheet の点検項目(開催されなかった日程の残置・稼働時間の誤り・スタッフ名)
   - 突き合わせ先(Notion フィールドレポート + 運営LINE)
   - 放サボ稼働の[[kodomon]] CSV インポート状況
   - **翌日 Mode 2 の対象月タブ (N+2 = 月末から +2 ヶ月先) の Q列(アンケート)チェック確認** ← Mode 2 の前提整備リマインド
     - 明日 8:00 の monthly-shift-survey が見にいくタブ
     - 空のままだと翌朝の survey が「No events selected」で空振り
   - 承認後の動線: `[ ] 集計実行(generate_working_hours.py)` チェック

### Step 2: 庭師通知
- garden-gaku-co `/send` で Discord master に1行通知
  - 例: 「📊 5月の稼働表チェックお願いします → board/pending/2026-05-31-working-hours-prep.md」

### Step 3(承認後の発火)
- 庭師がチェックリスト完了 + `[x] 集計実行` をチェック → bot が検知 → `python generate_working_hours.py --month YYYY-MM` 実行
- 出力シートURLを Discord master に通知
- 放サボ列(オレンジセル)への手入力を促す

### 判断ルール
- 月次シートに「未確定の稼働時間」が残っている → **実行しない**、board に「要確定」を立てて庭師通知
- 既に `YYYY-MM_稼働時間` タブが存在 → 上書き前に「再生成しますか?」を board で確認(`--force` 相当の判断ゲート)

### Mode 2 への引き継ぎ責務
Mode 1 は単独で完結する種ではない。**翌日朝の Mode 2(monthly-shift-survey)が成功するための前提を庭師に確認させる責務** も担う(月末 22:00 が前夜リマインドの自然なタイミングだから)。具体的には board に「翌日 Mode 2 の対象月(月末から +2 ヶ月先 = Mode 2 から見て翌月)の Q列確認」のチェック項目を必ず含める。Mode 2 側の実行時ガード(「Q列空なら空振り終了」)とのダブル防御。

---

## Mode 2: Month-start Survey(月初1日 — 翌月シフト募集)

**起動**: 種 `shift_manager/monthly-shift-survey`(cron 毎月1日 08:00)。

### 目的
翌月(N+1 月、N = 当月 = 発火月)のスタッフ募集フォームを生成 → 配信文を下書き → 庭師承認後に staff LINE グループへ配信。

### Step 1: 前提確認
- Monthly UI Sheet の `Q列(アンケート)` が翌月分の募集対象プログラムに正しくチェック済みか確認
- 未チェック or 不明 → 処理中断、board に「Q列チェック未完了」を立てて庭師通知

### Step 2: フォーム生成
```bash
cd /home/vps-harappa/garden/services/shift-manager
.venv/bin/python generate_shift_form.py --month YYYY-MM   # YYYY-MM = 翌月
```
- 生成された Google フォーム URL を取得・記録

### Step 3: board に剪定依頼を起草
`garden/board/pending/{today}-monthly-shift-survey.md` に以下を含む剪定依頼:
- 配信予定の LINE 本文(編集可、コードブロックで囲む)
- フォーム URL
- 配信先(staff グループ)
- 配信タイミング(承認後すぐ / 時刻指定)
- 庭師アクションガイド(承認/修正/却下)

### Step 4: 庭師通知
- garden-gaku-co `/send` で Discord master に1行通知
  - 例: 「📋 7月シフトアンケートの下書きあります → board/pending/2026-06-01-monthly-shift-survey.md」

### Step 5(承認後の post_approval)
- 庭師が board の `status: pending` → `approved` に更新(または短文返信「OK」)
- bot が検知 → garden-gaku-co `/send (group=staff, require_approval=false)` で配信
- 配信成功 → board を `garden/board/processed/` へ移動 + 庭師に完了通知

### 判断ルール
- 同一月の board が既に pending/processed にある → **新規発火しない**(べき等性、`idempotency.key = monthly-shift-survey-{target_month}`)
- 「OK」短文返信 → 本文・タイミング既定値で approved
- 「9時にして」 → 配信時刻を 09:00 に更新して approved
- 「NG」 → rejected

---

## Mode 3: Month-start Confirmation(月初1日 — 前月稼働の確認依頼)

**起動**: 種 `shift_manager/monthly-working-hours-confirmation`(構想中、cron 毎月1日 09:00 想定)。

### 目的
前月稼働表をスタッフが自分の目で確認できる状態にする + 精算ルート(3系統)を動かす。

### Step 1: 稼働表の見せ方判定 ← **未確定**
庭師が3候補から選択するまで構想中(継続宿題):
- (a) 個別テキスト要約(各スタッフへ自分の稼働を 1 メッセージ)
- (b) スプシ個人タブ(各スタッフが自分のタブだけ見える)
- (c) 現状スクショ(現行運用継続)

決定後に Step 2 以降を詰めます。

### Step 2(候補): 配信文起草 + board 剪定依頼
- `garden/board/pending/{today}-working-hours-confirmation.md` に下書き
- 配信本文に **3 ルートの動線**(業務委託請求書 / アルバイト freee 精算 / 外部スタッフ LINE 申請)を必ず含める
- 締切: 10日

### Step 3(候補): 承認後配信
- Mode 2 と同じ post_approval 経路

### TODO
- ガクチョ判断: 見せ方 (a)/(b)/(c) 決定 → SKILL に書き戻し
- 種 draft 起草(現在は構想のみ)

---

## Mode 4: Month-day-10 Finalize(月初10日 — シフト確定 + 稼働確認締切)

**起動**: 種 `shift_manager/monthly-shift-finalize`(構想中、cron 毎月10日 08:00 想定)。

### 目的
- 翌月シフト(Mode 2 で募集した分)の人員配置確定(回答集計 + 調整)
- 前月稼働確認の精算データ集約状況の可視化

### Step 1: 回答集計(S37 で Garden 移植済)
```bash
cd /home/vps-harappa/garden/services/shift-manager
.venv/bin/python aggregate_responses.py --month YYYY-MM           # Mode 2 で募集した翌月分の Forms 回答を集計
# --output_suffix _test を付けると Shift_Work_YYYY-MM_test に書く(正規タブを汚さず確認できる)
```
- Google Forms(`shift_form_id`)の回答 → NG マトリクスを **シフト調整シート**(`shift_work_id` の `Shift_Work_YYYY-MM` タブ)に書き出す。
- 既定の cutoff は前月1日 UTC(翌月募集の回答は前月に集まる前提)。回答者名は設問「お名前」優先、無ければ Staff Master の Email→Name で補完。
- 既存タブがある場合は手動行・既存データを保持してマージ(再実行安全)。NG=赤・◎=青の条件付き書式 + ヘッダ固定。
- 認証は service account(`harappa-drive-bot@…`、SCOPES に `forms.responses.readonly` を追加)。フォームは SA に共有済み。
- ⚠️ Mode 4 全体(種 `monthly-shift-finalize`)はまだ構想。**集計スクリプト単体は手動実行で利用可**(S37 で 7 月分を実集計 = 11 名)。

### Step 2(候補): 3 ルート集約状況の通知
- 業務委託請求書(invoice_processor 連携)
- アルバイト freee 精算
- 外部スタッフ LINE 申請
- 各ルートの到着状況を Discord master に通知 → 未着があれば剪定依頼

### TODO
- [x] `aggregate_responses.py` の Garden 移植(S37 完了。`garden/services/shift-manager/aggregate_responses.py`)
- 種 `monthly-shift-finalize` draft 起草
- 庭師判断: 確定作業の自動化スコープ(複雑な人員配置は人手前提)

---

## Mode 5: Discord Approval Response(承認応答)

**起動**: ガクコ(`garden-gaku-co/bot.py`)が Discord master channel で shift_manager 系の board に関する承認/テスト/却下/編集/閲覧の指示を受けた時。

### 目的
ガクチョの自然言語指示を受けて board ファイル(`garden/board/pending/*-{shift_manager-seed}.md`)を VPS 上で直接編集する。Obsidian で手書き編集する代わりに、**VPS が唯一の書き手**になることで Obsidian LiveSync 経由の巻き戻し事故([S26-27 で発覚した放サボ上書き](../../../docs/sessions/2026-06-02-session27.md) の構造的原因)を防ぐ。

### 前提
- `send_pending.py:notify_pending` が承認依頼通知に必要情報(配信本文プレビュー / 関連URL / 客観事実)を Discord に貼っている。ガクチョは Discord だけで判断可能。
- `garden/board/**` は **Obsidian LiveSync の ignore 対象**。Obsidian で board を見ても編集はしない/できない。承認操作は Discord で完結する。

### 指示の分類と動作

| ガクチョの自然言語 | 動作 | 編集内容 |
|---|---|---|
| 「承認」「OK」「集計まわして」「いって」 | board frontmatter の `status: pending` を `approved` に書き換え | status のみ |
| 「テスト送って」「テスト配信」「俺に送って」「個人 LINE で確認」 | `status: pending` → `test`(send_pending が personal LINE に送り、自動で pending に戻る) | status のみ |
| 「キャンセル」「却下」「待って」「やめて」「NG」 | `status: pending` → `cancelled`(send_pending が再発火しなくなる。board は pending に残るがガクチョが手動で processed/ や failed/ に移動 or 放置) | status のみ |
| 「本文の XX を YY に変えて承認」「文言を XX にして OK」 | `## 配信本文`(または `## 📋 配信本文(編集可)` 等の見出しを含む節)内のコードブロック該当箇所を Edit してから `approved` に | 本文 + status |
| 「配信時刻を 9:00 にして承認」「明日 8 時にして OK」 | frontmatter の `scheduled_send` を `YYYY-MM-DDTHH:MM:SS+09:00` 形式に upsert、その後 `approved` に | scheduled_send + status |
| 「board 見せて」「中身全部出して」「全文ちょうだい」 | board ファイル全文を Read してそのまま Discord に貼る(2000 字超なら分割) | Read のみ |

### 該当 board の特定ロジック

1. **直前の Discord 通知から推定**: `notify_master` 経由で直近に送られた承認依頼通知 board が 1 件しか無ければ、それを対象に確定。
2. **キーワードで推定**: ガクチョの指示に「シフト募集」「アンケート」(=monthly-shift-survey)、「稼働確認」「稼働表配信」(=monthly-working-hours-confirmation)、「集計」「prep」「稼働まわして」(=month-end-working-hours-prep)等のキーワードが含まれていれば、from_seed で絞り込み。
3. **対象月を併記**: 「5月稼働」「2026-05」「7月シフト」等で `target_month` を絞り込み。
4. **複数候補が残った場合**: **必ず聞き返す**。「以下の 2 件のどちらですか?」とリストアップ。勝手に決めない。
5. **0 件**: 「該当する pending board が無いみたいです。`board/pending/` をリストしますか?」と返す。

### 編集の安全規範

- **frontmatter の他フィールドは触らない**(target_month / from_seed / created / working_hours_url 等)
- 本文編集時は **配信本文セクション内のコードブロックのみ**触る(他の解説文や `## 状況` 等は変えない)
- 編集後は **必ず一行報告**:「反映した: `2026-06-01-monthly-shift-survey.md` の本文を編集 + status を approved に」
- 編集の reasoning が曖昧なら(該当箇所が複数等)、編集前に「ここを変えればいいですか?」と該当箇所を引用して確認

### LiveSync 隔離後の board 観察

- ガクチョが「先月の processed リストアップして」と聞いてきたら、`garden/board/processed/` を VPS 上で ls して返す(Obsidian では見えなくなっているので Discord 経由が観察手段)
- 「あの board の中身もう一回見せて」も同様に Read して貼る

### 失敗時の挙動

- board ファイルが書き換え後にすぐ消えた(同名で別 board が pending に湧いた等)→ LiveSync 整合性異常の可能性。ガクチョに「LiveSync で board が同期されているかも、ignore 設定確認お願いします」と知らせる
- send_pending の発火が確認できない(承認したのに次の cron tick で processed/ に移動しない)→ `garden/log/send-pending.log` の直近行を読んで原因を返す

### Output Style(本 Mode 固有)

- ガクチョが「承認」と短く言ってきたら、こちらも短く返す。「反映した: `{board名}` を approved に。次の 1 分以内に配信走ります」
- 編集を伴う場合は「反映前」を必ず確認: 「本文の『6月10日まで』を『6月15日まで』に変えて、status を approved にします。これで OK ですか?」(編集してから approved にする 2 ステップで、最初の編集前に確認する)
- 「テスト送って」は確認なしで即実行(個人 LINE 宛なので安全)

---

## Output Style(shift_manager 固有部分)

CHARTER の Output Style 質感に従いつつ、shift_manager 固有のセクション順:

### セクション順
`📊 状況` → `⚠️ 注意` → `📋 アクション` → `🔖 判断ほしい`

### shift_manager 用 良い締めの例
- 「5月の稼働表、最終フィールド分の入力待ちが2件です。1件は和田さんの担当回、もう1件は放サボ。和田さんに確認とコドモン CSV のインポート、こちらで手配しますか? それとも今夜中にガクチョが入れますか?」
- 「翌月シフトアンケートの配信文、下書き作りました。回答期限は 6/10(水)です。文面はそのままでよさそうですが、配信時刻だけ指定してください。今すぐ / 朝9時 / その他 のどれにしますか?」

(共通の「悪い締めの例」「形式」は CHARTER 参照)

---

## SKILL 内で確定済みの判断ルール

| 状況 | ルール |
|---|---|
| 月次シート Q列未チェック | 種を中断、剪定依頼を board に立てて庭師通知。`generate_shift_form.py` は実行しない |
| 既存稼働表タブの再生成要求 | 上書き前に board で `[ ] 再生成しますか?` を立てる(`--force` 相当のゲート) |
| 同月の既存 board(pending/processed)あり | 新規発火しない(べき等性) |
| 配信文の修正指示 | 庭師の短文返信に従って board 編集後に approved |
| 配信失敗 | board は pending 残置、`audit.last_outcome = "send_failed"` 記録、庭師通知 |
| 「シフト管理担当」が誰か未確定 | 当面は庭師に剪定依頼(継続宿題)、確定後に approver 切り替え |
| 自然言語期限指示(「来週」等) | 数値化を庭師に確認してから反映 |

---

## このSKILLを参照する種・サービス

| 名前 | 役割 | SKILL の参照範囲 |
|---|---|---|
| `garden/seeds/shift_manager/monthly-shift-survey.md` | 月初1日 08:00 cron | Mode 2 全体 + Output Style |
| `garden/seeds/shift_manager/month-end-working-hours-prep.md` | 月末最終日 22:00 cron(想定) | Mode 1 全体 |
| `garden/seeds/shift_manager/monthly-working-hours-confirmation.md` | 月初1日 09:00 cron(構想) | Mode 3 全体(見せ方確定後) |
| `garden/seeds/shift_manager/monthly-shift-finalize.md` | 月初10日 08:00 cron(構想) | Mode 4 全体 |
| `garden/services/garden-gaku-co/bot.py` | Discord 常駐対話 | 越境発話の picker 経由で on-demand load |
| `garden/services/shift-manager/generate_shift_form.py` | Mode 2 で呼ばれる Python | (SKILL ロード不要・機械処理) |
| `garden/services/shift-manager/generate_working_hours.py` | Mode 1 で呼ばれる Python | (SKILL ロード不要・機械処理) |

---

## 6/1 ミニマム実装スコープ(セッション21)

ガクチョ判断「ミニマムでも Garden で動かす」に基づく実装スコープ:

**実装する**:
- `garden/services/shift-manager/` への generate_shift_form.py / generate_working_hours.py 移植
- 共通依存(`freee_client.py` / `utils.py` / 2 つの json config) 移植
- credentials の VPS 配置(secrets/ 600 perm)
- 種 `monthly-shift-survey` のパス更新 + active 化(6/1 08:00 発火)
- 種 `month-end-working-hours-prep` の draft 起草
- board → gaku-co `/send` 最小ループ実装

**6/1 後に追加**:
- `monthly-working-hours-confirmation` (見せ方確定後)
- `monthly-shift-finalize`(`aggregate_responses.py` 移植後)
- HMC の他 logic スクリプト(`monthly_to_db.py` 等)の段階的 Garden 化判断

**Garden 移植済**:
- `generate_shift_form.py` / `generate_working_hours.py` / `import_kodomon.py`(S21)
- `aggregate_responses.py`(S37。Mode 4 Step 1 / Forms 集計)

**HMC に残置(当面)**:
- `monthly_to_db.py` / `db_to_monthly.py` / `register_payroll.py` / `export_external_staff.py` / `sync_staff_master.py` / `annual_to_db.py` 他
- 必要になった種から段階的に Garden 化判断

---

## 関連

- 共通規範: [garden/CHARTER.md](../../CHARTER.md)
- 業務正本: [garden/soil/workflows/monthly-cycle.md](../../soil/workflows/monthly-cycle.md)
- 起源: HMC `.agent/skills/shift_manager/SKILL.md`
- HMC マニュアル: [/home/tukapontas/harappa-cockpit/docs/manuals/shift_manager.md](file:///home/tukapontas/harappa-cockpit/docs/manuals/shift_manager.md)
- 種スキーマ: [garden/seeds/README.md](../../seeds/README.md)
- ADR(S19): [種(seed) と SKILL の責務分離](../../../docs/decisions/2026-05-30-skill-and-seed-separation.md)
- ADR(S20): [Garden CHARTER 導入とトーン統一](../../../docs/decisions/2026-05-30-garden-charter.md)
- 関連 plot: [daily-pilot](../daily-pilot/SKILL.md)(越境発話対応の picker は同時整備)
