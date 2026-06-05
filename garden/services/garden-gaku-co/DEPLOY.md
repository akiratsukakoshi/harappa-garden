# 社内 LINE サーバ(core_team)デプロイ Runbook

> S32 実装 → **S34(2026-06-05)で本番 VPS にデプロイ完了 + ガクチョと 1:1 疎通 GREEN**。
> 本番グループ投入(groupId 確定)だけ残(あえてテスト先行)。
> **ガクチョの手が要る箇所を ⭐ で明示**。secret は Claude に渡さず、ガクチョが VPS の `.env` に直貼り。

関連: ADR [2026-06-03 vendor-neutral](../../../docs/decisions/2026-06-03-vendor-neutral-interaction-layer.md) 実装順序「2」/ ADR [2026-06-05 コンテナ化](../../../docs/decisions/2026-06-05-line-server-containerization.md) / セッション [2026-06-05-session34](../../../docs/sessions/2026-06-05-session34.md)

## アーキテクチャ(配線)

```
運営スタッフ LINE グループ / (テスト中は)ガクチョ個人 1:1
  ↓ HTTPS
DNS: core.harappa.monster → 162.43.40.86(Xserver VPS DNS、ns*.xvps.ne.jp)
  ↓
NPM(proxy-manager_default 上のコンテナ)Proxy Host + Let's Encrypt SSL
  ↓ docker ネットワーク内で コンテナ名解決 → garden-gaku-core:8011
コンテナ garden-gaku-core(uvicorn / line/app.py / FastAPI)
  署名検証 → source 検査(core_team group か、テスト許可 userId か)= エアギャップ
  → gate(group のみ。1:1 は素通り)→ respond(+ tool-use)
  → reply → RAW logging(memory_logger, scope=line_core_team)
頭脳 b = Anthropic SDK(Provider アダプタ経由、import anthropic は provider.py だけ)
```

**重要(S34 で判明)**: VPS のファイアウォールが docker ブリッジ → ホスト(gateway 172.20.0.x)の
INPUT を DROP するため、NPM コンテナからホストプロセスの 8011 には到達できない。
よって LINE サーバは **`proxy-manager_default` 上のコンテナ**にして、NPM からコンテナ名で叩く
(couchdb / gaku-co5 と同じ方式)。詳細は [ADR 2026-06-05](../../../docs/decisions/2026-06-05-line-server-containerization.md)。

## 手順(役割分担)

### 1. コードを VPS へ配置(Claude)
```bash
rsync -avh -e ssh \
  /home/tukapontas/harappa-garden/garden/services/garden-gaku-co/ \
  harappa:/home/vps-harappa/garden/services/garden-gaku-co/ \
  --exclude '.env' --exclude 'venv' --exclude 'venv-line' --exclude '__pycache__' --exclude '*.pid'
```

> ⚠️ **実行ビットは git で管理する**(`-a` は perms を伝播するため)。`*.sh` が repo で `100644` のまま
> commit されていると、この rsync が **VPS 側の実行ビットを 644 で上書き** → cron が `Permission denied`
> で沈黙する。新しい `*.sh` を足したら `git update-index --chmod=+x` で `100755` にしてから push すること。
> (S35 で run-bot/morning-greet/night-cheer の 3 本がこれで停止した。`git ls-files -s *.sh` で 755 を確認)

### 2. ⭐ secret を VPS `.env` に記入(ガクチョ)
VPS の `/home/vps-harappa/garden/services/garden-gaku-co/.env`(chmod 600)に直接記入:
```
LINE_CORE_TEAM_CHANNEL_SECRET=<社内チャネルの Channel secret(32 字)>
LINE_CORE_TEAM_ACCESS_TOKEN=<社内チャネルの Channel access token(long-lived)>
ANTHROPIC_API_KEY=<社内専用 API key(sk-ant…、社外と別建て)>
LINE_CORE_TEAM_GROUP_ID=          # 手順6で確定してから記入(最初は空)
LINE_TEST_USER_IDS=              # テスト中はガクチョ個人 userId。本番投入後は空に戻す
```
※ 値の確認は length / set 判定のみ(`echo "$VAR"` 禁止、security ルール)。
※ nano 保存時は `..env.swp` が残らない(= 確実に保存された)ことを確認。

