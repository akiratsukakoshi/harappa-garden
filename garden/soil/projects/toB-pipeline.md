---
type: soil_project_index
domain: toB
fiscal_year: 2025
last_updated: 2026-06-17
source: soil/finance/discussions/20260617_経営分析・見込み修正.md(5/19 から更新)
status: draft   # 各案件の個別ファイル化・clientリンクは宿題(README 参照)
---

# toB 案件パイプライン(FY2025)

> **6/17 更新版**(5/19 スナップショット → ガクチョ修正反映)。各案件を個別ファイルに昇格 +
> [soil/clients/](../clients/) にリンクするのが宿題([README](README.md))。金額は税抜・計上月ベース。

## 確定〜見込み案件

| 案件 | クライアント | 金額 | 計上月 | 確度 | freee反映 |
|---|---|--:|---|---|---|
| MTI研修 | MTI | 227.3万 | 2026-05 | 確定 | ⚠️ 未反映(請求発行済) |
| 白井松研修 | 白井松 | 75万 | 2026-05 | 確定 | ⚠️ 未反映 |
| パナソニックホームズ①(みずき台運営) | パナソニックホームズ | 120万 | 2026-06 | 確定 | ⚠️ 要確認([台帳](../clients/panasonic-homes/projects/みずき台住民イベント運営/README.md)) |
| ゴンチャ社員総会 | ゴンチャ | 40万 | 2026-06 | 確定 | — |
| boundlesslife② | boundlesslife | 30万 | 2026-07 | 見込み | — |
| **MTI経営研修** ← 6/17追加 | MTI | **120万** | 2026-07 | 見込み | — |
| パナソニックホームズ②(みずき台運営) | パナソニックホームズ | 110万 | 2026-09 | 確定 | ⚠️ 要確認([台帳](../clients/panasonic-homes/projects/みずき台住民イベント運営/README.md)) |
| MTI経営者/AI研修 | MTI | 150万 | 2026-09 | 見込み | — |
| **デジハラ(AI関連)** ← 6/17追加 | — | **70万** | 2026-09 | 見込み(純増) | — |
| 三井塚越プロジェクト | 三井 | 10万/月 | 毎月 | 確定 | — |
| boundlesslife① | boundlesslife | 24.7万 | 2026-04 | 確定 | ⚠️ 未反映 |
| ~~フージャース若手研修~~ | ~~フージャース~~ | ~~150万~~ | ~~2026-08~~ | **❌ 6/17 除外(なさそう)** | — |
| ~~フージャース内定者研修~~ | ~~フージャース~~ | ~~150万~~ | ~~2026-09~~ | **❌ 6/17 除外(なさそう)** | — |

## 共創(toB・継続)

| 案件 | クライアント | 金額 | 期間 | 備考 |
|---|---|--:|---|---|
| 京急 共創プロジェクト | 京急 | 20万/月 | 2026-05〜**毎月継続** | 6/17確定。FY2025は5〜9月計上、**10月以降も継続=来期の安定土台** |

## 上振れ余地(確度未定)

- MTI・一丸ファルコスの追加案件の目
- AI研修(toB)のアドオン展開

## クライアント正本化の進捗(S48〜)

各案件を企業正本 [soil/clients/](../clients/) に展開し、a〜f(打合せ/資料/見積/実績/請求)+ finance を1枚に集約していく。

| クライアント | 状態 | 正本 |
|---|---|---|
| **MTI** | ✅ 型の参照実装(第1号) | [soil/clients/mti/](../clients/mti/)(新人研修[請求実物]/経営研修2026[Plaud 3本+台帳]/経営者研修[見積実物]) |
| **パナソニックホームズ** | ✅ 横展開2号(S49・メールのみで縦通し) | [soil/clients/panasonic-homes/](../clients/panasonic-homes/)(みずき台住民イベント運営=継続・四半期請求。Plaud 無し=ドメイン起点で骨格) |
| ゴンチャ / boundlesslife / 白井松 / 三井 / 京急 | ⬜ 未着手 | MTI/パナHM を参照実装に横展開 |

> 構造仕様 = [soil/clients/README.md](../clients/README.md)。見積/請求様式 = [soil/finance/templates/](../finance/templates/)。

## 関連

- 着地予測・目標: [soil/finance/targets.md](../finance/targets.md)
- 議論の経緯: [soil/finance/discussions/](../finance/discussions/)
- クライアント正本: [soil/clients/](../clients/)
- AI関連(toC)・toC基盤は finance discussions 参照(本ファイルは toB のみ)
