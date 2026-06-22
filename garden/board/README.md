# board(連絡板)運用の正本

> **これが board 運用ルールの単一の正本**(S56・2026-06-22 制定)。
> 「種ごとに各自ルールを書く」のはやめる。board の振る舞いは全部ここと
> [`board_registry.py`](../services/garden-gaku-co/board_registry.py) に集約し、
> [`board_lint.py`](../services/garden-gaku-co/board_lint.py) が機械的に違反を弾く。
>
> 関連: ADR [2026-06-22-board-central-management](../../docs/decisions/2026-06-22-board-central-management.md) /
> 構造の前提 ADR(2026-05-27 / 2026-06-01 / 2026-06-02)は履歴。生きた正本は本ファイル。

## board とは

エージェント(種)が**庭師に判断/通知を渡す連絡板**。1 件 = 1 ファイル(markdown + frontmatter)。

## ディレクトリ(ライフサイクル)

| dir | 意味 |
|---|---|
| `pending/` | **承認待ち または 通知中。ここには status=pending のものだけが居る**(鉄則) |
| `processed/` | 役目を終えた(承認・配信・通知済み) |
| `failed/` | ディスパッチが連続失敗して隔離 |
| `quarantine/` | 壊れた board |
| `triage/` | 朝ブリーフィング等の Triage 出力(承認対象でない) |

**鉄則: `pending/` に終端ステータスを残さない。** `send_pending.relocate_terminal_boards()` が
毎分、終端(processed/registered/done/completed/sent/skipped/**scheduled**)を `processed/` へ自動で片付ける。
（`scheduled` = SNS の予約完了。`processor.py schedule` が job_id を board に記録し終端化 → 片付く。）
表示側(朝ブリーフィング・ダッシュボード・`list-pending`)も status=pending で絞る。

## frontmatter スキーマ

```yaml
---
type: pruning_request        # 必須
from_seed: {plot}/{seed}     # 必須・board_registry に登録済みであること
title: 日本語の用件          # 推奨(無い時は registry のタイトル → 本文H1 → 種名)
status: pending              # pending|approved|test|scheduled|processed|registered|done|...
created: 2026-06-22T09:00:00+09:00
# 任意: target_month / week / scheduled_send / blocked / execute_command
---
```

許容 status: `pending` `approved` `test` `scheduled` `processed` `registered` `done` `completed` `sent` `skipped` `failed`。

## 承認モデル(3 種・registry の `approval` で宣言)

| モデル | 意味 | status:approved で何が起きるか |
|---|---|---|
| **AUTO** | 承認すると send_pending が自動実行(`dispatcher`=line_send/shell) | ディスパッチ実行 → processed |
| **CONVERSATIONAL** | 会話で承認 → bot / Claude セッションが実行(SNS 予約・経費/請求登録) | **自動配信しない**。会話で実行。誤って approved にしても黙って archive(エラーにしない) |
| **FYI** | 承認不要の通知だけ(録音 digest・財務投げかけ・朝 Triage) | 表示されたら役目終わり |

⚠️ **SNS など CONVERSATIONAL は `status: approved` にしない**(承認は Discord で「〜予約して」)。

## 不可侵の原則

1. **古いデータにフォールバックしない** — 入力(画像など)が無い/取得失敗なら、古い手元データで
   board を捏造せず、**リマインド通知だけして終わる**(SNS の stale fallback 事故の教訓)。
2. **pending = 承認待ちだけ** — 終端ステータスを pending に残さない。
3. **日本語タイトルを付ける** — `title:` か registry で、用件が一目で分かるように。
4. **必ず registry に登録** — board を作る種は `board_registry.REGISTRY` に1行。未登録は lint が ERROR。

## 新しく board を作る種を足すとき(手順)

1. [`board_registry.py`](../services/garden-gaku-co/board_registry.py) の `REGISTRY` に1行追加
   (`kind` 種別ラベル / `title` / `approval` / `dispatcher`)。
2. 種 frontmatter の `name`/`plot` を registry のキー(`{plot}/{name}`)と一致させる。
3. `python board_lint.py` が **違反なし** になることを確認。
4. AUTO の場合のみ `dispatcher`(line_send/shell)を設定。CONVERSATIONAL/FYI は `None`。

## board の実体はどこにあるか(ホスト)★必読

> **board の住所は VPS 一箇所。repo に board のコンテンツ用ディレクトリは無い。**
> repo には `garden/board/pending/` を**置かない**(S57 で撤去)。board の状態を
> ローカルで `ls` して断定しないこと。

- **唯一の住所 = VPS `/home/vps-harappa/garden/board/pending/`**。すべての pending board は
  ここに集まる(= board content の単一の真実)。`send_pending.py`・ダッシュボード・
  朝ブリーフィングはすべてここを読む。
- **VPS で動く種(`execution_host: vps`: SNS / finance / expense …)は VPS に直接書く。**
- **ローカルで動く種(`execution_host: local`: scribe / Plaud 系)** は、board を一旦
  `garden/services/scribe/outbox/`(scribe 内部の一時置き場・`.gitignore` 対象)に書き、
  `run-local.sh` が VPS の `board/pending/` へ push したのち **outbox を空にする**。
  → ローカルに board は溜まらない。repo の `garden/board/` にあるのは本 README とルールだけ。
- **状態を確認する正しい手段**: ダッシュボード(`core.harappa.monster/board`)/ 朝ブリーフィング /
  直接見るなら `ssh harappa 'ls /home/vps-harappa/garden/board/pending/'`。

> なぜこうしたか(S57): 旧設計は scribe が repo の `board/pending/` に board を書いて溜め、
> `rsync --ignore-existing` で VPS へ push していた。これが ①ローカルに古い board が墓場化
> ②更新が VPS に届かず食い違う、の2つの実害を生み「board が repo にあるのか VPS にあるのか」を
> 不明にした。住所を VPS 一箇所に統一して撤去。

## どこで見るか

- **ダッシュボード(閲覧専用)**: https://core.harappa.monster/board(承認待ちだけ・markdown 整形表示)
- **朝ブリーフィング**: 承認待ち board を冒頭に列挙
- **Discord master**: pending 着信時に通知(種別 + 日本語タイトル)
- **番人**: board 規約違反(ERROR)を検出したら Discord master に通知

## 一元管理の構成(まとめ)

| 層 | 実体 | 役割 |
|---|---|---|
| 正本(ルール) | 本ファイル | 人間が読む契約 |
| レジストリ(データ) | `board_registry.py` | 種ごとの振る舞いを1テーブルに |
| エンジン(実行) | `send_pending.py` | 分類・通知・ライフサイクル・配信を registry 由来で一括 |
| リンター(enforcement) | `board_lint.py` | 正本/registry への違反を機械検出 → 番人/ダッシュボード |
| 入口(新規作成) | `plot_gardener` SKILL | 新区画作成時に本正本へ通す |
