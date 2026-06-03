## ADR: garden-gaku-co 統合方針(対話層の Garden 単一化)

日付: 2026-05-31
セッション: 22
ステータス: 採用(設計確定 / 段階移行)。**※2026-06-03 訂正**: 本 ADR §2 の「gaku-co5.0 = 撤退対象 / リポジトリ凍結」は誤解を招く表現だったため訂正。gaku-co5.0 は**撤退(消滅)ではなく「社外専用デプロイへ痩せて生存」**(デジタル原っぱ大学 / AIBOU LAB を担当・Garden とエアギャップ)。社内機能のみが garden-gaku-co に移る。正本は [2026-05-28 決定4](2026-05-28-garden-gaku-co-interaction-layer.md) + [2026-06-03 ベンダー中立対話層 ADR](2026-06-03-vendor-neutral-interaction-layer.md)。

## 文脈

S20 〜 S21 の議論で、Garden の対話層に関する以下が見えてきた:

1. **二つの「ガクコ」が並存している**
   - **gaku-co5.0**(VPS、`bot.harappa.monster`)— LINE Messaging API 接続 + staff グループ強制承認制 + `/api/send` `/api/approve/{id}` 等の公開 API + memory(scope 別)+ aibou 機能
   - **garden/services/garden-gaku-co/**(Garden 内)— Discord ベース対話 bot + 朝の口火(morning_greet)+ 夜の振り返り(night_cheer)+ 喋るガクコ(常駐 bot)+ send_pending.py(post_approval ディスパッチャ)
2. **両者の命名が紛らわしい**(同じ「ガクコ」、Garden 側は名前で gaku-co5.0 と区別がつかない)
3. **シフト系の dummy 運用合意(S22)** — 庭師から「gaku-co5.0 と garden-gaku-co が短い期間に変更になると混乱するので、garden-gaku-co に統一されてからリリースする」と方針提示
4. **理想形**(庭師):「チャンネルは私用に Discord、スタッフ用に LINE と切り替えるが、その裏側は Garden で統合されていることを理想としている」

## 決定

### 1. 統合ゴール像 — 入口/出口は別、中身は単一

| 層 | Discord(ガクチョ私用) | LINE(スタッフ用) |
|---|---|---|
| **入口** | Discord bot(garden-gaku-co) | LINE Messaging API webhook |
| **中身**(統合)| 同じ persona(草木 / 木の精)+ 同じ memory(scope 分離)+ 同じ soil 参照 + 同じ plot picker + 同じ種ディスパッチ |
| **出口** | Discord bot 送信 | LINE Messaging API 送信 |

中身が単一であることが統合の本質。チャネル固有の機能(LINE strict approve / Discord reaction 等)は出入口層のみに局在化させ、対話エージェント本体には流入させない。

### 2. 命名の整理

- **garden-gaku-co を統合後の本流名** として確定
- gaku-co5.0 は「旧 LINE bot(撤退対象)」と位置づける
- 統合完了後、gaku-co5.0 リポジトリは凍結し、必要な部分は Garden 配下に取り込み済みとする
- 当面の混乱回避のため、本 ADR を以後の議論で参照する

### 3. 統合スコープ(gaku-co5.0 → Garden に取り込む対象)

| gaku-co5.0 の機能 | Garden 取り込み | 配置先 / 備考 |
|---|---|---|
| LINE Messaging API 接続(webhook 受信 + 送信) | ✅ 取り込み | `garden/services/garden-gaku-co/line/`(新設予定) |
| staff グループ強制承認制 | ✅ 取り込み | LINE 送信層に局在化、garden-gaku-co 本体ロジックには漏らさない |
| `/api/send` `/api/approve/{id}` 等の公開 API | △ 局所利用 | Garden 内部から呼び出す形式に整理、外部公開は撤退 |
| memory(scope 別 RAW + WIKI + 夜間バッチ) | ✅ 取り込み(soil 最適化付き) | 別 ADR [2026-05-31-memory-three-layer-and-soil-routing](2026-05-31-memory-three-layer-and-soil-routing.md) |
| aibou(相棒)機能 | △ 当面温存、後判断 | チーム公開時に再評価 |

### 4. 移行順序(リスクの低い順 — Stage)

| Stage | 内容 | 並行する別 ADR Stage |
|---|---|---|
| **0**(暫定)| send_pending.py に dummy ディスパッチモードを追加 — LINE 配信を Discord master に流す。**6/1 月初配信は dummy 運用** | — |
| **1** | memory システム移植(RAW logging 開始)— Discord 対話を捨てない | memory ADR Stage A |
| **2** | memory + soil 振り分け規約 ADR 化 + 菌糸 Mode 1 最小実装 | memory ADR Stage A.5 |
| **3** | 夜間バッチ起動(EXTRACT + CONSOLIDATE)+ bot context への master memory ロード | memory ADR Stage B + C |
| **4** | LINE webhook 受信を garden-gaku-co に追加(送信は当面 gaku-co5.0 経由のまま、二重化) | — |
| **5** | LINE 送信を garden-gaku-co に取り込み(`send.py` を Discord + LINE 両対応化) | — |
| **6** | gaku-co5.0 シャットオフ + send_pending.py を Garden 直結に切替 | — |
| **7** | チーム公開準備(下位 scope RAW + 投影ビュー + マスター透視権) | memory ADR Stage D |

Stage 0 = 5/31 〜 6/1 で運用、Stage 1〜3 = 短期、Stage 4〜6 = 中期、Stage 7 = 長期(チーム公開タイミング)。

### 5. dummy 運用の境界(Stage 0)

- 影響対象: `from_seed ∈ DISPATCH_LINE_SEND` かつ `status: approved` のみ
- 影響を受けないもの: `status: test`(personal LINE / ガクチョ自分宛)、shell 種(集計実行など)
- 制御: `.env` の `SEND_PENDING_DEFAULT_MODE=dummy` + board frontmatter `dispatch_mode: dummy|production` 上書き
- dummy 時の挙動: `/api/send` を呼ばず、本文全文を Discord master チャネルに「📨 dummy: 本配信用本文(手動コピー)」ヘッダ付きで投稿 → ガクチョが手動で LINE staff グループにコピー → board は processed/ へ移動

### 6. 統合中の API 公開撤退方針

gaku-co5.0 `/api/send` は現状 **認証なし**(S21 で発見、`bot.harappa.monster/api/send` を知れば第三者でも staff LINE 投稿可)。Stage 5 で送信が garden-gaku-co に移った後、外部 HTTP API は **公開しない**(Garden 内部呼び出しのみ)。Stage 6 完了時点で `bot.harappa.monster/api/send` の外部到達性を遮断する。

## 影響

- **当面**: 6/1 月初配信は dummy 経路で動く(LINE 接続層に変更入らず、リスク最小)
- **短期**: memory 移植が動くと、Discord 対話の判断ログが捨てられなくなる。ガクチョの「同じ話を何度もしなくて済む」体験が立ち上がる
- **中期**: LINE 受信が Garden に来ると、スタッフ発話の RAW + EXTRACT が soil に流入し始める。3者間会話(ガクコ宛でない雑談)も「整理されて保持」される
- **長期**: 公開チャネル(LINE)経由の漏洩リスクが投影ビューで防御される

## 関連

- 前提: [2026-05-30 菌糸(Mycelium) の役割と soil 参照規約](2026-05-30-mycelium-and-soil-reference.md)
- 並行: [2026-05-31 記憶の三層分離 + soil 振り分け規約](2026-05-31-memory-three-layer-and-soil-routing.md)
- セッション: [2026-05-31 セッション22](../sessions/2026-05-31-session22.md)
