# people/ — 「人」区画

土壌における「人」のエンティティページ群。

## サブカテゴリ

| ディレクトリ | 対象 |
|---|---|
| `staff/` | HARAPPA(株)のスタッフ — 代表・運営・業務委託・アルバイト |
| `clients/` | クライアント企業の **担当者**(個人)— 企業本体は `soil/clients/` |
| `partners/` | パートナー(京急電鉄等)の窓口担当者 |

## 区別の指針

- **staff vs clients/担当**: HARAPPA から給与/業務委託料を払う相手 = staff。お金を払ってくれる/協業相手 = clients/担当
- **clients vs partners**: 通常の取引関係 = clients、共同事業(みうらの森林等)の相手 = partners

## 命名規約

slug = `<first-name>-<last-name>` (romaji、kebab-case)
例: `akira-tsukakoshi`, `yuji-wada`

同名対策: ミドルネーム挿入 or サフィックス(`-2`)。

## frontmatter スキーマ(共通)

各サブカテゴリの README で固有フィールドを定義。
