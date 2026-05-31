# 土壌の地図 (index)

> 土壌の全エントリの意味的サマリ。菌糸(Mode 3)が ingest と編集のたびに更新する。
> 全件列挙はせず「カテゴリ・件数・主要リンク」に絞る(Karpathy LLM Wiki 哲学)。細部は各カテゴリ README または `[[link]]` 経由で都度 Read。

最終更新: 2026-05-31(セッション23 菌糸 Stage 1 初回 full scan)

## カテゴリ一覧

| カテゴリ | 状態 | 概要 |
|---|---|---|
| [people/staff/](people/staff/) | 🌳 **29名 active** | 経営1 / 業務委託13 / 外部スタッフ11 / アルバイト4。詳細は staff README |
| [people/clients/](people/clients/) | ⬜ 未着手 | クライアント企業の担当者(個人) |
| [people/partners/](people/partners/) | ⬜ 未着手 | パートナー窓口 |
| [business/](business/) | 🌱 **21ファイル骨格** | toC 学部別含む18 + toB 5 + communication 1。中身は埋め待ち多数 |
| [workflows/](workflows/) | 🌱 **4本 active** | annual-quarterly-planning / monthly-cycle / daily-cycle / program-execution |
| [concepts/](concepts/) | 🌱 1件 | [[kodomon]](外部システム、放サボ勤怠) |
| [clients/](clients/) | ⬜ 未着手 | クライアント企業本体 |
| [projects/](projects/) | ⬜ 未着手 | 進行中プロジェクト |
| [events/](events/) | ⬜ 未着手 | 個別イベント |
| [meetings/](meetings/) | ⬜ 未着手 | 議事録インデックス(本体は Plaud/Drive) |

---

## people/staff/ — スタッフ(29名 active)

詳細一覧と全 29 名の表は [people/staff/README.md](people/staff/README.md) を参照。本 index は意味的集計のみ:

### contract 集計(契約 × 1軸排他)

| contract | 人数 | 代表的なメンバー |
|---|---:|---|
| 経営 | 1 | [[akira-tsukakoshi]](ガクチョ) |
| 業務委託 | 13 | 運営4([[yuji-wada]] / [[shotaro-shimura]] / [[kei-suzuki]] / [[junki-iida]] 仮) + 写真・フィールド系 9 |
| 外部スタッフ | 11 | フィールドスタッフ全員(主に逗子・未指定地域) |
| アルバイト | 4 | フィールドスタッフ全員(逗子) |

### role 集計(役割 × 複数可)

| role | 人数 | 内訳 |
|---|---:|---|
| 運営 | 4 | [[akira-tsukakoshi]] / [[yuji-wada]] / [[shotaro-shimura]] / [[kei-suzuki]] |
| フィールドスタッフ | 21 | アルバイト4 + 外部スタッフ11 + 業務委託6(城家・中辻・前田・守田・大吉美穂・飯田) |
| 写真 | 5 | [[keiko-uchiyama]] / [[miho-oyoshi]] / [[kasumi-tachibana]] / [[misa-mine]] / [[kosaku-yoshida]](大吉美穂は写真+フィールド兼任) |
| 調理 | 0 | 未割り当て |

### area 集計(拠点)

| area | 人数 | 備考 |
|---|---:|---|
| 全社 | 1 | [[akira-tsukakoshi]] |
| 逗子 | 16 | 主力拠点 |
| 千葉 | 4 | フィールド+写真 |
| 大阪 | 2 | [[naoko-shiroie]] / [[mie-morite]] |
| 未指定 | 6 | 主に外部スタッフ |

### 集計外メモ

- alumni 候補 48名 → `[_review-2026-05-22-master-data-candidates.md](people/staff/_review-2026-05-22-master-data-candidates.md)` で保留(ガクチョ判定「無視で OK」)
- 退任 7名 → `[_alumni.md](people/staff/_alumni.md)` に集約
- 同期上の注意: [[kei-suzuki]] / [[yuji-wada]] は freee_id 統合あり、[[misa-mine]] は Freee 漢字違い(三根美沙)

---

## business/ — 事業構造(21ファイル骨格)

詳細は [business/README.md](business/README.md)。frontmatter のみ充実、中身は塚越さん埋め待ちが多い。

### toC(toC=対個人事業、12ファイル)

| 配下 | 主要サービス | linked_staff |
|---|---|---|
| [harappa-university/](business/toC/harappa-university/) | [[parent-child]](月3) / [[kids]](月1-2) / [[adult]](月2) | yuji / shotaro / kei |
| (直下) | [[ore-no-yoga]] / [[saboru-zushi]] / [[events]] / [[harappa-osaka]] | kei / shotaro |
| [ai/](business/toC/ai/) | [[aibou-gym]] / [[digital-harappa]] | (未) |

### toB(toB=対法人事業、5ファイル)

| サービス | linked |
|---|---|
| [[training]] | yuji |
| [[community-management]] | (未) |
| [[miura-forest]] | clients: [[京急電鉄]] |
| [[event-production]] | (未) |
| [[other-appearances]] | (未) |

### communication(1ファイル)

| サービス | cadence |
|---|---|
| [[newsletter]] | weekly(linked: akira) |

---

## workflows/ — 業務フロー(4本 active)

| ファイル | cycle | scope |
|---|---|---|
| [[annual-quarterly-planning]] | 年次 + 3ヶ月単位 | toC 原っぱ大学 おやこ/こども/おとな |
| [[monthly-cycle]] | 月次 | toC 原っぱ大学(月末/月初1日/月初10日/適宜)+ kodomon 連携 |
| [[daily-cycle]] | 日次 | 個人(ガクチョ)の業務管理(daily-pilot 区画の業務正本) |
| [[program-execution]] | プログラム開催毎 | toC 原っぱ大学 + Notion フィールドレポート連携 |

A 案テンプレ(目的 / 現状の方法 / 改善余地)で記述。monthly-cycle と daily-cycle は詳細化済、annual-quarterly-planning と program-execution は **書き直し残り**(MAP.md の宿題)。

---

## concepts/ — 概念ページ

| エントリ | 種別 |
|---|---|
| [[kodomon]] | 外部システム(放サボ勤怠管理、API/MCP 未調査) |

---

## 空カテゴリの位置づけ(Phase 1 残)

- **clients/** — クライアント企業本体(Phase 1 残)
- **projects/** — 進行中プロジェクト
- **events/** — 個別イベント
- **meetings/** — 議事録インデックス(Plaud 連携待ち)
- **people/clients/** / **people/partners/** — 個人レベルの担当者・窓口

---

## 関連

- 哲学: [README.md](README.md)(Karpathy LLM Wiki 方式)
- 編集ログ: [log.md](log.md)(全 ingest / edit の追記専用ログ)
- 維持役: [garden/mycelium/](../mycelium/)(菌糸 Mode 3 が本 index を維持)
