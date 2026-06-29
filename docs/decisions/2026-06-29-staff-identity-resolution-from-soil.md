# 2026-06-29 ADR — スタッフ人物特定は staff soil を正本にする

- **日付**: 2026-06-29
- **決定者**: ガクチョ(庭師) / Codex コーディング担当
- **ステータス**: Accepted

## 背景

meeting_coordinator のスポット会議作成で、core_team LINE の依頼文
「7/2 8-9時でがくちょーとゆうじのミーティングを設定」が正しく実行されなかった。

直接の問題は2つあった。

1. 固定日時の会議作成依頼が候補調整ルートに流れ、Zoom / Calendar 作成に進まなかった。
2. `ゆうじ` / `ゆーじさん` / `Yuji WADA` のような人物表記ゆれを、行動 tool 側が十分に解決できなかった。

調査すると、meeting_coordinator は `garden/soil/people/staff/` を少し参照していたが、
実態は `DEFAULT_PARTICIPANTS` の4名を起点に email / nickname を補強するだけだった。
つまり staff soil は存在するが、人物特定の正本として使い切れていなかった。

## 決定

### 1. スタッフ人物特定の正本は `garden/soil/people/staff/`

Garden 内の tool / service / LINE deterministic route がスタッフを特定するときは、
個別 tool 内の固定辞書を第一正本にしない。

まず `garden/soil/people/staff/*.md` を読み、各 staff ページの情報を名前解決辞書として使う。

特に以下を alias として扱う。

- ファイル stem(slug): `yuji-wada`
- H1 見出し: `# 和田 祐司(ユージさん)`
- H1 の空白除去表記: `和田祐司`
- H1 の括弧内表記: `ユージさん`
- frontmatter `nicknames`
- frontmatter `line_display_name`
- `line_display_name` の括弧内表記
- 空白あり / 空白なしの表記ゆれ

### 2. 固定辞書は fallback / 表示名補助に限定する

`DEFAULT_PARTICIPANTS` のような service 内辞書は、core team の初期表示名や fallback email を持つために残してよい。
ただし、人物特定の拡張は staff soil から行う。

新しいスタッフや nickname を増やす場合は、原則として tool 側のコードではなく staff soil を更新する。

### 3. 入力の呼称ゆれは受け入れ、出力で正規化する

CHARTER の呼称規範は「ガクコがどう呼ぶか」の規範であり、ユーザー入力を拒否するための検閲ではない。

たとえば `がくちょー` / `ガクチョー` / `塚越さん` は入力として受け入れ、内部では `akira-tsukakoshi`、出力では `ガクチョ` に正規化する。
同様に `ゆうじ` / `ゆーじさん` / `Yuji WADA` / `和田さん` は `yuji-wada` に解決する。

### 4. エラーはユーザーに返す

LINE 発話を起点にした tool / deterministic route は、実行失敗をログだけに閉じ込めない。
例外は捕捉し、`会議作成に失敗しました(...)` のように、発話元へ短く返す。

ただし、実装者が VPS CLI で直接実行した検証コマンドの失敗は LINE 発話ではないため、LINE には返らない。

## 実装

2026-06-29 に meeting_coordinator で以下を実装した。

- `processor._participant_registry()` が staff soil 全体を読み、H1 / nicknames / line_display_name を alias 化
- `processor.extract_participants_from_text()` を追加し、自然文から staff slug を抽出
- LINE deterministic route の固定日時会議作成が、固定 alias ではなく meeting_coordinator の soil ベース抽出を使うよう変更
- `ゆーじさん` / `ゆうじ` / `Yuji WADA` / `けーちゃん(鈴木 慶)` 等の回帰テストを追加

## 影響

- 人物表記ゆれの追加は staff soil 更新で吸収できる。
- meeting_coordinator 以外の service も、人物特定が必要な場合はこの方針に寄せる。
- service 内に独自の人名辞書を増やす場合は、fallback / 表示名 / scope 限定の例外として扱い、staff soil と二重管理しない。
- core_team LINE では、ユーザー入力の呼称ゆれを理由に実行を止めない。

## 関連

- [2026-06-02 soil の正本と 3 箇所配置の同期ルール](2026-06-02-soil-source-of-truth.md)
- [2026-06-03 対話層のベンダー中立アーキテクチャ](2026-06-03-vendor-neutral-interaction-layer.md)
- [garden/soil/people/staff/](../../garden/soil/people/staff/)
- [garden/services/meeting-coordinator/processor.py](../../garden/services/meeting-coordinator/processor.py)
