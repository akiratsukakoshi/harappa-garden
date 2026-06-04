# 社内 LINE サーバ(core_team)デプロイ Runbook

> S32(2026-06-04)実装。コードはローカル検証 GREEN。ここから先は VPS + LINE/NPM コンソール操作。
> **ガクチョの手が要る箇所を ⭐ で明示**。secret は Claude に渡さず、ガクチョが VPS の `.env` に直貼り。

関連: ADR [2026-06-03 vendor-neutral-interaction-layer](../../../docs/decisions/2026-06-03-vendor-neutral-interaction-layer.md) 実装順序「2」/ セッション [2026-06-04-session32](../../../docs/sessions/2026-06-04-session32.md)

## アーキテクチャ(配線)

```
運営スタッフ LINE グループ
  ↓ HTTPS
NPM 社内専用サブドメイン(別 LINE 公式・社外 gaku-co とエアギャップ)
  ↓ reverse proxy → 127.0.0.1:8011
uvicorn (line/app.py / FastAPI)
  署名検証 → core_team group か検査(エアギャップ)
  → gate(Stage1 Haiku)→ should なら respond(Stage2 + tool-use)
  → reply → RAW logging(memory_logger, scope=line_core_team)
頭脳 b = Anthropic SDK(Provider アダプタ経由、import anthropic は provider.py だけ)
```

## 手順(役割分担)

### 1. コードを VPS へ配置(Claude)
```bash
rsync -avh -e ssh \
  /home/tukapontas/harappa-garden/garden/services/garden-gaku-co/ \
  harappa:/home/vps-harappa/garden/services/garden-gaku-co/ \
  --exclude '.env' --exclude 'venv' --exclude 'venv-line' --exclude '__pycache__' --exclude '*.pid'
# 別 venv を作って LINE 依存をインストール
ssh harappa 'cd /home/vps-harappa/garden/services/garden-gaku-co && \
  python3 -m venv venv-line && \
  ./venv-line/bin/pip install -r requirements-line.txt'
```

### 2. ⭐ secret を VPS `.env` に記入(ガクチョ)
VPS の `/home/vps-harappa/garden/services/garden-gaku-co/.env`(chmod 600)に、S31 取得済 + 手配済の値を**直接記入**:
```
LINE_CORE_TEAM_CHANNEL_SECRET=<社内チャネルの Channel secret>
LINE_CORE_TEAM_ACCESS_TOKEN=<社内チャネルの Channel access token>
ANTHROPIC_API_KEY=<社内専用 API key(社外と別建て)>
# LINE_CORE_TEAM_GROUP_ID は手順6で確定してから記入(最初は空でよい)
```
※ `.env.example` を雛形に。`echo "$VAR"` 等で値を表示しない(security ルール)。

### 3. ⭐ NPM 社内専用サブドメイン(ガクチョ + Claude)
- NPM UI で新規 Proxy Host を作成 → Forward to `127.0.0.1:8011`(または `localhost`)。
- ドメインは社外 gaku-co とは**別**サブドメイン(例 `gaku-core.duckdns.org` 等、流儀は既存 vps 構成に合わせる)。
- SSL(Let's Encrypt)を有効化。
- DNS(duckdns 等)で当該サブドメインを VPS IP に向ける。

### 4. サーバ起動 + キープアライブ(Claude)
```bash
ssh harappa 'cd /home/vps-harappa/garden/services/garden-gaku-co && ./run-line-server.sh'
ssh harappa 'curl -s http://127.0.0.1:8011/health'   # {"status":"ok",...} を確認
# crontab に追加:
#   */2 * * * * /home/vps-harappa/garden/services/garden-gaku-co/run-line-server.sh
#   @reboot     /home/vps-harappa/garden/services/garden-gaku-co/run-line-server.sh
```

### 5. ⭐ Webhook URL を LINE に入力 + Verify(ガクチョ)
- LINE Developers Console(社内チャネル)→ Messaging API → Webhook URL に `https://<社内サブドメイン>/webhook`。
- Use webhook = ON。
- **Verify** ボタン → Success を確認(空イベントに署名付きで 200 を返す実装になっている)。

### 6. ⭐ bot を運営スタッフグループに追加 → groupId 確定(ガクチョ + Claude)
- ガクチョが bot を運営スタッフ LINE グループに招待。
- 誰かがそのグループで 1 発言 → Claude が webhook ログ(`/home/vps-harappa/garden/log/line-server.log`)から `groupId` を確認。
- ⭐ ガクチョが `.env` の `LINE_CORE_TEAM_GROUP_ID` にその値を記入 → サーバ再起動(pidfile 削除 → run-line-server.sh)。
- 「ガクコ」と呼びかけて応答が返れば疎通完了。

## 検証ポイント(デプロイ後の初ライブ)
- [ ] 「ガクコ」宛て発言 → 応答が返る(gate=True 経路)
- [ ] 他の人宛て・雑談 → 黙る(gate=False、沈黙の規律)
- [ ] 社外グループ・個人 1:1 では一切応答しない(エアギャップ)
- [ ] RAW が `garden/memory/line_core_team/raw/{date}.md` に溜まる
- [ ] 機微(財務/給与)を聞かれても「庭師の領域」と返し、tool を持たない(情報境界)

## ロールバック
- サーバ停止: `ssh harappa 'kill $(cat /home/vps-harappa/garden/services/garden-gaku-co/.line-server.pid)'` + cron 行をコメントアウト。
- LINE 側: Webhook を OFF。
- 社外 gaku-co5.0 とは完全別プロセス・別 LINE 公式なので、本サーバ停止は社外に影響しない。
