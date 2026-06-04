# 業務 Garden 化の型(plot_gardener)+ 語彙の 2 register 整理

- 日付: 2026-06-04(セッション33)
- status: accepted
- 関係者: ガクチョ(庭師)、Claude Code(実装)、codex 測量士(手紙起点)
- 起点: [測量士の手紙 2026-06-03](../surveyor/letters/2026-06-03.md) + [plot_gardener SKILL サンプル](../surveyor/letters/2026-06-03-plot-gardener-skill-sample.md)

## 背景

HMG は基盤整備(中立対話層・社内 LINE サーバ・永続記憶)を越え、「業務単位で区画を増やす」段階に入った。ガクチョのニーズは「shift_manager / daily-pilot と同じことを効率的に量産したい」。

ここで個別 tool を場当たり的に増やすと、HMC 的な「便利関数の集合」に逆戻りする(測量士の警告)。逆に毎回ゼロから区画を設計すると判断が多すぎて速度が落ちる。必要なのは **業務を区画化するときの標準入力・標準出力(=型)**。

測量士が 5 提案 + plot_gardener SKILL サンプルを提示。ガクチョと Claude Code で語彙を揃えたうえで、5 提案すべてを採用した。

## 決定

### 決定 1: 語彙を 2 register に整理する(提案 1 の精緻化)

測量士の「5 層フラット(SKILL/種/tool/service/capability)」を、**2 つの register(言語層)** に整理して採用する。

| register | 語 | 誰の言語か |
|---|---|---|
| 設計言語(Garden 比喩) | 区画・種・**通行手形**・土壌・収穫・剪定 等 | **庭師が設計する層** |
| 実装層(比喩を当てない) | tool・service・provider | **Garden(Claude)が手段を選ぶ水面下** |

- 業務を区画化するとき庭師が設計するのは **区画・種・通行手形** の 3 つだけ。
- **tool / service は水面下**。ガクチョの依頼に出さず、設計判断の単位にもしない。「SKILL と通行手形に定義されていれば、tool の粒度は Garden が決める」。
- 正本は [docs/garden-vocabulary.md](../garden-vocabulary.md)。

### 決定 2: 「業務のパック」= 区画(Plot)と確定する

ガクチョの言う「ワークフロー起点の 種 + SKILL + 通行手形 + service の束」は、Garden 語彙の **区画(Plot)** そのもの。shift_manager / daily-pilot がその第 1・2 号。`plot_gardener` は「区画を作るメタ区画」。

### 決定 3: capability を Garden 語彙「通行手形」に昇格する

`capability`(scope ごとの権限境界)を、語彙表「今後追加候補」から **基本語彙「通行手形」** に昇格。

- 設計議論では「通行手形」を使う。
- **コード内は英語 `capability` を維持**(`capabilities.py` / `tools_for(scope)` 等。実装層の互換性のため)。

### 決定 4: メタ区画 plot_gardener を新設する(提案 2)

`garden/plots/plot_gardener/SKILL.md` を CHARTER 継承型で新設。測量士サンプルをほぼフル移植し、上記語彙合意に統一。Mode 1〜6(Intake / Legacy Inventory / Workflow Spec / Garden Design / Implementation Plan / Review&Promotion)+ サンプル 2 例。

価値は「作業の自動化」より「**毎回の判断を議論から分類に落とす**」こと。初回から自動生成器にはしない。昇格状態 = **test**(最初の 1 業務に当てて active へ)。

### 決定 5: Garden 化モードを 3 つに分ける(提案 3)

`transplant`(移植型・HMC 既存あり)/ `seedling`(新植型・新規)/ `hybrid`(改植型・既存あるが設計を大きく変える)。迷えば hybrid 扱いでレガシーを読む。

### 決定 6: 移植型は Legacy Inventory から始める(提案 4)

`transplant` / `hybrid` では、HMC レガシーを読む前に新規実装しない。合言葉「**業務知識は継承する。起動と承認の形だけ Garden に変える**」。4 分類(そのまま使う / Garden 作法に包む / SKILL に吸い上げる / 捨てる)。`CLAUDE.md` に短く参照を置く。

### 決定 7: 依頼単位を「この業務を Garden 化して」にする(提案 5)

ガクチョが渡すのは **業務名 / mode / MVP の 3 つだけ**。tool / service の粒度は渡さない。`OPERATIONS.md` Card 5 に明記。

## 影響範囲

- 新規: `garden/plots/plot_gardener/SKILL.md`
- 更新: `docs/garden-vocabulary.md`(通行手形昇格 + 2 register 節)/ `garden/OPERATIONS.md`(Card 5)/ `CLAUDE.md`(業務 Garden 化の節)
- 既存 plot(daily-pilot / shift_manager)は遡及変更なし(この型を「後付けで正当化する基準」として機能)。

## 先送り(測量士「先送りしてよいこと」を踏襲)

- tool registry の網羅的整備 / 全 capability の一覧化
- finance / invoice / expense など各業務の詳細実装
- 外部 LLM 乗り換え実装 / staff ALL 向け厳密な情報投影ビュー

→ いずれも「業務 Garden 化の型」を 1 業務で回してから。

## 次の判断(未確定)

**dogfood 第 1 号** をどの業務にするか。候補: shift_manager(型の検証)/ expense_processor(実利・移植本番)/ core_team の LINE read tool 群(デプロイ直後の価値)。plot_gardener を 1 業務に当てて初めて test → active へ昇格できる。

## 関連

- 起点: [測量士の手紙 2026-06-03](../surveyor/letters/2026-06-03.md)
- 前提: [2026-06-03 vendor-neutral-interaction-layer](2026-06-03-vendor-neutral-interaction-layer.md)(通行手形 = capability の実装基盤)
- 語彙正本: [docs/garden-vocabulary.md](../garden-vocabulary.md)
- workflow 原則: [2026-05-24 workflows-as-truth](2026-05-24-workflows-as-truth-and-improvement-targets.md)(目的と現状の方法を分ける = Mode 3 に継承)
