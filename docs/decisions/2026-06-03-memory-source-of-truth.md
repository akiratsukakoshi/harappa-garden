# 2026-06-03 — memory の正本と sync ルール

> セッション 29(2026-06-03)で確定。S26 で soil の正本ルールを片付けた([2026-06-02 ADR](2026-06-02-soil-source-of-truth.md))対称形として、memory 側の正本ルールも明文化する。S26-S28 持ち越し宿題の解消。

## 起点

S22 の三層分離 ADR([2026-05-31](2026-05-31-memory-three-layer-and-soil-routing.md))で memory の論理構造は決まった。S26 で Stage A.5(ingest-raw 種 active 化)が走り出した。これにより wiki/*.md が **VPS で毎晩 03:30 に積み上がる** 構造になった = soil と同じく「VPS で書き込まれる構造ファイル」が誕生。

しかし memory の **物理配置・正本所在・sync 経路** は未整理だった:

- repo / vault / VPS の 3 箇所に同じファイルが存在(soil と同じ構造)
- どこが正本か明文化されていない
- repo ↔ VPS の経路(soil-sync 相当)が無い
- `raw/*.md` は `.gitignore` で除外されているが、sync 時の扱いが曖昧

S28 でついでに整理しようかという議論もあったが、S28 は path 大移動の取りこぼし修正に絞った。本セッション(S29)で「soil と対称」として片付ける。

## 決定

### 1. 配置(soil と同形)

memory は 3 箇所に配置:

- **repo**: `~/harappa-garden/garden/memory/`(git 管理)
- **vault**: `~/Dropbox/gakuchovault/garden/memory/`(Obsidian、LiveSync 経由で VPS と双方向)
- **VPS**: `/home/vps-harappa/garden-mirror/garden/memory/`(ingest-raw 種 / bot の書き込み先)

### 2. 正本ルール(ファイル種別ごとに分離)

| パス | 書き手 | 正本 | git | sync |
|---|---|---|---|---|
| `memory/README.md` | 人(Claude) | repo | ✅ | pull/push 対象 |
| `memory/master/raw/.gitkeep` | 人 | repo | ✅ | pull/push 対象 |
| **`memory/master/raw/*.md`** | bot.py / memory_logger.py のみ | **VPS 専属** | ❌(.gitignore) | **除外** |
| `memory/master/wiki/*.md` | ingest-raw 種(VPS) + 人(repo / vault) | **VPS 主・repo 従** | ✅ | pull/push 対象 |
| `memory/master/wiki/index.md` | 同上 | 同上 | ✅ | pull/push 対象 |

#### 「VPS 主・repo 従」の意味

`wiki/*.md` は両方向に書き込みが発生する:

- **VPS から**: 毎晩 03:30 の `ingest-raw` 種が RAW を読み wiki に章追記(主)
- **repo から**: Claude セッション中にガクチョと相談しながら整理・編集(従)
- **vault から**: 人が Obsidian で読み・たまに編集(従、LiveSync 経由で VPS に行く)

積み上げ頻度は ingest-raw が圧倒的に高いので **VPS を主正本** と定義。repo は (1) git 履歴を残す (2) Claude が手で編集して push する経路、として位置付ける。

#### 競合回避の規律

- **セッション開始時に `pull-from-vps.sh`**(VPS の最新 wiki を取り込む)
- セッション中に Claude が編集
- **セッション終了時 / commit 前に `push-to-vps.sh`**(repo の変更を VPS に戻す)

この順序を守れば 99% の場合競合しない。同時編集の理論上競合は手動マージで対応。

### 3. `raw/` は VPS 専属(repo に上げない)

`master/raw/*.md` は:

- **機密**(Discord 対話の生ログ = ガクチョの判断ログ含む)
- **片方向書き込み**(bot.py / memory_logger.py だけが書く、人は触らない)
- **14 日経過で Stage B バッチが削除予定**(現在 Stage A.5、未実装)

これを repo に上げる意味がない。`.gitignore` で除外済(S22)に加え、sync スクリプトでも `--exclude='*/raw/*.md'` を必ず付与し **構造的に repo に流れ込まない** ようにする。`.gitkeep` は除外対象外なのでディレクトリ存在保証は保たれる。

### 4. sync スクリプト(soil-sync と対称)

`garden/services/memory-sync/`:

- `pull-from-vps.sh` — VPS → repo
- `push-to-vps.sh` — repo → VPS
- `README.md` — 使い方

soil-sync との差分は **`--exclude='*/raw/*.md'` の有無** のみ。それ以外は同じ構造で、見比べた時に「対」と分かるようにした。

### 5. セッションプロトコル

CLAUDE.md のセッションプロトコルに以下を追記する方針:

- **開始時**: memory wiki を参照する作業がある時のみ `pull-from-vps.sh`(なければ省略可)
- **終了時**: memory wiki を編集した時のみ `push-to-vps.sh`(なければ省略可)

soil-sync と同じく「無関係なセッションでは省略可」の運用。**毎セッション必須にしない理由**:Stage A.5 が ingest-raw に頼って毎晩自動更新する設計なので、Claude が手を触れないセッションでは pull する必然性がない(commit 時に古い wiki を上書きするリスクは push 側のみ気をつければよい)。

### 6. 1 本に統合せず別ディレクトリ

`garden-sync` 的に soil + memory を 1 本にまとめる選択肢もあったが、責務分離を優先して別ディレクトリにした:

- soil と memory は対象ディレクトリも除外ルールも異なる
- どちらかだけ実行するケースがある(memory 編集だけのセッション、soil 編集だけのセッション)
- 1 本にすると `--soil` `--memory` 等のフラグが必要になり複雑化

将来両方を常に同期したくなったら、薄いラッパー(`garden-sync.sh` が両方呼ぶ)を上に被せる選択肢が残る。

## 採用しなかった案

### 案 A: wiki も VPS 専属(repo に上げない)

検討: raw と同じく wiki も VPS だけにすれば、競合問題はゼロになる。
却下理由:
- Claude が wiki を編集する場面が確実にある(ingest-raw の出力をガクチョと議論しながら整える、新主題の章立て見直し等)
- repo に履歴を残したい(誰がいつ何を加えたかの可視化)
- git diff レビューの対象にしたい

### 案 B: repo を完全な正本にする(VPS は実行用キャッシュ)

検討: soil の構造ファイル正本ルールと同じく、repo を主にする。
却下理由:
- ingest-raw が VPS で書く頻度が圧倒的に高い(毎晩自動)
- repo を主にすると毎セッション開始時に pull が必須になり、忘れた時に古い状態で push して上書き事故が起きる
- VPS が実態として書き手の主役なので、設計と現実をずらすメリットがない

### 案 C: 双方向同期(unison 等)

検討: bidirectional sync ツールで自動解決。
却下理由:
- 仕組みが重い(soil-sync は 30 行の bash で済んでいる)
- 競合自動解決はブラックボックスになり事故時の追跡が難しい
- セッション開始 pull → 終了 push の規律で十分回避できる

## 影響

- **ADR 起票**: 本ファイル
- **新規ファイル**:
  - `garden/services/memory-sync/pull-from-vps.sh`
  - `garden/services/memory-sync/push-to-vps.sh`
  - `garden/services/memory-sync/README.md`
- **更新**:
  - `garden/memory/README.md` に正本ルール表を追記
  - `CLAUDE.md` セッションプロトコルに memory-sync 言及を追記
  - `garden/MAP.md` の「次回本命候補(1)」を消化済にし、`garden/services/memory-sync/` を区画表に追加
- **検証済**: pull-from-vps dry-run + 実走で正常動作、raw/*.md が除外されることを確認

## 関連

- 並列 ADR: [2026-06-02 soil の正本と 3 箇所配置の同期ルール](2026-06-02-soil-source-of-truth.md)
- 三層分離 ADR: [2026-05-31 memory-three-layer-and-soil-routing](2026-05-31-memory-three-layer-and-soil-routing.md)
- Stage A.5 active 化(本 ADR の前提): [2026-06-02 セッション26](../sessions/2026-06-02-session26.md)
- ingest-raw 副次発見(本 ADR を促した経緯): [2026-06-03 セッション28 §4](../sessions/2026-06-03-session28.md)
