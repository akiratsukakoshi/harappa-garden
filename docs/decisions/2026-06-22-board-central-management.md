# ADR: board 運用を「正本 + レジストリ + リンター」で一元管理する

- 日付: 2026-06-22(セッション56)
- ステータス: 採用
- 関連: [board 運用の正本](../../garden/board/README.md) / 前提 ADR(2026-05-27 board 構造 / 2026-06-01 lifecycle・通知 / 2026-06-02 board・log を vault 外へ)

## 背景

board(連絡板/剪定依頼)の運用ルールが **種ごとに各自記述**され、正本が無かった。結果、
セッション56 で次の規約違反が同時多発していた:

- SNS の土曜セレクト種が、画像取得失敗時に**古いローカル画像で board を捏造**(stale fallback)。
- 承認依頼の通知文面が **種別「unknown」・タイトルが種名のみ**で用件が分からない(ガクチョ指摘)。
- `pending/` に **status=processed/registered の board が居座り**、「未承認はどれか」が分からない(実害)。
- SNS board を `status: approved` にすると send_pending が「未知の from_seed」で**失敗ループ**。

ガクチョの問い:「**種ごとに管理だと、また同じルール無視が作られる。どこかで一元管理しないと。**」

## 決定

board 運用を 4 層で一元管理する(本プロジェクトの「workflows を正本に、方法は改善対象」と同型)。

| 層 | 実体 | 役割 |
|---|---|---|
| 正本(ルール) | [`garden/board/README.md`](../../garden/board/README.md) | 人間が読む契約(スキーマ/ライフサイクル/承認3モデル/不可侵原則) |
| レジストリ(データ) | [`board_registry.py`](../../garden/services/garden-gaku-co/board_registry.py) | 種 → {種別, タイトル, 承認モデル, 配信先} を1テーブル。**新種=1行追加** |
| エンジン(実行) | [`send_pending.py`](../../garden/services/garden-gaku-co/send_pending.py) | 分類・通知・ライフサイクル片付け・配信ルーティングを registry 由来で一括 |
| リンター(enforcement) | [`board_lint.py`](../../garden/services/garden-gaku-co/board_lint.py) | 正本/registry への違反を機械検出 → 番人(Discord)+ ダッシュボードに通知 |

入口の強制: `plot_gardener` SKILL のチェックリストに「registry 登録 + lint 通過」を必須化。

### 承認モデル(registry の `approval`)

- **AUTO**: status:approved で send_pending が `dispatcher`(line_send/shell)実行(シフト募集/集計)。
- **CONVERSATIONAL**: 会話で承認 → bot/Claude が実行(SNS 予約・経費/請求登録)。status:approved にしても**自動配信せず黙って archive**(失敗ループの罠を解消)。
- **FYI**: 承認不要の通知のみ(録音 digest・財務投げかけ・朝 Triage)。

### 不可侵の原則(正本に明記)

1. 入力が無い/取得失敗なら**古いデータにフォールバックしない**(リマインドのみ)。
2. **pending = 承認待ちだけ**(終端ステータスは毎分 processed/ へ自動片付け)。
3. **日本語タイトル必須**。
4. board を作る種は**必ず registry に登録**(未登録は lint ERROR + 承認時に弾く)。

## 根拠

- 振る舞いは**エンジンが registry 由来で一括処理**するので、雑な種でも sane な分類/ライフサイクルになる。
- ルールの所在が**1ファイル(正本)+1テーブル(registry)**に収束し、新種対応は「1行追加」。
- **lint が機械的に違反を弾く**ので、規律でなく仕組みで再発を止める(導入時に未登録の既存種4本を即検出 → 登録済み)。

## 影響

- 既存の配信(シフト LINE/shell)挙動は registry から同じ集合を導出するため不変。
- 既存の `DISPATCH_LINE_SEND`/`DISPATCH_SHELL` ハードコードは registry 由来に置換。
- 番人(`*/10`)と board ダッシュボードが lint 違反を可視化。

## やらないこと

- 既存 board の遡及リネーム・大移動はしない(必要に応じて janitor が片付ける)。
- 承認操作そのものの場所(Discord 一本)は変えない。ダッシュボードは閲覧専用のまま。
