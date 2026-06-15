---
name: sns_manager
description: 原っぱ大学の SNS 運用区画(Instagram/Facebook)。週次投稿の画像セレクト(土)・文案作成(月)・予約と、週次振り返りレポートを担う。塚越さんが著者・Garden が整形者。HMC sns_pilot の transplant 移植。
plot: sns_manager
topics: [SNS, Instagram, Facebook, Reels, 投稿, フィード, キャプション, 文案, ハッシュタグ, 週次レポート, Meta, インサイト, リーチ, エンゲージメント, 画像セレクト, ガクチョー文体, sns_pilot]
inherits_from:
  - garden/CHARTER.md
linked_workflows: []
requires_soil:
  - garden/soil/business/            # 事業構造・各サービスの文脈(文案の素材)
created: 2026-06-15
last_updated: 2026-06-15
created_by: claude (with ガクチョ, セッション45 / plot_gardener transplant)
status: draft                        # 種3本起草 → dry-run で test、初回1周見届けで active
---

# sns_manager — SNS 運用区画

原っぱ大学の Instagram / Facebook 運用を支える区画。HMC `sns_pilot`(SKILL + apps/sns_pilot)の **transplant 移植**。

> 共通の業務観・呼称・トーンは [garden/CHARTER.md](../../CHARTER.md) を継承。
> 戦略の詳細(ファネル・3目的 A/B/C・KPI)は [SNS_STRATEGY.md](SNS_STRATEGY.md) を**必ず先に読む**。

## この区画の最重要原則

**塚越さんが著者、Garden が整形者。** Garden がゼロから文章を作ると文体がバレる。
ガクチョの「一言コメント(生素材)」を起点に、ガクチョー語へ変換・整形するのが Garden の仕事。
創造判断(どの画像を選ぶか・どう書くか)は board に出してガクチョの剪定を必ず通す。

## scope(通行手形)

**master(Discord)のみ。** SNS は creative 判断・外部公開を伴うため core_team / staff には出さない。

## SSOT(正本)

| データ | 正本 | 本区画の扱い |
|---|---|---|
| 候補画像 | **Google Drive フォルダ**(ガクチョが金曜までに設置、`SNS_DRIVE_FOLDER_ID`) | read-only(SA で DL)。**セレクトの素材** |
| 投稿カレンダー・KPI 目標 | `config/config.json`(HMC 継承) | 火=B / 木=Reels / 土=A・C交互、投稿時間 |
| KPI 実績ログ | Google スプレッドシート(`SNS_SHEET_ID`、HMC 継承) | report が追記(SA) |
| インサイト(リーチ等) | Meta Graph API | read。週次レポートの素材 |
| 投稿予約 | **ig_scheduler**(VPS 稼働、`ig-api.harappa.monster`) | 承認後に画像バイナリ+caption を予約 |

## 投稿カレンダー(HMC 戦略から継承)

| 曜日 | 形式 | 目的 | 投稿時間 | 素材 |
|---|---|---|---|---|
| 火 | フィード写真 | **B: 既存共感** | 20:00 | 画像 + 一言コメント |
| 木 | Reels(動画) | 新規リーチ | 12:00 | YouTube Shorts 転用 |
| 土 | フィード写真 | **A: 新規獲得 / C: 哲学共有(前週と交互)** | 8:00 | 画像 + 一言コメント |

**MVP の対象は火・土のフィード写真2本のみ。** 木の Reels(動画)は当面ガクチョ手動 or 次フェーズ(セレクト対象に含めない)。

## 判断ルール(全 Mode 共通)

- **文体(ガクチョー語)**: 「〜でございます」「〜なのであります」等の語尾 / 身体感覚の具体描写(「手のひらがジンジンした」)/ ユーモアと逆張り / **綺麗にまとめすぎない**。一言コメントを必ず起点に、ゼロから創作しない
- **文字数**: フィード 150〜300字。ハッシュタグ 5〜8個(ニッチ寄り、**`#原っぱ大学` を必ず含む**)
- **A/C の交互**: 土曜の目的は前週と交互。前週がどちらだったかは直近の board / Sheet で確認
- **承認を飛ばさない**: セレクトも文案も必ず board → Discord でガクチョの剪定を経てから次に進む。外部公開(本番投稿)前に承認必須
- **日付は機械計算**: 「今週の火・土」は種の `computed_inputs` で `date` から算出。Claude の暗算禁止(HMC の既知ミス)

## Mode A1: Image Select(土曜)

**種**: `sns_manager/saturday-image-select`(cron 土 09:00)

金曜までにガクチョが Drive フォルダへ置いた候補画像から、今週の**火(B)・土(A/C)用に2枚**を SNS の意図を汲んで選定する。

