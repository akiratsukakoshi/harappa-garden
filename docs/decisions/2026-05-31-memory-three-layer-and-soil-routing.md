## ADR: 記憶の三層分離 + soil 振り分け規約 + Stage 段階

日付: 2026-05-31
セッション: 22
ステータス: 採用(設計確定 / 実装は Stage 別)

## 文脈

S20 §5「永続記憶 — gaku-co5.0 を移植」で「ガクチョの要件と 90% 一致、移植する」と整理したが、S22 で再検討した結果、**構造軸の本質的な差** を見落としていた:

| | gaku-co5.0 memory | Garden soil |
|---|---|---|
| 分類軸 | **scope(チャネル)軸** — MASTER / LINE_STAFF / discord_* / aibou_* | **意味(対象)軸** — people / business / events / workflows / clients |
| 起点 | 対話(誰と話したか) | 業務対象(何についての情報か) |
| 維持役 | 夜間バッチ(processor.py) | 菌糸(S20 で新設、未実装) |

そのまま移植すると、memory(scope 軸)と soil(意味軸)が **別の世界として並存** してしまう。庭師の意図は逆で:

- 対話で出てきた事実が **意味に応じて soil に流入** する
- ただし **チャネル間漏洩は厳密に防ぐ**(マスターのやり取りが staff_all に流れてはいけない)
- ガクコ宛でない 3者間会話(スタッフ同士の雑談・連絡)も **整理して保持** する

加えて、本 ADR と並行する [2026-05-31 garden-gaku-co 統合方針](2026-05-31-garden-gaku-co-unification.md) の「裏側は Garden で統合」というゴールに、記憶層の設計が一体で組み込まれる必要がある。

## 決定

### 1. 情報を三層に分けて配置軸を変える

| 層 | 入れる対象 | 分類軸 | 漏洩制御 |
|---|---|---|---|
| **RAW** | 対話の生ログ(bot 宛 / 非宛問わず全発話) | **scope(チャネル)軸** | scope 間で **絶対に交わらない**(物理ディレクトリ分離 + 読み取り権限分離) |
| **SOIL** | 「事実」だけ(誰・いつ・何・どう) | **意味(対象)軸** | master のみ完全読み取り、下位 scope は **投影ビュー** 経由で限定的に読む(Stage D で実装) |
| **MEMORY WIKI** | 「判断・評価・意図・ニュアンス」 | **scope(チャネル)軸** | scope 間で **絶対に交わらない**。master memory は master bot のみ、staff memory は staff bot のみ |

**ポイント: soil には事実しか書かない**。判断ログ・人物評価・戦略意図は scope ローカルの memory wiki に隔離する。

### 2. 振り分け規約(菌糸 Mode 1 Ingest の責務)

RAW の各発話を **菌糸 Mode 1 Ingest** が読み、以下に振り分ける:

| 抽出内容 | 出力先 | 例 |
|---|---|---|
| **事実**(誰・いつ・何・どう、検証可能) | **soil**(該当する対象軸) | 「慶ちゃん来週シフト入れない」→ `soil/people/staff/鈴木慶.md`、「6/15 イベントある」→ `soil/events/` |
| **判断・評価・意図**(主観的、主体依存) | **scope memory wiki**(該当 scope ローカル) | 「慶ちゃんの来月の役割を見直したい」→ `garden/memory/master/wiki/staff_assignment.md` |
| **決定事項**(具体的に動くもの) | **scope memory wiki** + **soil**(意味的に該当する対象があれば反映) | 「6/15 イベント、集合は 7 時に駅前で確定」→ master memory + `soil/events/{event}.md` |
| **予定**(未来の事実) | **soil**(events / projects)+ scope memory(注記レベル) | 同上 |
| **グレーな約束 / 文脈ノイズ** | 捨てる | S20 §5 で庭師方針「グレーな約束は拾わない、明示的タスク化が境界」 |

**抽出強度の優先順位**(S20 §5 庭師要件):**判断ログ > 背景 > 対話文脈**。

### 3. 3者間会話(ガクコ宛でない発話)の扱い

LINE staff グループでスタッフ同士の会話・連絡が常時発生する。これも記憶対象に含める:

- **RAW logging**: bot 宛 / 非宛区別なく、`scope=line_staff` の RAW に全発話を保持
- **EXTRACT**(夜間バッチ): bot 宛 / 非宛問わず、事実 / 決定 / 予定を抜き出す
- **出力先振り分け**:
  - 公開事実(集合場所・日付・連絡網)→ **soil**(events / projects 等、意味軸)
  - 進行中の運営感覚・苦労・空気感 → **`memory/line_staff/wiki/{topic}.md`**(scope ローカル、主題別章立て)
- **bot 応答ポリシー**: 発話には反応せず**傍聴のみ**、**@ガクコ明示時のみ介入**(雑談に過剰反応しない)
- **整理粒度**: 時系列議事録ではなく、**主題別章立て**(`memory/line_staff/wiki/{topic}.md` 形式 + `memory/line_staff/index.md` で主題一覧)。主題は EXTRACT 時に LLM が判定(例: 「沖縄キャンプ運営」「6月シフト混乱」など)

### 4. 漏洩防御 — 物理境界 + 投影ビュー

