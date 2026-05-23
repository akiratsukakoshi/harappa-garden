---
type: workflow
status: active
dynamism: static
cycle: 年次 + 3ヶ月単位
scope: toC 原っぱ大学 おやこ / こども / おとな
linked_services:
  - "[[parent-child]]"
  - "[[kids]]"
  - "[[adult]]"
linked_staff:
  - "[[akira-tsukakoshi]]"
  - "[[yuji-wada]]"
  - "[[shotaro-shimura]]"
  - "[[kei-suzuki]]"
  - "[[junki-iida]]"
linked_workflows:
  - "[[monthly-cycle]]"
  - "[[program-execution]]"
sources:
  - "塚越さん 2026-05-23 セッション3 投入"
last_updated: 2026-05-23
last_updated_by: claude
---

# (A) 年間カレンダー → 3ヶ月企画反映

> toC 原っぱ大学(おやこ/こども/おとな)の3ヶ月先までの開催を確定させるまでのフロー。年次で骨格を引いて、3ヶ月毎に詳細を肉付けする 2 段ロケット。

## 全体図

```
年始 ─── 年間カレンダー策定 ─┐
                          │
        3ヶ月毎 ───────────┴─→ 月次カレンダー作成
                                    │
                                    ↓
                              企画会議(3ヶ月分)
                                    │
                                    ↓
                             STORES予約 反映 + 月次カレンダー確定
                                    │
                                    ↓
                              企画公開・周知 → [[monthly-cycle]] へ引継ぎ
```

## ステップ

### 1. 年間活動カレンダー策定(年始)

- **時期**: 毎年始
- **担当**: 運営4名 + [[junki-iida]]
- **アウトプット**: [年間カレンダー Sheet](https://docs.google.com/spreadsheets/d/14JuhBGiS2IUiv1F89bCBFEppXeF9paflL6Ll1gxrZGM/) を確定
- **参照**: `shift_manager` SKILL の年間カレンダー管理タスク

### 2. 月次カレンダー作成(3ヶ月に1回)

- **時期**: 3ヶ月に1回
- **担当**: 運営4名 + [[junki-iida]]
- **動き**: 年間カレンダーをフックに、3ヶ月先までの月次カレンダーを引く
- **アウトプット**: [月次カレンダー Sheet](https://docs.google.com/spreadsheets/d/1_RMAQuSb3eWV30WGQ_gsJI5M6Ll1WHvbM4ifkGDuNkM/) を更新

### 3. 企画会議(3ヶ月分)

- **時期**: 月次カレンダー作成と同じ周期(3ヶ月に1回)
- **参加**: 運営4名 + [[junki-iida]]
- **動き**: 各学部の開催内容を確定し、各プログラムに **企画担当者**(運営4名 + 飯田)を割り振る
- **アウトプット**:
  - 各プログラムの企画担当者 = 確定
  - 各プログラムの企画内容 = 確定

### 4. STORES予約 反映 + 月次カレンダー確定

- **担当**: 企画担当者(各プログラム)
- **動き**: 企画内容を [STORES予約](https://stores.jp/) に反映、月次カレンダーも確定
- **アウトプット**: STORES予約上で企画ページが公開可能な状態に

### 5. 企画公開・周知

- **担当**: 企画担当者(コミュニケーションタスクに引継ぎ)
- **動き**: 公開、SNS / メルマガ等での周知
- **次の遷移**: 当月分の運用は [[monthly-cycle]] へ引継ぎ

## 不変条件(invariants)

- **3ヶ月先まで** の月次カレンダーが常に埋まっている状態を維持する
- 企画担当者の割当は **学部固定ではない**(プログラム毎・企画会議毎に割り振り直す)

## 種(自律トリガー)候補 — Phase 3 向けメモ

- 年始(1/1〜): 年間カレンダー策定リマインダー
- 月次カレンダー周期(3ヶ月毎): 企画会議準備リマインダー
