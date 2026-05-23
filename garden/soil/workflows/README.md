---
type: index
status: active
dynamism: static
scope: 業務フロー(共通)
last_updated: 2026-05-23
last_updated_by: claude
---

# workflows/ — 業務フロー(共通)

> 複数の事業・サービスを横断する業務フローを置く。事業特化のフローは [business/](../business/) 配下の各サービスページに書く(ハイブリッド配置・[2026-05-22 セッション1](../../../docs/sessions/2026-05-22-session1.md) 決定)。

## 現状(2026-05-23 セッション3 で初期化)

対象スコープ: **toC 原っぱ大学 おやこ / こども / おとな の3定期学部**(toC 1-a/b/c)。
その他の toC(放課後サボール・俺のヨガ・キャンプ等)・toB は将来言語化。

## 3階層の関係

時系列で連動する 3 つの独立サイクル:

```
[年次]   ┌─ (A) 年間→3ヶ月→月次の企画反映   3ヶ月先までの開催が確定
         │
[月次]   ├─ (B) 当月の流れ(シフト中心)      翌々月のスタッフ稼働が確定
         │
[開催毎] └─ (C) プログラム実施フロー          各回の現場運用
```

- (A) の決定が (B) の前提になる(月次カレンダーがあって初めてシフトが組める)
- (B) の決定が (C) の前提になる(現場責任者・フォトグラファーが確定して初めてプログラム準備が動く)

## 一覧

| ファイル | 何を扱う |
|---|---|
| [[annual-quarterly-planning]] | (A) 年間カレンダー策定 → 3ヶ月単位の月次反映 → 企画会議 → STORES 反映 |
| [[monthly-cycle]] | (B) 月初1日のシフトアンケート → 10日確定 → LINEグループ作成 → 月末まとめ |
| [[program-execution]] | (C) 企画MTG → 準備 → 体験案内 → 天気判断 → 実行 → お礼 → 振り返り → 写真共有 |

## 主な登場人物(役割語彙)

ワークフロー内で出てくる役割名と、それを担う staff:

| 役割 | 担い手 | 備考 |
|---|---|---|
| **企画担当者** | 運営4名 + [[junki-iida]] | 企画会議で各プログラムに割り振り。学部固定ではない |
| **現場責任者** | 運営4名のいずれか | 当該開催のオペレーション責任。学部固定ではない |
| **フォトグラファー** | `role: 写真` 5名のいずれか | 月次シフトで決定 |
| **スタッフ(現場)** | `role: フィールドスタッフ` を中心に | プログラム毎に LINE グループを作って連絡 |

運営4名 = [[akira-tsukakoshi]] / [[yuji-wada]] / [[shotaro-shimura]] / [[kei-suzuki]]

## 外部システム接続

| システム | 用途 |
|---|---|
| Google Sheet [年間カレンダー](https://docs.google.com/spreadsheets/d/14JuhBGiS2IUiv1F89bCBFEppXeF9paflL6Ll1gxrZGM/) | (A) 年間活動カレンダー(年始策定) |
| Google Sheet [月次カレンダー](https://docs.google.com/spreadsheets/d/1_RMAQuSb3eWV30WGQ_gsJI5M6Ll1WHvbM4ifkGDuNkM/) | (A) 月次カレンダー(3ヶ月先までの企画詳細) |
| STORES予約 | (A)(C) 企画公開・体験参加者管理・写真アルバム配布 |
| Notion [フィールドレポート](https://www.notion.so/5dab98a40ae443849e3804c0b431abe2) | (C) 振り返りレポート DB(2026-05-23 MCP 開放・スキーマ取込済) |
| Google Photo | (C) 写真アルバム(フォトグラファー → STORES経由で参加者へ) |
| LINE | (B)(C) スタッフ全体グループ・プログラム毎グループ・参加者個別 |

## 関連 SKILL(HMC 由来)

- [`shift_manager`](../../../../harappa-cockpit/.agent/skills/shift_manager/SKILL.md) — (B) 月初1日 / 10日 / 月末のシフトタスクが定義済み。HMG で再実装する際の原型

## 関連事業

- [[parent-child]] — おやこ学部(月3回)
- [[kids]] — こども学部(月1-2回)
- [[adult]] — おとな学部(月2回)
