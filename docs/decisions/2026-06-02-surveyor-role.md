# 測量士(外部視点 AI)を HMG に導入する

- **日付**: 2026-06-02
- **記録**: セッション25
- **決定者**: ガクチョ(庭師) / Claude Code
- **ステータス**: 合意・実装完了(`docs/surveyor/` 新設 + README + テンプレ + 語彙・MAP・CLAUDE.md への周知)
- **前提**: [HMG コンセプト](../concept.md)、[Garden 語彙](../garden-vocabulary.md)、[CHARTER](../../garden/CHARTER.md)

## 背景

HMG は S0〜S24 までで急速に育ち、 **board ライフサイクル・菌糸・永続記憶・shift_manager・kodomon 連携** など複数の区画とサービスが同時並行で進んでいる。ガクチョ自身も日々増える仕様要件で全体像を把握しづらくなってきた。

Claude Code は実装の伴走者として議論に深く入り込むため、 **「俯瞰」が効きにくい構造的限界** がある。設計議論が長期化したり、複雑性が積み上がっても、その内側にいる Claude Code には地形のゆがみが見えづらい。

そこで **別系列の LLM(codex)に外部観測者として定期入場してもらう** ことで、HMG の目的との整合性・複雑化・正本関係のほつれを定期的に俯瞰してもらう運用を導入する。

## 決定

### 決定 1: 測量士は **外部視点** として位置づける(庭の役者ではない)

| 役割 | Garden 語彙 | 主な責務 | 位置 |
|---|---|---|---|
| ガクチョ | 庭師 (Gardener) | 戦略決定・最終承認・剪定 | 庭の縁 |
| Claude Code | (実装者) | 設計議論・実装・反映 | 庭の中(伴走) |
| codex | **測量士 (Land Surveyor)** | 外部視点での俯瞰・整理・助言 | 庭の外 |

測量士は **庭の中で動く役者ではない**(植物・番人・菌糸・草木の精とは異なる)。庭の縁の外側から地形を測る存在として位置づける。

### 決定 2: 配置は `docs/surveyor/`(`garden/` ではない)

外部視点であること、観測・記録の場であることから `docs/` 直下とする。`garden/` は庭の中の機構(plot / seeds / services / soil / mycelium 等)に予約する。

```
docs/surveyor/
├── README.md          ← 役割定義 + 運用フロー(正本)
└── letters/
    ├── TEMPLATE.md    ← 手紙の雛形(削除しない)
    └── YYYY-MM-DD.md  ← 手紙本体(1 日 1 通、2 通目以降は -NN.md)
```

### 決定 3: 手紙の運用フロー

- **起動**: ガクチョ判断で任意発火(定期 cron はしない、形骸化を避ける)
- **入力**: ガクチョが codex に MAP / 最新 session を渡す(または codex が repo 直読み)
- **出力**: codex が `letters/YYYY-MM-DD.md` を新規作成(`TEMPLATE.md` ベース)
- **応答**: Claude Code が同ファイルに `## Claude Code の応答` セクションを追記(必須・短文 OK)
  - 提案ごとに **採用 / 却下 / 保留** を明示
- **介入**: ガクチョが意見したい場合は `## ガクチョのメモ` を追記
- **昇格**: 設計判断レベルの採用は ADR 化(手紙はあくまでも観測と助言、ADR は決定)

詳細: [`docs/surveyor/README.md`](../surveyor/README.md)

### 決定 4: 測量士の **やらない** リスト

- repo ファイルの直接編集(letters/ への新規作成のみ可)
- MAP.md / ADR / session / SKILL / seed / service / workflow / secret / runtime data の改変
- 一般論だけの助言(HMG の文脈・Garden 語彙・既存 ADR に照らさない助言は NG)
- 宿題を増やしすぎる行為(本当に効くものを絞る)
- Claude Code との競合(代替ではない)

### 決定 5: 周知の射程

| 場所 | 内容 |
|---|---|
| [`docs/garden-vocabulary.md`](../garden-vocabulary.md) | **測量士** を外部視点として追加(基本語彙とは別セクション) |
| [`CLAUDE.md`](../../CLAUDE.md) | Garden 語彙表に 1 行追加 + 「設計議論の蓄積場所」に `docs/surveyor/` 追加 |
| [`garden/MAP.md`](../../garden/MAP.md) | 区画別ステータス表に 1 行追加(`docs/surveyor/`、状態 = 🌱) |
| [`garden/CHARTER.md`](../../garden/CHARTER.md) | **書かない**(CHARTER は plot 内の役者用、測量士は対象外) |

## 影響

- ガクチョの俯瞰負荷が下がる(別系列 AI に外部レビュー任せ可能)
- Claude Code とガクチョの議論に第三の視点が加わる(セカンドオピニオン)
- 設計判断の質が上がる(複雑化を早めに検知できる)
- 運用負荷は最小(手動起動・短い応答で済む設計)

## リスクと対処

| リスク | 対処 |
|---|---|
| 手紙が宙に浮く(Claude Code が応答しない) | 応答セクション必須化 + 24h 以内ルール |
| 提案が形骸化(全部 「採用」 or 全部 「却下」) | 採用/却下/保留の 3 値判定を強制、保留には判断条件を書く |
| 宿題が膨れる | 測量士に「3〜5 件まで」のガードを明記、ガクチョが取捨選択 |
| codex と Claude Code が同じファイルを同時編集 | codex は新規作成のみ、Claude Code は応答セクション追記のみ。書き込み区間が分離 |
| 「外部視点」の独立性が損なわれる(Claude Code の議論履歴を渡しすぎる) | codex への入力は MAP + 最新 session を最小単位とし、ガクチョが必要分だけ追加 |

## 関連

- [`docs/surveyor/README.md`](../surveyor/README.md) — 運用フローの正本
- [`docs/surveyor/letters/TEMPLATE.md`](../surveyor/letters/TEMPLATE.md) — 手紙の雛形
- [`docs/garden-vocabulary.md`](../garden-vocabulary.md) — 測量士の語彙位置
- [`garden/MAP.md`](../../garden/MAP.md) — 区画別ステータス
- [`CLAUDE.md`](../../CLAUDE.md) — プロジェクト全体の入口
