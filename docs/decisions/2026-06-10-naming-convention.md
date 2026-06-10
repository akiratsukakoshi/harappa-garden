# ADR: HMG 命名規約(underscore / hyphen の使い分け)

日付: 2026-06-10
セッション: 39
ステータス: 採用(新規作成分から適用。既存はリネームしない)

## 文脈

S39 のプロジェクトレビューで、同一区画の実装が表記揺れしていることが指摘された:

```
garden/plots/expense_processor/      ← underscore
garden/services/expense-processor/   ← hyphen
garden/plots/shift_manager/          ← underscore
garden/services/shift-manager/       ← hyphen
garden/plots/daily-pilot/            ← hyphen(plots 内でも揺れ)
```

命名規約が文書化されていないため、新しい区画・サービス・種を作るたびに
「どちらの記法か」を毎回判断しており、揺れが拡大する構造だった。

## 決定

**レイヤーごとに記法を固定する**(レイヤー内の一貫性 > レイヤー間の一致):

| レイヤー | 記法 | 理由 | 例 |
|---|---|---|---|
| Python パッケージ・モジュール(`lib/` 等 import されるもの) | **underscore** | PEP 8。hyphen は import 不可 | `freee_client.py` |
| `garden/plots/{name}/`(区画) | **underscore** | SKILL から Python 資産への参照が多く、業務名の同一性を保つ | `expense_processor` |
| `garden/services/{name}/`(サービス) | **hyphen** | daemon / コンテナ / Unix サービスの慣習 | `expense-processor` |
| `garden/seeds/` の種ファイル・bash スクリプト | **hyphen** | Unix ファイル名慣習(既存の種は全て hyphen) | `monthly-expense-draft.md` |
| Docker コンテナ名 | **hyphen** | Docker 慣習 | `garden-gaku-core` |

つまり **「plot(業務名)= underscore、実行体(サービス・種・コンテナ)= hyphen」**。
`garden/plots/daily-pilot/` は例外(参照が多いため現名を維持)。

## 既存ディレクトリはリネームしない

リネーム=住所変更であり、以下が古い住所を直書きしているため、物理リネームは行わない:

- VPS crontab(launcher の `--seed` パス、cron 17 本)
- S38 で設定した bot の scoped Bash 許可(**絶対パス `:*` 形式**。パスが変わると許可が外れる)
- 種 frontmatter の `execute_command`(S38 で全て絶対パス化済み)
- send_pending.py の allowlist prefix(S39)

S36 の障害(参照切れによる cron 沈黙)と同型のリスクを自ら作ることになるため、
**「新規から適用、既存は歴史的経緯として注記」** を採用する。

## 却下した代替案

| 案 | 却下理由 |
|---|---|
| 全レイヤー underscore に統一 + 既存リネーム | 上記の参照切れリスク。得られるのは見た目の一貫性のみ |
| 全レイヤー hyphen に統一 | Python import が不可能になる(`lib/` 構造と矛盾) |

## 影響

- plot_gardener(Mode 4 Garden Design / Mode 5 Implementation Plan)で新規 plot / service / 種を
  起草する際は本 ADR の表に従う
- `garden/plots/plot_gardener/SKILL.md` に本 ADR への参照を追記するのが望ましい(宿題)
