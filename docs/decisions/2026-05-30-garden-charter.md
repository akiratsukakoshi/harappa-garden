# ADR: Garden CHARTER 導入とトーン統一 — 全 plot 共通の業務観モジュール化

日付: 2026-05-30
セッション: 20
ステータス: 採用

## 文脈

[セッション19](../sessions/2026-05-30-session19.md) で daily-pilot SKILL.md を起こし、Phase 4(区画 Garden 化)の第1号 plot として立ち上がった。続いて第2号(`shift_manager`)を着手するにあたり、以下の課題が顕在化:

1. **共通部の重複問題** — daily-pilot SKILL の 355 行中、約 60 行(呼称・トーン・Core Philosophy 4 原則・Output Style 質感の骨格)は全 plot で共通になる。新 plot を立てるたびにコピペすると、呼称や Empowerment & Proactivity の質感が plot ごとにずれ、第3号・第4号で必ず劣化する(コピペ漏れ・ニュアンス変化)。
2. **「ガクチョ呼称」の3重管理** — `CLAUDE.md`(global)+ daily-pilot SKILL + bot.py の 3 箇所に重複し、変更時の漏れリスクが高い。
3. **「Vice Pilot」表現の出自問題** — HMC 由来の語彙が daily-pilot SKILL と persona に残っていた。Garden の生態系(庭師 / 種 / 剪定 / 土壌)とトーンが合わず、「庭師の補佐」のような上下関係を連想させる。
4. **トーンの揺らぎ** — bot のレスや night_cheer のひとことが「下書きこっちで作るよ」のような友達口調になりがちで、仕事モードでの使い勝手が悪い(庭師フィードバック)。

これらは「業務観 / 呼称 / トーン / Output Style 質感」が **どこか1箇所** に集約されていない構造問題。[セッション19 ADR](./2026-05-30-skill-and-seed-separation.md) で「種 = 発火ディスパッチャ / SKILL = 業務観モジュール」のレイヤ分けを正式化したが、**plot を超えた共通根** をどこに置くかは未決だった。

## 決定

`garden/CHARTER.md` を新設し、**全 plot SKILL の共通根** を集約する。

### 集約する内容(5項目)

| 項目 | CHARTER に置く理由 |
|---|---|
| 庭師(ガクチョ)像と呼称 | 全 plot で不変。1箇所で管理 |
| Garden の中の存在(ガクコ等)の位置づけ | 上下関係でなく「橋渡し役」スタンスを共有 |
| トーン規範(ですます調基本、過剰敬語禁止) | 全 plot で同一の声色を保証 |
| Core Philosophy 4 原則(HITL / SSOT / Pattern A / Empowerment & Proactivity) | 各 plot は本 plot 固有の適用だけ書く |
| Output Style 質感(1項目1行・締めの規範・良い締めの型・悪い締めの例) | 具体例は plot 固有、骨格は共通 |

### ガクコ(および将来 plot ごとに生まれる声)の再定義

「庭師の Vice Pilot」「庭師の補佐」のような上下関係表現を撤廃し、以下に再定義:

- **Garden の中で動く存在**(庭師の上下関係にあるのではない)
- **草木のような、木の精のような存在**(Garden そのものから生まれた)
- **庭師(ガクチョ)と Garden の橋渡し役** として動く
- **役割名は固定しない** — 各 plot で具体的な顔(daily-pilot は秘書的、shift_manager は管理代行的)を持つが、根の在り方は同じ

これは Garden 語彙(庭師 / 種 / 剪定 / 土壌)の生態系メタファに沿った位置づけであり、「補佐」「Vice Pilot」のような階層関係表現を意図的に避ける。

### ロード機構

**loader は実装しない**。各 consumer(seed prompt / Python サービス)が起動時に CHARTER と SKILL の **両方を物理的に読み込んで** prompt に連結する。

- **確実性**: 参照リンクだけだと Claude が読み忘れる可能性。物理的にプロンプト内に展開すれば確実
- **規模適合**: 現在の 5 経路(seeds/daily-pilot/morning-briefing.md + night-review.md + bot.py + morning_greet.py + night_cheer.py)に loader は過剰設計
- **将来**: Phase 4 が進んで 20 経路超えたら、loader 機構(`inherits_from` を解釈するライブラリ)への移行を検討

