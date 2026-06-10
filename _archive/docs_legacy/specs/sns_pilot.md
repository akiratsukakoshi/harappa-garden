# App Definition: sns_pilot

## 1. アプリ概要

**sns_pilot** は、原っぱ大学のSNS運用（Instagram/Facebook）を支援するAI Agent Skillです。
「生素材→AI整形」の思想に基づき、ガクチョーが提供する写真とひとことコメントをもとに、AIがガクチョー文体でキャプションを整形します。週3投稿（火・木・土）を基本とし、Facebook投稿はMeta Graph APIで自動スケジュール、Instagram投稿はXserverクラウドサーバー上のIGスケジューラー経由で自動スケジュールします。

---

## 2. システム構成

### 2.1 使用API・サービス

| サービス | 用途 | 認証方式 |
|---------|------|---------|
| Meta Graph API v21.0 | FB投稿スケジュール、IG即時投稿、インサイト取得 | Page Access Token |
| Instagram Graph API | IGメディア情報取得 | Page Access Token |
| IGスケジューラー API | IG写真投稿の予約キュー管理 | APIキー（X-API-Key） |
| Google Sheets API | KPIログ記録 | サービスアカウント |

### 2.2 IGスケジューラーサーバー

Meta Graph APIのIGスケジュール投稿機能はTech Provider申請（大企業向け）が必要なため使用不可。
代替として、Xserverクラウド上のDockerコンテナ（`ig_scheduler`）が予約キューを管理し、指定時刻にIG即時投稿APIを呼び出す。

**エンドポイント:** `https://ig-api.harappa.monster`
**Dockerホスト:** `162.43.40.86`（Xserver VPS）
**コンテナ:** `/home/vps-harappa/ig_scheduler/`
**ワーカー実行間隔:** 毎分（APScheduler）
**障害通知:** 投稿失敗時に `tukapontas@gmail.com` へメール送信

### 2.3 環境変数（.env）

```
META_ACCESS_TOKEN        # Facebookページアクセストークン（type=PAGE）
META_IG_ACCOUNT_ID       # Instagram Business Account ID（17841404542535531）
META_PAGE_ID             # Facebook Page ID（348855281822862）
META_PAGE_ACCESS_TOKEN   # ユーザーアクセストークン（インサイト取得用）
META_BUSINESS_ID         # Business Manager ID（398396207313279）
SNS_DRIVE_FOLDER_ID      # Google Drive フォルダID（予備用途）
IG_SCHEDULER_API_URL     # IGスケジューラーURL（https://ig-api.harappa.monster）
IG_SCHEDULER_API_KEY     # IGスケジューラーAPIキー
```

### 2.3 重要な設定上の注意点

- **META_ACCESS_TOKEN** はtype=PAGEのページトークン。`/me/accounts` は使えない。`get_page_access_token()` はこのトークンをそのまま返す。
- **META_IG_ACCOUNT_ID** は `17841404542535531`（harappa_daigaku）。Business Manager ID（398396207313279）とは別物。
- **Facebook Page ID** は `348855281822862`。`129417183848258` は誤り。
- タイムゾーン変換は必ず `JST.localize(datetime(...))` を使うこと。`datetime(..., tzinfo=JST)` を使うと東京の歴史的LMT（UTC+9:19）が適用され19分ずれる。
- Metaアプリは **Liveモード** で運用すること（Developmentモードでは`instagram_content_publish`が動かない）。

---

## 3. ファイル構成

```text
apps/sns_pilot/
├── meta_client.py       # Meta Graph API クライアント（schedule_ig_photo_via_server含む）
├── schedule_posts.py    # ドラフトMD → IG/FB自動スケジュール
├── sheets_client.py     # Google Sheets KPIログ書き込み
├── weekly_report.py     # 週次レポート生成（Insights取得→MD出力）
├── drive_uploader.py    # Drive画像アップロード（現在未使用）
└── config.json          # スプレッドシートID・投稿時刻・KPI目標値

deploy/ig_scheduler/     # IGスケジューラーサーバーコード
├── app.py               # FastAPI + APSchedulerワーカー
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example

scripts/
└── deploy_ig_scheduler.sh  # サーバーへのデプロイスクリプト

.agent/skills/sns_pilot/
├── SKILL.md             # スキル定義・Human-in-the-Loopワークフロー
└── SNS_STRATEGY.md      # SNS戦略・KPI設計・チャンネル役割定義

data/sns_pilot/
├── context/             # ガクチョー文体・価値観の参照元MD
├── drafts/              # 週次ドラフト（YYYY-MM-DD.md）
├── images/
│   ├── candidates/      # 候補画像（毎週補充）
│   ├── selected/        # 今週採用画像（スクリプトが参照）
│   └── carry_over/      # 次回繰り越し画像
└── reports/             # 週次KPIレポート（YYYY-MM-DD_weekly.md）
```

