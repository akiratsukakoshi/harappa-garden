# ADR 2026-06-05: 社内 LINE サーバはコンテナ化(ホストプロセスでなく)+ テスト用エアギャップ例外

- 状態: Accepted
- 日付: 2026-06-05(セッション34)
- 関連: [2026-06-03 vendor-neutral-interaction-layer](2026-06-03-vendor-neutral-interaction-layer.md)(実装順序「2」) / [DEPLOY.md](../../garden/services/garden-gaku-co/DEPLOY.md)

## 背景

S32 で社内 LINE サーバ(core_team)を実装し、S34 で本番 VPS にデプロイ。当初設計(DEPLOY.md 初版)は
**ホストプロセス**(`venv-line` + `run-line-server.sh` の uvicorn を 127.0.0.1:8011)で動かし、
NPM から `127.0.0.1:8011` に proxy する想定だった。

## 課題

1. **NPM はコンテナ**(`proxy-manager_default` 上)。コンテナ内の `127.0.0.1` はコンテナ自身を指し、
   ホストの 8011 に届かない。
2. ホストを docker ブリッジ gateway(172.20.0.1)で指しても、**VPS のファイアウォール(iptables INPUT)が
   docker ブリッジ → ホストの通信を DROP** している(8011 だけでなく NPM 自身の 81 番も timeout で確認)。
   sudo 権限が無く firewall は変更できない。
3. つまり「NPM(コンテナ)→ ホストプロセス」は構造的に塞がれている。

## 決定

**LINE サーバを `proxy-manager_default` ネットワーク上のコンテナ `garden-gaku-core` にする。**
NPM は他サービス(couchdb / gaku-co5)と同じく **コンテナ名解決**で `garden-gaku-core:8011` に到達する。
ファイアウォール無関係。ポートは publish せず(`expose` のみ)= 公開 IP には出ない(エアギャップの一部)。

- イメージ: `python:3.12-slim` + `requirements-line.txt`(`Dockerfile.line`)。コードは bind-mount。
- マウント: `/home/vps-harappa/garden` と `/home/vps-harappa/garden-mirror` を**同じ絶対パス**で
  (CHARTER / persona / log / RAW 記憶が無改造で動く)。
- `--user 1000:1000`(RAW 書き込み所有者を host と揃える)、`--restart unless-stopped`(cron 不要)。
- **起動は `docker run`(`run-line-container.sh`)**。VPS の `docker-compose` は v1 で、buildkit 製
  イメージの image config に `ContainerConfig` キーが無いと recreate 経路で KeyError で落ちる既知バグが
  あるため、compose は使わない(`docker-compose.line.yml` は参考用に残す)。

廃止: `run-line-server.sh` + `venv-line`(ホストプロセス方式)。

## テスト用エアギャップ例外(`LINE_TEST_USER_IDS`)

本番グループ投入の前に、ガクチョ個人と 1:1 でテストするための限定例外を追加。

- `LINE_TEST_USER_IDS`(カンマ区切り)に入れた **userId の 1:1 のみ通す**。既定は空 = 全 1:1 を無視
  (エアギャップ維持)。本番グループ投入後は空に戻す運用。
- 1:1 は「全メッセージが bot 宛」なので **gate(宛て判定)を素通り**(意味的に正しい。hack ではない)。
- scope は `line_core_team` のまま。相手は庭師本人(全透視権)なので情報境界の問題なし。

## 付随して直したこと

- **tool-use の 400 バグ**: respond の tool-use ループが assistant ターンを「テキストのみ」で積み、
  モデルが返した `tool_use` ブロックを欠落させていた → 続く `tool_result` に対応する `tool_use` が無く
  Anthropic が 400。中立 Provider 形式に「assistant の tool_calls」を表現する形を追加し、
  `AnthropicProvider._to_anthropic_message` で text + tool_use ブロック列に再構成するよう修正。
- MVP の `echo` は noop の配線確認用 placeholder。1:1 テストでは渡さない(`offer_tools=False`)
  — 渡すとモデルが無駄に呼び、最終テキストが空になって reply が飛ばないことがあるため。
  実ツール実装後に tool-use を会話でも再開する。

## 影響

- 「業務 tool は水面下で Garden が選ぶ」方針(plot_gardener)と整合。次フェーズは
  テスト環境(1:1)で区画(plot)の read tool 群を実装 → 確認 → 本番グループへ昇格、の流れ。
- ベンダー中立の規律は不変(`import anthropic` は provider.py のみ)。

## 却下案

- **0.0.0.0 bind + firewall 開放**: sudo 無し + 公開 IP に 8011 を晒すリスク。却下。
- **gateway IP bind**: firewall が DROP するため到達不可。却下。
