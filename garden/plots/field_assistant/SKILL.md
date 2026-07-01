---
name: field_assistant
description: フィールド運営アシスタント区画。シフトカレンダーを発火マスターに、現場責任者の準備忘れ・確認漏れを防ぐ(週初めリマインド / D-2 ブリーフ / 月末月謝チェック / 名簿読み出し)。Garden 初の core_team 向け区画。
plot: field_assistant
topics: [フィールド運営, 現場責任者, 企画担当, 準備リマインド, 名簿, 参加者, 体験, 天気, シフトカレンダー, STORES, 月謝, 振替, おやこ学部, こども学部]
inherits_from:
  - garden/CHARTER.md
linked_workflows:
  - "[[program-execution]]"      # 本区画が円滑化する対象ワークフロー(正本)
  - "[[monthly-cycle]]"
requires_soil:
  - garden/soil/people/staff/    # ニックネーム → 実名(メンション解決の参考)
created: 2026-06-11
last_updated: 2026-07-02
created_by: claude (with ガクチョ, セッション42 / plot_gardener seedling 初適用)
status: draft                    # スモーク → test、LINE グループ投入 + 初回発火で active
---

# field_assistant — フィールド運営アシスタント

[program-execution](../../soil/workflows/program-execution.md) ワークフローの**現場責任者の準備忘れ・確認漏れを防ぐ**ための区画。
Garden 初の **core_team scope**(運営コアスタッフの LINE グループ)向け。master(Discord)区画とは情報境界が異なることに常に注意。

> 共通の業務観・トーンは [garden/CHARTER.md](../../CHARTER.md) を継承。

## SSOT(正本)

| データ | 正本 | 本区画の扱い |
|---|---|---|
| 開催予定・担当者 | **シフトカレンダー**(shift_manager の Monthly UI Sheet、タブ `YYYY-MM`) | read-only。**発火のマスター** |
| 参加者名簿 | STORES 予約 API(参照系のみ) | read-only |
| 天気 | Open-Meteo(キー不要) | read-only。会場→座標は `config/venues.json` |
| 月謝消化状況 | STORES 予約 API | read-only。振替チケット**発行は管理画面**(API 不可) |

カレンダー列(ヘッダー名で解決): 日付 / 曜日 / 会場 / カテゴリ / 活動内容 / 時間 / **企画者(H)** / **現場責任者(I)** / 応急衛生 / スタッフ

## 判断ルール(全 Mode 共通)

- **承認境界なし**: 本区画は全機能 read-only + 通知のみ。board を立てない(Garden 初の「剪定不要」区画)
- **担当メンション**: シフトカレンダーのニックネーム表記をそのまま `@名前 さん` で使う。`config/line_users.json` に userId 登録済みなら LINE の実メンションに変換、未登録はテキスト表記フォールバック
- **現場責任者が未記入のイベントは「(未記入⚠️)」と明示**(空欄こそ準備漏れの兆候)
- **企画MTG確認の対象 = カテゴリに「おやこ」または「こども」を含み、「自由」を含まない**イベントのみ
- **PII 境界**: LINE 本文に出すのは「苗字 + 子どもの名前 + 利用チケット」まで。保護者フルネーム・電話・アレルギー・緊急連絡先は**スプシのみ**(月末に全タブ自動クリア)。アレルギー「なし」以外の行はスプシで黄色表示 + LINE では ⚠️ マークのみ
- **財務・給与系の情報はこの区画に存在させない**(core_team 境界。月謝チェックは会員名と消化状況のみで金額を扱わない)

## Mode 1: Weekly Prep Reminder(週初め)

**種**: `field_assistant/weekly-prep-reminder`(cron 月曜 08:10)

当該週(月〜日)の全イベントについて現場責任者に準備チェックをメンション通知:
□物品手配 □スタッフスレ投稿 □体験者への案内(いれば) □天気判断(前日まで)

翌週のおやこ・こども学部イベントについて企画者に「企画MTGはお済みですか?」(**リマインドのみ。完了判定はしない** = ガクチョ決定 S42)。

イベントゼロの週も「今週の開催予定はありません」と一行送る(沈黙と故障を区別するため)。

実行: `processor.py weekly`

## Mode 2: Event Brief(活動日 D-2)

**種**: `field_assistant/daily-event-brief`(cron 毎朝 07:30、D+2 にイベントが無ければ無言スキップ)

