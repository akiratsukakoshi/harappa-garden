# garden/ — HMG 設計層

このディレクトリは **HMG (HARAPPA Management Garden) の設計層**。Garden 語彙(土壌・種・区画・番人・苗床・蔵)が支配する領域で、ここに HMG の「庭」そのものが育つ。

既存の HMC 由来の実装層(`.agent/`, `apps/`, `modules/`)とは棲み分ける。HMC 由来のコードは段階的に `garden/plots/` 配下に Garden 化していく。

## 配下ディレクトリ

| ディレクトリ | Garden 語彙 | 内容 |
|---|---|---|
| `soil/` | **土壌** | コンテキスト基盤(人・事業・クライアント・業務フロー等の統合知識) |
| `seeds/` | **種** | トリガー定義(cron / イベント / 状態変化) ※未着手 |
| `plots/` | **区画** | 業務ドメイン(財務・SNS等)、SKILL の Garden 化版 ※未着手 |
| `watchers/` | **番人** | 監視エージェント ※未着手 |
| `nursery/` | **苗床** | 試行中の業務・新SKILL ※未着手 |
| `kura/` | **蔵** | 長期アーカイブ ※未着手 |

## 設計原則

- **markdown + sqlite + MCP server** を基本(ベンダー中立)
- 土壌は **LLM Wiki 方式**(Karpathy)で育てる — markdown のページ群、frontmatter で構造化、`[[link]]` で関係性
- 編集権限は庭師(塚越さん)とエージェント(Claude)双方が持つ。**すべての変更を `soil/log.md` に追記**
- 判断を含む編集(統合・上書き)は **剪定待ち**(庭師承認)

## 関連

- HMG コンセプト: [docs/concept.md](../docs/concept.md)
- Garden 語彙: [docs/garden-vocabulary.md](../docs/garden-vocabulary.md)
- 由来: [docs/origin.md](../docs/origin.md)
