# ADR: soil の正本と 3 箇所配置の同期ルール

日付: 2026-06-02
セッション: 26
ステータス: 採用(運用開始)

## 文脈

[S23(2026-05-31)で soil を vault と VPS garden-mirror に配置](../sessions/2026-05-31-session23.md)した時点で、soil は **3 箇所** に存在する状態になった:

| 場所 | 経路 | 想定された書き手 |
|---|---|---|
| repo `garden/soil/` | git 管理 | Claude(セッション中) |
| vault `gakuchovault/garden/soil/` | Dropbox + LiveSync | ガクチョ(Obsidian)+ Claude |
| VPS `garden-mirror/garden/soil/` | LiveSync(CouchDB ↔ MD) | 菌糸(VPS launcher) |

S23 では「正本関係の明文化」を次セッション宿題として残した。

## 現状調査(2026-06-02 時点)

- repo / vault / VPS の 3 箇所の soil は **内容完全一致**(`diff -r` で差分ゼロ、172 行の `log.md` も同一)
- vault ↔ VPS は LiveSync で双方向同期(秒オーダー)
- repo は孤立(vault / VPS と繋ぐ経路なし、S23 の初期配置は手動 cp / scp のみ)
- 菌糸 `index-refresh` は VPS で 6/1, 6/2 の 03:00 に発火しているが、`log.md` への追記は LLM 判断で skip(直前の bootstrap が全件カバー済みのため)→ 偶然にも分岐が発生していない

## 想定 vs 実態の検証

S20 〜 S23 の議論では「ガクチョが Obsidian で soil を直接編集する」シーンを暗黙の前提にしていたが、本セッション(S26)でガクチョと再確認した結果:

- ガクチョが Obsidian 単独で soil を編集することは **ほぼない**(振り返ると S1 〜 S24 の soil 編集は全て Claude セッション経由)
- ガクチョ自身も「直接触らない運用のほうがすっきりする」と明言
- 「将来ガクコ経由で書きたくなるケース」は想定範囲内(ガクコは VPS 上で動くので、書き手としては菌糸と同じ扱い)

→ **書き手は実質 2 つ(Claude セッション + VPS 上のエージェント群)**。vault は **読み取り専用ビュー** として位置づけ直す。

## 決定

### 1. soil の正本は「ファイルの層」によって分ける

| 層 | 該当ファイル | 主たる書き手 | 正本 |
|---|---|---|---|
| **構造ファイル** | `people/` `business/` `clients/` `projects/` `workflows/` `events/` `meetings/` `concepts/` 配下のエンティティページ + README | Claude(セッション中) | **repo** |
| **菌糸産ログ** | `log.md` の `index-refresh` / `index-bootstrap` 等の自動追記、`index.md` の差分更新 | 菌糸(VPS launcher) | **VPS** |

**両方の書き手が両方のファイルを触る** という構造上の重複(例: `log.md` には Claude も菌糸も書く)は、時間的 sequencing で吸収する(下記 §4)。

### 2. vault は読み取り専用ビュー

- Obsidian は **リンク辿り・バックリンク表示・全文検索** の閲覧専用ツールとして使う
- ガクチョが Obsidian で soil を編集することは **想定しない**(機能的にできるが、推奨しない)
- 万が一 vault で直接編集が起きた場合は、**LiveSync で VPS に反映** → **次回 `pull-from-vps` で repo に取り込まれる** → そこで Claude が気づいて反映 / 棄却を判断する(repo が事後的に勝つ)

### 3. 同期スクリプトは 2 本(双方向ではない)

`garden/services/soil-sync/` に 2 本の単方向 rsync スクリプトを置く:

- **`pull-from-vps.sh`** — VPS → repo(菌糸が書いたぶんを取り込む)
- **`push-to-vps.sh`** — repo → VPS(Claude が書いたぶんを反映)

vault は LiveSync で自動同期されるため、スクリプトの管轄外。

初版は `--delete` なしで運用 1〜2 週観察し、誤削除リスクが顕在化しないことを確認してから `--delete` 化を検討する。