---

## 4. 主要モジュール仕様

### meta_client.py

| メソッド | 説明 |
|---------|------|
| `get_page_access_token()` | `META_ACCESS_TOKEN` をそのまま返す（すでにPage Token） |
| `upload_photo_for_url(image_path)` | FB非公開写真としてアップロードしCDN URLを返す |
| `schedule_ig_photo_via_server(image_url, caption, publish_at)` | **現行メイン。** IGスケジューラーサーバーに予約ジョブを登録する |
| `schedule_ig_photo(image_url, caption, publish_at)` | ~~IGフィード写真をスケジュール~~ **使用不可**（Tech Provider申請が必要） |
| `schedule_fb_photo(image_path, caption, publish_at)` | FBページへ写真投稿をスケジュール（`/photos` endpoint） |
| `get_post_insights(media_id)` | 投稿インサイト取得（reach/saved/shares等） |
| `get_account_insights(days)` | アカウント全体インサイト取得 |
| `get_follower_count()` | 現在のフォロワー数取得 |

### schedule_posts.py

**実行方法:**
```bash
PYTHONPATH=/home/tukapontas/harappa-cockpit \
  .venv/bin/python3 apps/sns_pilot/schedule_posts.py \
  data/sns_pilot/drafts/YYYY-MM-DD.md [--dry-run]
```

**ドラフトMDフォーマット:**
```markdown
## 木曜日（04/23）- B: 既存共感
**画像**: DSC06138.JPG
**投稿時間**: 20:00
**本文**:
本文テキスト
**ハッシュタグ**: #タグ1 #タグ2
```

**処理フロー:**
1. MDを解析 → 投稿情報リストを生成
2. 各投稿について画像をFBにアップ → CDN URL取得
3. **IGスケジュール登録**: `schedule_ig_photo_via_server()` でサーバーキューに登録（job_idと予定時刻を返す）
4. FBスケジュール登録: `/photos` endpoint（動作確認済み）

---

## 5. Instagram API の制限事項と対応状況

| 機能 | API対応 | 備考 |
|------|---------|------|
| IG即時投稿 | ✅ | `instagram_content_publish` 権限で可能 |
| IGスケジュール投稿（API直接） | ❌ | `(#3) User must be on whitelist` エラー。Tech Provider申請が必要（Metaの大企業向け要件） |
| **IGスケジュール投稿（サーバー経由）** | **✅** | **IGスケジューラーサーバーで代替実装済み。`schedule_ig_photo_via_server()` を使用** |
| IGストーリーズ投稿 | ❌ | API対応なし |
| FB写真スケジュール | ✅ | `/photos` endpoint で動作確認済み |
| FB動画スケジュール | ✅ | `/videos` endpoint |

**スケジュール済みFB投稿の確認場所:**  
Meta Business SuiteのカレンダーUIには表示されない。  
→ Facebookページ → 「プロフェッショナルダッシュボード」→「スケジュール済みの投稿」で確認。

**IGスケジュールジョブの確認:**
```bash
curl -s -H "x-api-key: $IG_SCHEDULER_API_KEY" https://ig-api.harappa.monster/jobs
```

---

## 6. Google Sheets KPI連携

**スプレッドシートID:** `1NWU7FYGsMol18aHkrvpVzEB7dxIk2YvyTlb4eUD-Ycg`

| シート名 | 内容 |
|---------|------|
| 週次サマリー | 週別フォロワー数・リーチ・インプレッション |
| 投稿ログ | 投稿ごとのリーチ・保存・シェア・コメント |
| Reels KPI | 再生数・3秒視聴率・フォロワー外リーチ率 |

---

## 7. 今後の拡張候補

- IGスケジューラーでReels対応（現在はフィード写真のみ）
- LINE@ Messaging API連携（月1〜2回の告知配信）
- 週次レポートのSheets自動記録完全自動化（Phase 3）
- 投稿時間の最適化モニタリング（3ヶ月ローリング分析）
- IGスケジューラーのジョブ一覧をHMCから確認できるコマンド追加
