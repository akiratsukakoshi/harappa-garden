# mycelium — 土壌維持エージェント(菌糸)

> 土の中で網目状に広がり、栄養を分解して各ページに運ぶ存在。見えないが土壌の健全性を支える基盤。

## 位置づけ

Garden 語彙: **菌糸(Mycelium)**(セッション20 追加)。詳細: [docs/garden-vocabulary.md](../../docs/garden-vocabulary.md)。

| 役割 | 担当 |
|---|---|
| 庭師(Gardener) | 意志・決定 |
| 番人(Watcher) | 監視・告げる |
| **菌糸(Mycelium)** ← ココ | **分解・運搬・integrate・index 更新・関係性編み直し** |
| 草木 / 木の精 | 対話(ガクコ等) |

番人と菌糸の違い:番人は「見て告げる」、菌糸は「分解して運ぶ」。責務が違うので独立した役割。

## 責務(soil/README.md に明文化済の3責務をエージェントとして実体化)

| Mode | 内容 | 発火源 |
|---|---|---|
| **Mode 1: Ingest** | 新ソース(議事録・メール・Drive)を読み、該当 soil ファイルに反映、index 追記、log 記録 | watcher(soil/inbox/ への投入を検知)or 種(cron) |
| **Mode 2: Lint** | 矛盾・古い記述・孤立ページ・欠損リンクを検出 → 連絡板に剪定依頼。**創発ログ(`garden/board/emergence/`)の review** も含む(繰り返し起きる創発 = SKILL 書き戻し候補としてガクチョに剪定依頼) | 種(週次 cron) |
| **Mode 3: Index 更新** | soil ファイル編集発生時に [soil/index.md](../soil/index.md) 該当エントリを最新化 | watcher(soil/ 配下の変更検知) |
| **Mode 4: 関係性編み直し** | `linked_*` フィールド整備、`[[link]]` 付与漏れ検出 | 種(月次 cron)or Mode 1/3 から呼ぶ |

## 実装の段階分け(Stage)

| Stage | 何を実装 | タイミング | 状態 |
|---|---|---|---|
| **Stage 1** | Mode 3(Index 更新)= soil/ 配下の変更検知 → index.md 自動追従 | **shift_manager 着手より先**(staff 29名分の index 最新化が前提) | 未着手 |
| Stage 2 | Mode 2(Lint)= 週次 cron | shift_manager 安定後 | 未着手 |
| Stage 3 | Mode 1(Ingest)= 議事録・メール対応 | meetings 連携 / inbox-process と同期 | 未着手 |
| Stage 4 | Mode 4(関係性)= 月次 cron | 全体運用が成熟後 | 未着手 |

## 想定ディレクトリ構造(実装時)

```
mycelium/
├── README.md         # このファイル
├── SKILL.md          # 業務観モジュール(全 Mode 集約、CHARTER 継承)
├── seeds/            # cron 発火源
│   ├── lint-weekly.md
│   ├── relations-monthly.md
│   └── ingest-on-demand.md
├── watcher.py        # soil/ 配下の変更検知 daemon(Mode 3)
└── inbox.py          # soil/inbox/ への投入検知(Mode 1 補助)
```

## 関連

- 土壌: [garden/soil/](../soil/) — 被維持対象
- 土壌の地図: [garden/soil/index.md](../soil/index.md) — 菌糸が最新化を担う
- 共通規範: [garden/CHARTER.md](../CHARTER.md) — soil 参照規約
- 哲学: Karpathy の LLM Wiki(soil/README.md 参照)
- ADR(セッション20): [菌糸の役割と soil 参照規約](../../docs/decisions/2026-05-30-mycelium-and-soil-reference.md)
