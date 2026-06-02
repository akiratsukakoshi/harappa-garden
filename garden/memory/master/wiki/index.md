---
scope: master
layer: wiki
type: index
created: 2026-06-02
last_updated: 2026-06-02
last_updated_by: mycelium (Mode 1 ingest-raw, 2026-06-02)
---

# master memory wiki — 主題一覧

Discord master scope の対話から抽出した **判断・評価・意図** を主題別に整理する wiki の索引。

ADR: [docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md](../../../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)
書き手: 菌糸 Mode 1 Ingest(seed: `mycelium/ingest-raw`、cron 03:30 JST)

## 主題

事前定義 7 主題 + 運用で増える可能性のある新規主題を列挙。各主題ページは `{topic}.md` で参照。

### 事前定義 7 主題(セッション23 庭師合意)

| スラグ | 概要 | ページ |
|---|---|---|
| `staff_assignment` | スタッフの役割・配置・契約 | (未生成) |
| `event_planning` | イベント企画・調整 | (未生成) |
| `business_strategy` | 事業方針・サービス改廃 | (未生成) |
| `client_relations` | クライアント・パートナー関係 | (未生成) |
| `tech_infra` | Garden / VPS / インフラ | [tech_infra.md](tech_infra.md) |
| `personal_reflection` | 庭師個人の振り返り・気持ち | (未生成) |
| `daily_operation` | 日々の運営調整 | [daily_operation.md](daily_operation.md) |

### 新規追加(LLM 命名、運用で増える)

(まだなし)

## ルール

- 菌糸 Mode 1 が振り分け時に該当主題ファイルを **追記**(append-only)
- 該当主題なし → kebab-case で新規命名 → 本 index と新ファイルを同時生成
- 重複・矛盾の整理は菌糸 Mode 2 Lint(Stage 2、将来)で実施

## 関連

- 菌糸 SKILL: [garden/mycelium/SKILL.md](../../../mycelium/SKILL.md) Mode 1
- 種: [garden/seeds/mycelium/ingest-raw.md](../../../seeds/mycelium/ingest-raw.md)
- 入力 RAW: [../raw/](../raw/) (.gitignore 除外、機密扱い)