1. `processor.py fetch-images --week {月曜日付}` で Drive フォルダの候補画像を VPS ローカルにDL(ファイル一覧 + ローカルパスが返る)
2. **Claude が各画像を Read して中身を見る** → 火(B既存共感)・土(A/C)の意図に最も合う2枚を選定
3. board を起草(`board/pending/`)= 選んだファイル名・**画像の簡易描写**・選定理由・火/土の割り当て・(A/C どちらか)
4. Discord に承認依頼通知 → ガクチョが board で**返信・編集・一言コメント追記・承認**(日曜夜まで)

> ガクチョはこの board で各画像に**一言コメント**を添える(= 月曜の文案生成の起点)。

候補が無い / 1枚しかない場合は board に「候補不足」と明示してガクチョに知らせる(沈黙しない)。

## Mode A2: Caption Draft(月曜朝)

**種**: `sns_manager/monday-caption-draft`(cron 月 07:30)

土曜に承認された画像 + ガクチョの一言コメントを起点に、火・土の**フィード文案**を作成する。

1. 承認済み board(画像 + 一言コメント + A/C 割り当て)を読む
2. **Claude がガクチョー文体で文案2本を作成**(SNS_STRATEGY の文体・3目的を反映、150〜300字 + ハッシュタグ)
3. board を起草 = 火/土それぞれの本文・ハッシュタグ・投稿時間・画像ファイル名
4. Discord に承認依頼 → ガクチョが訂正・承認
5. 承認後 → `processor.py schedule --board <path>` で ig_scheduler に予約(火 20:00 / 土 8:00)。予約結果(job_id)を board に記録

承認前に予約しない。一言コメントが board に無い画像はスキップして board に明示。

**使用済み画像の自動退避**: `schedule` が予約に成功すると、投稿に使った画像の Drive 原本を候補フォルダ直下から `使用済み/` サブフォルダへ自動 move する(翌週以降の候補に再掲しないため。候補は「置きっぱなし」運用で OK)。差し替えで不採用になった候補は移動せず候補のまま残る。`--no-archive` で抑止可。move には Drive フォルダの **編集者** 共有が必要(閲覧者だと 403)。

## Mode B: Weekly Report(月曜朝)

**種**: `sns_manager/monday-weekly-report`(cron 月 07:00、**通知のみ・承認境界なし**)

先週(月〜日)の Meta インサイトを取得 → Google スプレッドシートに記録 → MD レポートを生成し Discord へ通知。

実行: `processor.py report` が完結(Insights 取得 → Sheet 追記 → MD 出力)。Claude は出力された MD を Discord に流すだけ(整形しない)。

レポート内容: フォロワー増減 / 投稿別リーチ・保存・シェア / Reels フォロワー外リーチ率(目標60%)/ 投稿時間分析 / ルールベースの気づきコメント。

## Mode A3: アドホック投稿(イレギュラー単発・対話)

週次フロー(土セレクト → 月文案)の外で、「明日の投稿を作りたい」「今日この写真を出したい」等の**単発依頼**に master Discord で対話的に応じる。

1. ガクチョが対象画像を Drive に置く(or 既存候補から)+「○月○日 ○時に出したい」「目的は A/B/C のどれ」を伝える
2. Claude が画像を Read → ガクチョー文体で文案(目的が曖昧なら対話で確認)→ その場 or board で提示
3. 承認 → `processor.py schedule` で予約:
   - **任意日時**: `--publish-at` は週次カレンダーに縛られず任意の日時を指定できる(明日でも当日でも)
   - **カルーセル(複数画像)**: `--image` の代わりに `--images "a.jpg,b.jpg,c.jpg"`(2〜10 枚)。IG はカルーセル投稿、FB は複数写真のアルバム(横スワイプ)として予約

承認境界は週次と同じ(外部公開は不可逆 = ガクチョ承認後にのみ予約)。文体ルールも同じ(一言コメント/視点を起点に、ゼロから創作しない)。

## Mode C: LINE@ 配信(将来・Phase 4)

HMC でも**自動投稿は未実装**(文案作成のみ、配信は手動だった)。LINE 公式アカウント(登録者向け・271名)への Messaging API 連携は本区画の対象外。やるなら別途新植。

## 失敗時

- セレクト/文案/予約で失敗 → log にエラー全文(番人が拾う)+ board/failed へ
- ig_scheduler 予約失敗 → board に残し再実行可能に(べき等性: 同 job は重複予約しない)

## active 化条件

| 段階 | 条件 |
|---|---|
| draft | SKILL + 種3本 + service 骨格がある |
| test | dry-run(Drive DL / report / schedule)が通る |
| active | 実運用1周(土セレクト → 承認 → 月文案 → 承認 → 予約 + レポート1本)をガクチョが見届け |

## HMC レガシーとの境界

HMC `sns_pilot`(別 repo)は当面残置。**Garden 移行後は Garden 側で運用**し、HMC 側は手動フォールバック扱い。投稿予約サーバー `ig_scheduler` は両者で共用(VPS 稼働の同一コンテナ)。