イベントごとに: 企画タイトル・会場・時間 / 担当 4 役 / 参加サマリ(組数・人数)+ **予約ごとに「苗字(子ども全員)チケット」** / 会場の天気(午前・午後の降水確率と風・突風)。

末尾に「詳細名簿が必要なら『名簿出して』」の案内。天気取得失敗時もブリーフ自体は送る。

実行: `processor.py brief`

## Mode 3: Monthly Furikae Check(月末)

**種**: `field_assistant/monthly-furikae-check`(cron 28-31 日 19:30、`--if-last-day` で月末日のみ実行)

当月の月謝会員のうち**月謝消化 0 回の人**を抽出して通知(回数券・現地決済のみで参加した人も対象 = 移植元の規準)。発行作業は STORES 管理画面(API は参照のみ)。
LINE 通知に加え、**全会員の一覧を名簿ワークブックの固定タブ `月謝振替チェック` に書き出し**、その URL を LINE に添付(A案・毎月上書き。振替対象行は黄色表示 = ガクチョ決定 S45)。
同時に名簿ワークブックの他タブをクリア(`clear-sheets`、スプシ増殖防止 = ガクチョ決定 S42)。**`月謝振替チェック` タブは `KEEP_TABS` で保持**されるため掃除では消えない。

実行: `processor.py furikae --if-last-day` → `processor.py clear-sheets`

## Mode 4: Roster On-Demand(対話)

**通行手形**: core_team(+ master)。LINE グループで「6/14 の名簿出して」等。

- tool `get_event_roster(date, to_sheet)` が `processor.roster_text()` を呼ぶ
- 既定はテキストサマリ(苗字 + 子ども + チケット + ⚠️マーク)
- 「詳しく」「一覧で」等の要望時は `to_sheet=true` → スプシにフル名簿(保護者名・電話・アレルギー・緊急連絡先)を書き出して URL を返す

## Mode 5: Weather On-Demand(対話)— S42 追加

**通行手形**: core_team + master。「箱根のあさっての天気は?」等、**任意の場所 × 任意の日付**。

- tool `get_weather(place, date)` = `processor.weather_text()`。出力 = 天気(晴れ/雨等)・気温範囲・降水確率・風/突風を午前/午後で
- 場所解決: ① `config/venues.json`(登録会場) ② **国土地理院アドレス検索**(漢字地名に強い) ③ Open-Meteo 地名検索(ローマ字)④ 全滅なら default 会場 + 注記
- 範囲: 16 日先まで(Open-Meteo の限界)。過去日は不可
- 「天気どう?」だけで場所未指定なら直近の開催会場(シフトカレンダー)を優先して聞き返さず出す

## 運用メモ

- **LINE グループ投入前**: `FIELD_LINE_TO` = ガクチョの userId(1:1 テスト)。投入後にグループ ID へ切替
- **メンションの LINE 仕様(S42 実測)**: ①textV2 + substitution で bot からメンション可 ②**userId 必須**(表示名では不可) ③**group/room 宛のみ**(1:1 宛は 400 → line_push が宛先 prefix C/R で自動判定しテキストにフォールバック) ④userId 一括取得 API は認証済アカウント限定 → **発話 webhook から収集**(制約なし)
- **userId 収集の流れ**: グループ投入 → メンバーが発話 → line/app.py の収集フックが userId+表示名を `config/line_collected.json` に記録 → soil 運営ページの `line_display_name:` と照合(`processor.py sync-line-users`)→ `config/line_users.json` に**全ニックネーム → userId** を自動登録 → 次回配信からメンション有効
- **会場座標**: `config/venues.json` は概算値。ガクチョ確認で実フィールド座標に調整
- 既知の弱点: 体験参加者の自動判定は未実装(チケット表記で代替)。STORES イベント名とカレンダー活動内容の突合は部分一致ヒューリスティック

## Improvement Hints

| 案 | 状態 |
|---|---|
| 体験参加者の自動判定(個別案内・お礼テンプレ連携 = workflow ステップ 3/6) | 未着手 |
| 開催前日の天気判断リマインド(workflow 不変条件「前日まで」) | 未着手(D-2 ブリーフでカバー中) |
| 振り返りレポート Notion 自動下書き(workflow ステップ 7) | 未着手 |
| LINE メンションの userId 自動収集(webhook 連携) | 構想(手動登録で開始) |
| 写真アルバム → STORES 共有のタスク化(workflow ステップ 8) | 未着手 |