### 3. コンテナ起動(Claude)
```bash
ssh harappa 'cd /home/vps-harappa/garden/services/garden-gaku-co && ./run-line-container.sh --build'
# health(NPM コンテナから):
ssh harappa 'docker exec proxy-manager_nginx-proxy-manager_1 curl -s http://garden-gaku-core:8011/health'
```
`--restart unless-stopped` でキープアライブ(cron 不要)。`.env` を変えたら **作り直しが必要**
(env_file はコンテナ作成時しか読まれない)→ `./run-line-container.sh` を再実行。

### 4. ⭐ DNS A レコード(ガクチョ)
Xserver VPS の DNS パネル → `harappa.monster` に追加:
| ホスト名 | 種別 | 内容 |
|---|---|---|
| `core` | A | `162.43.40.86` |
反映確認は Claude が `dig` で行う。

### 5. ⭐ NPM Proxy Host + SSL(ガクチョ)
> NPM 管理画面に入れない時(パケットフィルタ): Claude が SSH トンネルを張る
> `ssh -fN -L 8181:127.0.0.1:81 harappa` → ブラウザで `http://localhost:8181/`。
> admin ログイン不能時は bcrypt で安全リセット(ADR 2026-05-25 決定8 / 下記ロールバック欄)。

- Domain Names: `core.harappa.monster`
- Scheme: `http` / Forward Hostname: **`garden-gaku-core`**(コンテナ名)/ Forward Port: `8011`
- Websockets: OFF
- SSL タブ: Request a new Let's Encrypt Certificate + Force SSL ON(**DNS 反映後**に押す)

### 6. ⭐ Webhook URL + Verify(ガクチョ)
- LINE Developers Console(社内チャネル)→ Messaging API → Webhook URL = `https://core.harappa.monster/webhook`、Use webhook ON、**Verify** → Success。
- **LINE Official Account Manager → 応答設定**: 「チャット」OFF + 「Webhook」ON + 応答メッセージ OFF
  (ここが「チャット」だと 1:1/group のメッセージが webhook に飛ばない。Verify が通っても実メッセージが来ない時はここ)。

### 7. テスト(1:1・あえて本番グループより先)
- ⭐ ガクチョが bot を友だち追加 → 1:1 で 1 発言 → Claude がログから `userId` 取得。
- ⭐ ガクチョ(or Claude)が `.env` の `LINE_TEST_USER_IDS` にその userId → `./run-line-container.sh` で作り直し。
- 1:1 で会話確認(1:1 は gate 素通り = 全メッセージが bot 宛)。

### 8. ⭐ 本番グループ投入 → groupId 確定(ガクチョ + Claude)— **残**
- LINE Developers Console で「Allow bot to join group chats」ON。
- ガクチョが bot を運営スタッフ LINE グループに招待 → グループで 1 発言。
- Claude が `docker logs garden-gaku-core` から `groupId` を取得。
- ⭐ `.env` の `LINE_CORE_TEAM_GROUP_ID` に記入 + `LINE_TEST_USER_IDS` を空に → `./run-line-container.sh`。
- 「ガクコ」と呼びかけて応答が返れば本番疎通完了。

## 検証ポイント
- [x] HTTPS `/health` 200 / Let's Encrypt 証明書 / `GET /webhook` 405 / `POST /webhook`(署名なし)403
- [x] 1:1(テスト許可 userId)で gate 素通り → respond → reply 200
- [x] RAW が `garden/memory/line_core_team/raw/{date}.md` に溜まる
- [ ] (本番)group で「ガクコ」宛て → 応答 / 他宛て雑談 → 黙る(gate)
- [ ] 社外グループ・未許可個人 → 一切応答しない(エアギャップ)

## ロールバック / 運用
- 停止: `ssh harappa 'docker stop garden-gaku-core'`(`--restart` で起き直すので恒久停止は `docker rm -f`)。
- LINE 側: Webhook を OFF。社外 gaku-co5.0 とは別プロセス・別 LINE 公式なので影響しない。
- NPM admin パスワードリセット(bcrypt、生成→60字 assertion→DB 反映、要 DB バックアップ): ADR [2026-05-25 決定8](../../../docs/decisions/2026-05-25-couchdb-livesync-implementation.md)。

## 廃止
- `run-line-server.sh` + `venv-line`(ホストプロセス方式)は S34 のコンテナ化で不要。
- `docker-compose.line.yml` は compose v1 バグで使えず参考用(起動は `run-line-container.sh`)。
