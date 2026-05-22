# HMG 庭の見取り図

> **常に最新**。セッションごとに更新する。塚越さん(庭師)が「今どこにいるか」を1ページで把握するためのファイル。

## 一行で

HARAPPA Management Garden (HMG) は AI中心の経営運用プラットフォーム。
庭師=塚越さん、エージェント群=自律的に育つ生態系。HMC(操縦席)からの進化版(庭=育てる生態系)。

## 現在地 @2026-05-22

- **設計フェーズ**: 土壌の最小実装中(Phase 1)
- **直近セッション**: [2026-05-22 セッション1](../docs/sessions/2026-05-22-session1.md)
- **直近の重要決定**: 土壌方式 = Karpathy LLM Wiki / スキーマ = role 1軸 / 機微情報は Wiki に書かない

## 区画別ステータス

凡例: ⬜未着手 / 🌱育成中(骨格あり) / 🌳成熟 / 🍂休耕 / 🥗収穫済

| Garden 語彙 | パス | 状態 | 一行 |
|---|---|---|---|
| 土壌 (soil) | [garden/soil/](soil/) | 🌱 | 骨格 + スタッフ4 + 事業骨格21 + 退任7 + レビュー80 |
| 土壌-people/staff | [soil/people/staff/](soil/people/staff/) | 🌱 | 4名確定 + alumni + 80名レビュー待ち |
| 土壌-people/clients | [soil/people/clients/](soil/people/clients/) | ⬜ | クライアント担当者(個人) |
| 土壌-people/partners | [soil/people/partners/](soil/people/partners/) | ⬜ | パートナー窓口 |
| 土壌-business | [soil/business/](soil/business/) | 🌱 | 21ファイル骨格、各サービスの中身埋め待ち |
| 土壌-clients | [soil/clients/](soil/clients/) | ⬜ | クライアント企業本体 |
| 土壌-projects | [soil/projects/](soil/projects/) | ⬜ | 進行中プロジェクト |
| 土壌-workflows | [soil/workflows/](soil/workflows/) | ⬜ | 業務フロー(event/client-work/monthly/seasonal) |
| 土壌-events | [soil/events/](soil/events/) | ⬜ | 個別イベント |
| 土壌-meetings | [soil/meetings/](soil/meetings/) | ⬜ | 議事録インデックス(Plaud等) |
| 土壌-concepts | [soil/concepts/](soil/concepts/) | ⬜ | 概念ページ(season/garden-philosophy 等) |
| 種 (seeds) | garden/seeds/ | ⬜ | トリガー(cron/event/状態変化)定義 |
| 区画 (plots) | garden/plots/ | ⬜ | HMC SKILL の Garden 化版 |
| 番人 (watchers) | garden/watchers/ | ⬜ | 監視エージェント |
| 苗床 (nursery) | garden/nursery/ | ⬜ | 試行領域 |
| 蔵 (kura) | garden/kura/ | ⬜ | 長期アーカイブ |

## ロードマップ(Phase)

### Phase 1: 土壌の最小実装 ← **現在地**

土壌の主要カテゴリ(人・事業・クライアント・フロー・議事録)に **骨格** を持たせる。中身は順次埋める。

- [x] コンセプト・ネーミング(2026-05-22 セッション1)
- [x] garden/ + soil/ 骨格(README/index/log)
- [x] スタッフマスター骨格(4名 + alumni + レビュー80名)
- [x] 事業構造骨格(toC/toB/communication 21ファイル)
- [ ] クライアント企業一覧(`soil/clients/`)
- [ ] 業務フロー(`soil/workflows/`) — 塚越さんソース提供待ち
- [ ] 議事録インデックス(`soil/meetings/`) — Plaud 連携

### Phase 2: 剪定の規律(承認境界)

土壌の輪郭が見えたら、エージェントの自律実行 vs 庭師承認の境界を設計。

- [ ] 自律実行 vs 剪定待ちの境界文書化
- [ ] 通知方法(連絡板/高札)の設計
- [ ] LINE 通知連携(まずは塚越さん個人、後にチーム)

### Phase 3: 種(自律トリガー)

エージェントが自律起動できる仕組み。

- [ ] cron / event / 状態変化 のトリガー定義(`garden/seeds/`)
- [ ] MCP server 実装(土壌へのアクセス層)
- [ ] 既存ソース(Square予約・Notion・Plaud)の ingest

### Phase 4: 区画の Garden 化

HMC SKILL を順次 HMG に移植・自律化。

- [ ] HMC SKILL の Garden 化(finance_importer → invoice_processor → ...)
- [ ] 番人エージェントの実装(`garden/watchers/`)
- [ ] チームメンバー(LINE 経由)への開放準備

## 直近の宿題

### 庭師(塚越さん)
- [ ] [_review-2026-05-22-master-data-candidates.md](soil/people/staff/_review-2026-05-22-master-data-candidates.md) の 80名レビュー(気が向いたタイミング)
- [ ] `business/` 各サービスページの中身埋め(or Claude が他ソースから合成)
- [ ] `workflows/` のソースドキュメント提供(イベント時/クライアントワーク時/月間)
- [ ] Square予約 / Notion / Plaud のシェア(Phase 3 で必要)

### Claude
- [ ] 次回セッション開始時に本 MAP.md と最新セッション記録を読む
- [ ] 塚越さんが選んだ次の議論候補に着手

## 主要な決定の索引

| 決定 | 日付 | 記録場所 |
|---|---|---|
| HMG ネーミング | 2026-05-22 | [decisions/2026-05-22-naming.md](../docs/decisions/2026-05-22-naming.md) |
| 土壌方式 = Karpathy LLM Wiki | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| スキーマ = role 1軸 + 機微情報 Wiki 外置き | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| 慶ちゃん追加・「運営」表記統一 | 2026-05-22 | [CLAUDE.md](../CLAUDE.md) |
| Obsidian は分離 + 読み取り参照 | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |
| 業務フロー = ハイブリッド配置 | 2026-05-22 | [sessions/2026-05-22-session1.md](../docs/sessions/2026-05-22-session1.md) |

## 直近のセッション

- [2026-05-22 セッション1](../docs/sessions/2026-05-22-session1.md) — HMG 立ち上げ・土壌+業務骨格構築

## 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md) — プロジェクト規約
- [docs/concept.md](../docs/concept.md) — HMG コンセプト(育てる文書)
- [docs/garden-vocabulary.md](../docs/garden-vocabulary.md) — Garden 語彙
- [docs/origin.md](../docs/origin.md) — HMC からの由来
- [garden/README.md](README.md) — garden/ 配下の構造
- [garden/soil/README.md](soil/README.md) — 土壌の運用ルール