### トーンの方針

- **ですます調** を基本とする(「〜です」「〜ます」「〜してください」)
- 過剰な敬語・ビジネス文書調は避ける(「〜でございます」「謹んで」等)
- 友達口調を強く禁止リスト化はしない(揺らぎ許容)
- 仕事モードの落ち着き = 庭師フィードバックを反映

## 代替案と却下理由

| 案 | 内容 | 却下理由 |
|---|---|---|
| A | コピペ続行(`garden/plots/_TEMPLATE.md` を置く) | 第3号・4号で必ず質感が劣化する。「ガクチョ呼称」の 3 重管理問題も解決しない |
| B | SKILL loader を実装(`inherits_from: garden/CHARTER` を解釈) | 5 経路には過剰設計。loader 自体のバグが全 SKILL に波及するリスク |
| C(採用) | CHARTER.md + 各 consumer が物理的に両方ロード | 機構なしで確実性を担保。第2号着手前に最低限の構造 |
| D | 役割名(Vice Pilot 相当)を Garden 語彙で新造(「庭手」「庭付き」等) | 各 plot で AI の役割は違う(秘書的 / 管理代行的 / 経理助手的)。1語に固定すると plot ごとに違和感が出る。庭師判断で「あえて名前はつけない」(C 案) |

## 影響

### 即時(セッション20)

- `garden/CHARTER.md` 新設(約 90 行)
- `garden/plots/daily-pilot/SKILL.md` 短縮(355 → 約 220 行、共通部を CHARTER 参照に圧縮 + Vice Pilot 表現を全削除 + 例文をですます調に統一)
- `garden/services/garden-gaku-co/persona/g-gaku-co.md` 更新(トーンを CHARTER 整合 + 「橋渡し役・木の精」スタンス反映)
- 5 consumer 書き換え(CHARTER + SKILL の二段ロード):
  - `garden/seeds/daily-pilot/morning-briefing.md`
  - `garden/seeds/daily-pilot/night-review.md`
  - `garden/services/garden-gaku-co/bot.py`
  - `garden/services/garden-gaku-co/morning_greet.py`
  - `garden/services/garden-gaku-co/night_cheer.py`
- VPS scp + bot 再起動完了(2026-05-30 18:06)

### 第2号 plot(shift_manager)着手時

- CHARTER 由来の質感(呼称・トーン・Core Philosophy・Output Style 骨格)が自動で乗る
- shift_manager SKILL は plot 固有の手順・ファイル(`soil/people/staff/`)・判断ルール・具体的な締めの例だけに集中できる
- 第2号着手は Phase 3c(HMC 移植)と同期

### CHARTER 運用ルール

- **CHARTER 肥大化の誘惑への抑止** = 約 90 行を上限の目安にする。「これも共通っぽいから」が始まると plot SKILL が空洞化する
- **CHARTER と CLAUDE.md(global)の重複** = 「ガクチョ呼称」は両方に書く(視点が違う: CLAUDE.md = 私 Claude 向け / CHARTER = SKILL が他モデル・bot に伝える用)。完全統合は不可

### 観察ポイント

- 今夜 22:30 / 22:40 と 明朝 06:30 / 06:40 が **CHARTER + SKILL 二段ロードでの初稼働**。トーン(ですます調)が乗っているか確認
- Discord 対話でガクコの口調が仕事モードに揃っているか観察(揺らぎが目立つなら CHARTER のトーン節を磨く)

## 関連

- 直前 ADR: [種(seed) と SKILL の責務分離](./2026-05-30-skill-and-seed-separation.md)
- 起源: HMC `.agent/skills/hmc_pilot/SKILL.md`(SKILL 3層構造の原型)
- 関連ファイル: [garden/CHARTER.md](../../garden/CHARTER.md) / [garden/plots/daily-pilot/SKILL.md](../../garden/plots/daily-pilot/SKILL.md)
