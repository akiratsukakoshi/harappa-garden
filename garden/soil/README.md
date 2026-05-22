# soil/ — 土壌(コンテキスト基盤)

> エージェントが自律取得できる、HMG の統合知識層。Karpathy の LLM Wiki 方式で育てる。

## 哲学

知識は時間とともに **複利で蓄積する**。新しい情報源を投げ込むたびに、エージェント(Claude)が:

1. **Ingest** — ソースを読み、サマリを書き、関連エンティティページを更新、`log.md` に追記、`index.md` を更新
2. **Query** — 土壌に対する質問に答え、必要なら回答を新しいページとして残す
3. **Lint** — 矛盾・古い記述・孤立ページ・欠損リンクを定期チェック

人間(庭師)は **ソースを投げる/質問する/剪定する** に集中し、bookkeeping は LLM が引き受ける。

## ディレクトリ構造

```
soil/
├── README.md          # このファイル
├── index.md           # 土壌の全エントリ一覧(LLM が更新)
├── log.md             # 編集ログ(追記専用)
│
├── people/            # 「人」
│   ├── staff/         # スタッフ(代表・運営・業務委託・アルバイト)
│   ├── clients/       # クライアント企業の担当者(個人)
│   └── partners/      # パートナー(京急電鉄等の窓口)
│
├── business/          # 事業構造(toC/toB のサービス群)
│
├── clients/           # クライアント企業
├── projects/          # 進行中プロジェクト(動的)
├── workflows/         # 業務フロー(静的) — event/client-work/monthly/seasonal
├── events/            # 個別イベント(動的)
├── meetings/          # 議事録インデックス(本体は Plaud/Drive)
└── concepts/          # 概念ページ(seasons, garden-philosophy 等)
```

## 動的・静的の区分

各ページは更新頻度で 3 段階に区分される(frontmatter `dynamism` で表現):

| 区分 | 更新頻度 | Wiki への保存 |
|---|---|---|
| **static** | 月〜年 | 本体を Wiki に置く(業務フロー、事業構造、概念) |
| **dynamic** | 日〜週 | 要旨を Wiki に + 外部参照(クライアント状態、プロジェクト進捗) |
| **super-dynamic** | 時間〜日 | Wiki に置かない、MCP で都度照会(予約状況、メール、カレンダー) |

## frontmatter スキーマ(共通)

```yaml
---
type: staff | client | partner | project | event | service | workflow | concept
status: active | inactive | alumni | archived
dynamism: static | dynamic | super-dynamic
sources:
  - "Freee Partner DB"
  - "Drive: スタッフ一覧"
last_updated: 2026-05-22
last_updated_by: claude | gardener
---
```

各 type 固有のフィールドは、その type の README.md に定義。

## リンク規約

- 内部リンク: `[[slug]]` 形式(Karpathy wiki 流)。slug = ファイル名(拡張子なし)
- 例: `[[akira-tsukakoshi]]`、`[[2026-spring-camp]]`、`[[miura-forest]]`
- 関係性は frontmatter の `linked_*` フィールドで構造化(例: `linked_clients`, `linked_services`)
- 本文中にも `[[link]]` を書いてよい(grep/Obsidian 両対応)

## 編集の規律

### 自律実行してよい編集(Claude)
- 新規 ingest(議事録読んで該当エンティティに追記)
- 軽微な整合性修正(typo、リンク切れ、明白な抜け)
- `index.md` / `log.md` の自動更新

### 剪定待ち(庭師承認)が必要な編集
- エンティティの統合(クライアント A と B を統合する等)
- 過去発言と矛盾する記述の上書き
- 構造変更(新カテゴリの追加、ディレクトリ再編)
- 削除(archive 移動を含む)

## ログのルール

`log.md` は **追記専用**。フォーマット:

```markdown
## [YYYY-MM-DD] action | title
- by: claude | gardener
- type: ingest | edit | lint | prune
- pages: [[slug1]], [[slug2]]
- summary: 一行要約
- source: 参照元(あれば)
```

## index.md のルール

`index.md` は **土壌の地図**。ingest が走るたびに LLM が更新。各エントリは一行サマリ。

## 参考

- Karpathy の LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
