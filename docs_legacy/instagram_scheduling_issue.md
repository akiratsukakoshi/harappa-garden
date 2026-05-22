# Instagram予約投稿 API制限問題 - 調査記録

作成日: 2026-04-21  
作成者: Claude（harappa-cockpit開発セッション）

---

## 問題の概要

Meta Graph API を使ってInstagramの**予約投稿**（スケジュール投稿）を行おうとすると、以下のエラーが返り実行できない。

```json
{
  "error": {
    "message": "(#3) User must be on whitelist",
    "type": "OAuthException",
    "code": 3
  }
}
```

---

## 環境・構成

### Metaアプリ情報
- アプリ名: `harappa_hmc`
- アプリID: `1410473207782460`
- アプリ状態: **Live（公開済み）**
- 開発者ポータル: developers.facebook.com

### 使用しているID・トークン
| 変数名 | 値 | 説明 |
|--------|-----|------|
| `META_IG_ACCOUNT_ID` | `17841404542535531` | Instagram Business Account ID（username: harappa_daigaku） |
| `META_PAGE_ID` | `348855281822862` | Facebook Page ID（原っぱ大学） |
| `META_ACCESS_TOKEN` | type=PAGE のページアクセストークン | FB/IG操作の主トークン |
| `META_PAGE_ACCESS_TOKEN` | type=USER のユーザーアクセストークン | インサイト取得等 |

### 付与済み権限（`META_PAGE_ACCESS_TOKEN`で確認）
```
pages_show_list: granted
instagram_basic: granted
instagram_manage_insights: granted
instagram_content_publish: granted
pages_read_engagement: granted
pages_manage_posts: granted
```

---

## 実施した調査・試行

### 1. アプリをLiveモードに切り替え
- 当初アプリはDevelopmentモード
- プライバシーポリシーURL設定後、Liveモードへ切り替え
- **結果:** 即時投稿テストはOKになった。スケジュール投稿はまだNGのまま。

### 2. 即時投稿テスト（`published` パラメータなし）
```python
POST /17841404542535531/media
{
  "image_url": "https://...(公開URL)...",
  "caption": "テスト",
  "access_token": META_ACCESS_TOKEN
}
```
**結果: ✅ 成功（container_id が返ってくる）**

### 3. スケジュール投稿テスト（`published=false` + `scheduled_publish_time`）
```python
POST /17841404542535531/media
{
  "image_url": "https://...(公開URL)...",
  "caption": "テスト",
  "published": "false",
  "scheduled_publish_time": 1776942000,  # 2026-04-23 20:00 JST
  "access_token": META_ACCESS_TOKEN
}
```
**結果: ❌ `(#3) User must be on whitelist`**

- ページトークン・ユーザートークン両方で試行 → どちらもNG
- 画像URLをFacebook CDN / Wikipedia公開画像 / 各種公開URLで試行 → どちらもNG
- `published=false`でスケジュールなし（ドラフト状態）でも試行 → 同様にNG

### 4. App Review申請を試みる
開発者ポータルの「ユースケース」→「Instagramのコンテンツ公開」から高度なアクセス権申請を探した。

表示されたメッセージ：
```
To add a permission or feature to App Review, become a Tech Provider.
Tech Providers have the ability to request higher access levels to all 
available permissions and features through App Review.

To qualify as a Tech Provider, you must complete access verification. 
Be aware that this status also involves additional reviews and stricter 
data access requirements to ensure data security.

This decision cannot be reversed after you've been identified as a Tech Provider.
```

**結果: ❌ Tech Provider申請が必要**

Tech Providerとは「他のビジネスのデータにアクセスするサードパーティアプリ」向けの認定で、自社アカウントのみを扱う内部ツールには過剰な要件。ビジネス認証・アクセス認証・アプリレビューの3ステップが必要で、不可逆な申請となる。

---

## 現状の結論

| 機能 | 状態 | 備考 |
|------|------|------|
| IG即時投稿 | ✅ 可能 | `instagram_content_publish` 権限で動作 |
| IGスケジュール投稿 | ❌ 不可 | Tech Provider申請（大企業向け）が必要 |
| IGストーリーズ | ❌ 不可 | API自体が未対応 |
| FB写真スケジュール | ✅ 可能 | `/photos` endpointで動作確認済み |

### 現行の回避策
- **Facebook:** Meta Graph API `/photos` endpoint でスケジュール投稿が自動化済み
- **Instagram:** Instagram公式アプリから手動スケジュール（詳細設定 → この投稿をスケジュールする）

---

## セカンドオピニオンで確認したいこと

1. **Tech Provider以外にIGスケジュール投稿を実現する方法はあるか？**
   - 例: Marketing API経由、別エンドポイント、undocumentedなパラメータ等

2. **`instagram_content_publish` でスケジュール投稿が使えるのはどのような条件か？**
   - 内部ツール（自社アカウントのみ）でも不可なのか？
   - アプリの種類（Consumer/Business/None）によって変わるか？

3. **即時投稿を時刻通りに実行する現実的な代替アーキテクチャは何か？**
   - サーバーレス（AWS Lambda / GCP Cloud Functions）でのcron実行
   - Meta公式ツール（Creator Studio等）のAPI的な操作方法
   - その他

4. **Business Manager System User経由でスケジュール投稿できるケースはあるか？**

---

## 参考: 実装済みコード

**スケジューリングスクリプト:** `apps/sns_pilot/schedule_posts.py`  
**Meta APIクライアント:** `apps/sns_pilot/meta_client.py`  
**技術仕様書:** `docs/specs/sns_pilot.md`
