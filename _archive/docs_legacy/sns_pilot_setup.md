# SNS Pilot セットアップ手順

`apps/sns_pilot/` を動かすために必要な4つの設定を行います。

---

## 1. Meta Access Token の取得

### 必要なもの
- Instagramビジネスアカウント ✅（確認済み）
- Facebookページ（Instagramと紐付け済みか要確認）
- Meta for Developers アカウント

### 手順

1. **Meta for Developers にアクセス**
   https://developers.facebook.com/apps/

2. **アプリを作成**（なければ）
   - 「アプリを作成」→「ビジネス」タイプを選択

3. **Graph API Explorer で Token を取得**
   https://developers.facebook.com/tools/explorer/
   - 対象アプリを選択
   - 「アクセス許可を追加」で以下を全て選択:
     - `instagram_basic`
     - `instagram_content_publish`
     - `instagram_manage_insights`
     - `pages_read_engagement`
     - `pages_manage_posts`
   - 「ユーザーアクセストークンを生成」をクリック

4. **長期トークンに変換**（有効期限60日）
   以下のURLにアクセス（`<SHORT_TOKEN>` と `<APP_ID>`, `<APP_SECRET>` を置換）:
   ```
   https://graph.facebook.com/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=<APP_ID>
     &client_secret=<APP_SECRET>
     &fb_exchange_token=<SHORT_TOKEN>
   ```
   返ってきた `access_token` を `.env` の `META_ACCESS_TOKEN=` に設定する。

5. **IG Account ID の確認**
   ```
   https://graph.facebook.com/me/accounts?access_token=<TOKEN>
   ```
   → Facebookページ一覧が返る。そのページに紐付いたIGアカウントIDを取得:
   ```
   https://graph.facebook.com/<PAGE_ID>?fields=instagram_business_account&access_token=<TOKEN>
   ```
   返ってきた `instagram_business_account.id` が `META_IG_ACCOUNT_ID`。

6. **`.env` に設定**
   ```
   META_ACCESS_TOKEN=<長期トークン>
   META_IG_ACCOUNT_ID=<IGアカウントID>
   META_PAGE_ID=<FacebookページID>
   ```

### トークンの更新について
長期トークンは60日で失効します。
以下のコマンドで残り有効期間を確認できます:
```
https://graph.facebook.com/debug_token?input_token=<TOKEN>&access_token=<TOKEN>
```
月1回、月次レポート時に確認することを推奨します。

---

## 2. Google Drive フォルダの作成

Instagram投稿用の画像を一時的に公開URLとして提供するためのDriveフォルダです。

1. Google Drive で「sns_pilot_images」フォルダを作成
2. フォルダIDをURLから取得
   （例: `https://drive.google.com/drive/folders/XXXXXXXXXX` の `XXXXXXXXXX` 部分）
3. `.env` に設定:
   ```
   SNS_DRIVE_FOLDER_ID=<フォルダID>
   ```

---

## 3. Google Sheets の service account 共有

振り返りスプレッドシートにプログラムからアクセスするための設定です。

1. `credentials.json`（サービスアカウントキー）がプロジェクトルートにあることを確認
2. スプレッドシートをサービスアカウントのメールアドレスと共有
   - スプレッドシートを開く → 共有 → サービスアカウントのメールを追加（編集者権限）
   - サービスアカウントのメールは `credentials.json` 内の `client_email` フィールド

---

## 4. pytz のインストール確認

`schedule_posts.py` は `pytz` を使います。未インストールの場合:
```bash
.venv/bin/pip install pytz
```

---

## 5. IGスケジューラーサーバーの設定

Meta Graph APIのIGスケジュール機能はTech Provider申請が必要なため使用不可。
代替として、Xserver VPS上のDockerコンテナがIG投稿の予約キューを管理する。

### 現在の稼働状況（設定済み）
- **API URL:** `https://ig-api.harappa.monster`
- **サーバー:** `162.43.40.86`（Xserver VPS, vps-harappa）
- **コンテナ:** `/home/vps-harappa/ig_scheduler/`
- **設定完了日:** 2026-04-23

### .env への追加（設定済み）
```
IG_SCHEDULER_API_URL=https://ig-api.harappa.monster
IG_SCHEDULER_API_KEY=（管理者に確認）
```

### 再デプロイが必要な場合
サーバーコードを変更した場合は以下を実行:
```bash
bash scripts/deploy_ig_scheduler.sh
```

### サーバー側 .env の更新
```bash
ssh harappa
nano /home/vps-harappa/ig_scheduler/.env
cd /home/vps-harappa/ig_scheduler && docker-compose restart
```

### ヘルスチェック
```bash
curl https://ig-api.harappa.monster/health
```

### 予約ジョブ確認
```bash
curl -H "x-api-key: <IG_SCHEDULER_API_KEY>" https://ig-api.harappa.monster/jobs
```

---

## 動作確認

設定完了後、以下でドライランテスト:
```bash
cd /home/tukapontas/harappa-cockpit
.venv/bin/python apps/sns_pilot/schedule_posts.py data/sns_pilot/drafts/2026-02-09.md --dry-run
```

週次レポートのテスト:
```bash
.venv/bin/python apps/sns_pilot/weekly_report.py
```