| 層 | master bot | staff bot(将来) | aibou bot(将来、個人別) |
|---|---|---|---|
| `memory/master/` | 読み書き | **不可視** | **不可視** |
| `memory/line_staff/` | 読み取り(マスター透視権、Stage D) | 読み書き | **不可視** |
| `memory/line_aibou_{id}/` | 読み取り(マスター透視権、Stage D) | **不可視** | 読み書き(自分のみ) |
| `soil/` | 完全読み取り | 投影ビュー経由(`garden/views/line_staff/`) | 投影ビュー経由(`garden/views/line_aibou_{id}/`) |

**投影ビュー**(Stage D で実装):
- soil 本体から、scope に応じた「公開可能ビュー」を **菌糸が生成・配布**
- ファイル単位ではなく、フィールド単位で機微情報を除外(visibility frontmatter ベース)
- staff bot は `garden/views/line_staff/` 配下のみ読み取り(settings.json の path-scoped allow + bot 起動時 chroot 相当)
- 生成タイミングは soil 更新時(菌糸の責務として後日詳細化)

**Stage A 〜 C(ガクチョ単独運用)期間中は投影ビュー不要** — 唯一の読み手がガクチョ本人なので漏洩リスクがそもそも存在しない。Stage D(LINE 統合 = チーム公開)直前に実装する。

### 5. 配置(ディレクトリレイアウト)

```
garden/
  memory/
    master/                       # Discord ガクチョ私用 scope
      raw/                        # 日次 MD、14日保持
        2026-05-31.md
        2026-06-01.md
        ...
      wiki/                       # 主題別章立て(LLM 抽出 / 統合済み)
        {topic}.md
        ...
      index.md                    # 主題一覧
    line_staff/                   # Stage D で稼働開始
      raw/
      wiki/
      index.md
    line_aibou_{group_id}/        # Stage D で稼働開始(個人別)
      raw/
      wiki/
      index.md
  views/                          # Stage D で稼働開始(投影ビュー)
    line_staff/
      people/staff/...            # 機微情報除外版
      events/...
    line_aibou_{group_id}/
      ...
  mycelium/
    README.md                     # S20 で立ち上げ済
    ingest/                       # Stage A.5 で実装(振り分けロジック)
```

### 6. Stage 段階

| Stage | 内容 | 連動する別 ADR Stage(統合 ADR)|
|---|---|---|
| **A** | `garden/memory/master/raw/` で Discord 対話の RAW logging だけ開始(soil 反映なし、振り分けロジックなし。対話を捨てない仕組みだけ先に) | 統合 Stage 1 |
| **A.5** | 菌糸 Mode 1 Ingest 最小実装(master RAW → soil + master memory wiki への振り分け、本 ADR §2 規約に従う) | 統合 Stage 2 |
| **B** | 夜間バッチ(EXTRACT + CONSOLIDATE、03:00 JST、claude-haiku-4-5)起動 + 14 日経過 RAW 削除 | 統合 Stage 3 |
| **C** | bot 起動時に master index + 最近 RAW を context にロード(真の永続記憶) | 統合 Stage 3 |
| **D** | LINE 統合に伴い、下位 scope RAW 開始 + 投影ビュー生成 + マスター透視権実装 + 3者間会話の EXTRACT | 統合 Stage 4〜7 |

### 7. gaku-co5.0 からの流用方針

[gaku-co5.0 app/memory/](file:///home/tukapontas/gaku-co5.0/app/memory/) の以下は **そのまま流用**:

- 2 段構造(RAW + WIKI)
- 14 日 RAW 保持期間
- 夜間バッチの基本フロー(EXTRACT → CONSOLIDATE → NEW/UPDATE)
- claude-haiku-4-5 採用(コスト)
- SQLite 不採用(MD のみ)
- scope ごとの index.md(LLM Wiki 哲学の中核)

以下は **Garden 用に再設計**:

- **出力先の振り分け**(本 ADR §2)— gaku-co5.0 は scope ローカル WIKI のみ、Garden は soil + scope memory wiki の二系統に振り分ける
- **マスター透視権**(本 ADR §4)— gaku-co5.0 の MASTER は単一 scope 蓄積、Garden の master は下位 scope を読み取れる階層構造
- **3者間会話の主題別章立て**(本 ADR §3)— gaku-co5.0 は時系列ベース、Garden は主題別

## 影響

- **設計の地殻変動**: 「対話 → 記憶 → soil」の流れが一本化される。チャネルを越えても soil は単一(これが統合 ADR の「裏側 Garden 単一化」の実体)
- **菌糸の責務が具体化**: S20 で立てた Mode 1 Ingest の出力先が確定 = 実装可能になる
- **漏洩防御が明文化**: 物理ディレクトリ分離 + 投影ビュー + soil の事実限定 という 3 重防御で「マスターのやり取りが staff_all に流れない」を技術的に保証
- **3者間会話の価値が顕在化**: ガクコ宛でない発話も「整理して保持」される構造になり、運営現場の暗黙知が蓄積される

## 関連

- 前提: [2026-05-30 菌糸(Mycelium) の役割と soil 参照規約](2026-05-30-mycelium-and-soil-reference.md)
- 並行: [2026-05-31 garden-gaku-co 統合方針](2026-05-31-garden-gaku-co-unification.md)
- 流用元: [gaku-co5.0 memory システム](file:///home/tukapontas/gaku-co5.0/app/memory/)
- セッション: [2026-05-31 セッション22](../sessions/2026-05-31-session22.md)
- 関連 Garden 語彙: [docs/garden-vocabulary.md](../garden-vocabulary.md)
