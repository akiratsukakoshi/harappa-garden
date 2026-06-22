# ADR 2026-06-23: board の住所は VPS 一箇所に統一する

## ステータス

採用(セッション57)

## 背景

セッション57 で、Claude(私)が SNS 投稿の状況確認において **基本構造を誤読**した。local repo の `garden/board/pending/` を見て「SNS board が無い・何も予約されていない」と断定したが、実際は SNS 区画が `execution_host: vps` で動いており、board・選定画像・予約はすべて **VPS 上**にあった。

ガクチョの指摘: 「これは Claude のメモリで上塗りする話ではなく、**プロジェクト構造そのものが誤読させた**のではないか。board の正本が VPS にしか無いと読み取れない構造になっていないか」。

調査の結果、構造的な歪みが確認された:

- **board が二重に存在しうる**:
  - scribe(`execution_host: local`・Plaud がローカル WSL 専用)は board を local `garden/board/pending/` に書き、`run-local.sh` が VPS へ rsync。
  - VPS で動く種(SNS / finance 等)は VPS の `board/pending/` に直接書く。
- よって `ls garden/board/pending/`(状態を見る最も自然な操作)が、**警告なしに不完全な答え**(ローカル種の分だけ)を返す。

さらに、この二重構造には実害があった:

1. **墓場化**: scribe は push 後もローカルの board を掃除せず溜める。古い board が残り「これが承認待ちだ」と誤認させる(誤読の直接原因)。
2. **VPS が stale**: push が `rsync --ignore-existing` だったため、scribe が同一 board を更新しても VPS に届かない。実測で local(完全版)と VPS(古い版)が食い違っていた。

## 決定

**board の住所を VPS 一箇所(`/home/vps-harappa/garden/board/pending/`)に統一する。** repo に board の**コンテンツ用ディレクトリを持たない**。

- ローカルで動く種(scribe)は、board を **scribe 内部の一時 outbox(`garden/services/scribe/outbox/`・`.gitignore` 対象)** に書く。「board」という語を local のパスに出さない。
- `run-local.sh` が outbox → VPS `board/pending/` へ push したのち **outbox を空にする**(墓場を作らない)。
- push は **`--ignore-existing` を使わない**(更新を VPS に届ける)。同日内に board を書き直したら VPS で上書きし、`notified_at` が消えることで send_pending が更新版を再通知する(新情報なので妥当)。新規録音が無い回は board を書かない(空振り通知を出さない)。
- repo の `garden/board/` に残るのは**ルールの正本(README.md)と failed/ 等の枠だけ**。
- 状態を確認する正しい手段 = ダッシュボード(`core.harappa.monster/board`)/ 朝ブリーフィング / `ssh harappa 'ls /home/vps-harappa/garden/board/pending/'`。

## 根拠

- **誤読は構造が生んだ**。memory(Claude 内部知識)で塞ぐのは backstop に過ぎず、「自然な操作が誤った答えを返す」構造を残すと、memory を持たない読み手(別 LLM・将来のセッション・人間)が同じ誤りを犯す。住所を一箇所にすれば、`garden/board/` を見ても board コンテンツが無い=VPS を見るしかない、と構造から確定する。
- **二重 push は実害がある**(墓場化・stale)。一方向(local outbox → VPS、push 後に消す)にすれば食い違いが原理的に起きない。

## 関連

- 構造の前提: [2026-06-22 board の一元管理](2026-06-22-board-central-management.md)(正本+レジストリ+リンター)。本 ADR は「**board の物理的な住所**」をそこに足す。
- scribe がローカル専用な理由: [[plaud-bridge-local-wsl]](memory)。
- セッション: [2026-06-23 session57](../sessions/2026-06-23-session57.md)