### 4. セッションプロトコル(時間的 sequencing で競合回避)

| タイミング | アクション | 目的 |
|---|---|---|
| **セッション開始時** | `pull-from-vps.sh` | 菌糸が書いた最新エントリを repo に取り込む |
| **セッション中** | Claude が repo で自由編集 | git 管理下、commit 可 |
| **セッション終了時 / commit 前** | `push-to-vps.sh` | Claude が書いたぶんを VPS に反映 |
| **菌糸 cron(03:00)** | VPS の `log.md` / `index.md` を更新 | セッション時間帯と被らない |

菌糸の cron は深夜固定、Claude セッションは日中が中心なので時間帯が重ならない。同時刻に Claude セッションが回る場合は、ガクチョ判断で手動 pull/push を挟む(運用 1〜2 週で問題顕在化するか観察)。

### 5. 将来のガクコ経由編集の扱い

ガクコ(bot)は VPS 上で動くため、書き手としては **菌糸と同じ立場**:

- ガクコが soil を編集 → VPS garden-mirror に書く → 次回 `pull-from-vps` で repo に取り込まれる
- 書く先のルール:構造ファイルへの編集も VPS 起点で行ってよいが、`pull-from-vps` で repo に流れるまで「正本未反映」状態になることを許容する
- 緊急に repo 反映が必要なら Claude セッションで `pull-from-vps` を即実行

### 6. 初回ベースライン

本 ADR 採用時点で 3 箇所の soil は内容完全一致。**現状を初回ベースライン** として確定し、以降は本 ADR のルールに従って同期する。

## 代替案と却下理由

| 案 | 内容 | 却下理由 |
|---|---|---|
| **案 A: vault = 正本** | ガクチョが Obsidian で書く前提 | ガクチョ自身が「直接触らない」と表明、実態と乖離 |
| **案 B: repo 単一正本(双方向 sync デーモン)** | mirror-daemon を拡張して 3 箇所完全双方向 | 競合解決ロジック複雑、実装重い、菌糸が書く頻度では過剰 |
| **案 D: 双方向 sync デーモン** | 常時 daemon で全箇所同期 | 同上、scope の割に重い |

採用案(層別正本 + 単方向 rsync 2 本)は最小実装で書き手と正本が 1:1 対応するため選択。

## 影響

### 即時(本セッション)

- `garden/services/soil-sync/{pull-from-vps.sh, push-to-vps.sh, README.md}` 新設
- `garden/soil/README.md` に「正本と同期ルール」節を追加
- `garden/MAP.md` の soil 関連行を更新、宿題「soil 正本関係明文化」を済みマーク
- 本 ADR
- Claude auto memory に「セッション開始/終了に pull/push を実行」を保存

### 短期(1〜2 週運用観察)

- 偶発的な分岐が発生しないか観察
- 菌糸 `log.md` 追記頻度の傾向把握
- `--delete` 採用可否判断
- ガクコ稼働後の書き手追加に伴うルール再評価

### 長期

- ガクコの実稼働で「書き手 3 つ(Claude + 菌糸 + ガクコ)× 2 正本(repo + VPS)」の運用が始まる
- 投影ビュー(memory ADR §4)実装時、soil 経由のスタッフ機微情報フィルタリングに本ルールが前提となる

## 関連

- 前提 ADR(S20): [菌糸(Mycelium) の役割と soil 参照規約](2026-05-30-mycelium-and-soil-reference.md)
- 前提 ADR(S22): [記憶の三層分離 + soil 振り分け規約](2026-05-31-memory-three-layer-and-soil-routing.md)
- 前提 ADR(S13): [gakuchovault 内の Garden フォルダ配置](2026-05-27-vault-folder-layout.md) — vault 配置の初出
- セッション(S23): [菌糸 Stage 1 active + soil vault 化](../sessions/2026-05-31-session23.md) — 3 箇所配置の発端
- 関連ファイル: [garden/soil/README.md](../../garden/soil/README.md) / [garden/services/soil-sync/](../../garden/services/soil-sync/)
