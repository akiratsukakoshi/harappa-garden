# Meta Graph API SNS自動投稿 実装ガイド

> **このドキュメントはAIエージェントが読み込んで実装できることを想定した技術ガイドです。**  
> 対象: Meta Businessアカウント取得済み、素材自動生成済みで投稿予約の自動化を目指す方  
> 作成日: 2026-04-26

---

## 概要と制限事項（最初に必読）

### できること / できないこと

| 機能 | 対応 | 備考 |
|------|------|------|
| Facebook 写真投稿スケジュール | ✅ | `/photos` endpoint で動作 |
| Facebook 動画投稿スケジュール | ✅ | `/videos` endpoint で動作 |
| **Instagram 写真即時投稿** | ✅ | `instagram_content_publish` 権限で動作 |
| Instagram 写真スケジュール投稿（API直接） | ❌ | **Tech Provider申請が必要（詳細後述）** |
| Instagram ストーリーズ | ❌ | API未対応 |

### IGスケジュール投稿の制限（重要）

Meta Graph APIでInstagramの予約投稿（`published=false` + `scheduled_publish_time`）を使おうとすると以下のエラーが返る:

```json
{"error": {"message": "(#3) User must be on whitelist", "type": "OAuthException", "code": 3}}
```

これは **Tech Provider申請（Metaの大企業向けプログラム）が必要** なためで、自社アカウントのみを管理する内部ツールでは取得できない。

**解決策: 自前のスケジューラーサーバーを立てる**

- IG用: クラウドサーバー（VPS/Docker）またはサーバーレス（AWS Lambda等）上にスケジューラーを実装し、指定時刻に即時投稿APIを呼び出す
- FB用: Meta APIが直接スケジュール投稿をサポートするため、追加サーバー不要

---

## Part 1: Meta API セットアップ（FB/IG共通）

### 1-1. 前提条件の確認

以下がすべて揃っているか確認する:

- [ ] **Instagramビジネスアカウント**（個人アカウントは不可）
- [ ] **Facebookページ**（個人のFBアカウントではない「ページ」）
- [ ] IGとFBページが紐付いていること（IG設定 → 「リンクされたFacebookページ」で確認）
- [ ] Meta for Developersアカウント（developers.facebook.com でのログイン）
- [ ] Meta Business Manager（business.facebook.com）へのアクセス

### 1-2. Meta Developerアプリの作成

1. [developers.facebook.com/apps](https://developers.facebook.com/apps/) にアクセス
2. 「アプリを作成」をクリック
3. アプリタイプ: **「ビジネス」** を選択（ConsumerやNoneではない）
4. アプリ名・連絡先メールを入力して作成

作成後、アプリダッシュボードで以下を確認・メモ:
- **アプリID**（App ID）
- **アプリシークレット**（App Secret）← 設定 → ベーシック に表示

### 1-3. 必要な権限（Permissions）の追加

アプリダッシュボード → 「ユースケース」 または 「アクセス許可」から以下を追加:

| 権限 | 用途 |
|------|------|
| `instagram_basic` | IGアカウント情報の読み取り |
| `instagram_content_publish` | IG投稿の作成・公開 |
| `instagram_manage_insights` | IGインサイト取得（任意） |
| `pages_read_engagement` | FBページ情報の読み取り |
| `pages_manage_posts` | FBページへの投稿管理 |

### 1-4. アプリをLiveモードに変更（必須）

**Developmentモードのままでは `instagram_content_publish` が動作しない。**

1. アプリダッシュボード → 上部のトグルスイッチ「開発中」→「ライブ」に切り替え
2. プライバシーポリシーURLの入力を求められる場合は設定する（簡単なものでOK）
3. Liveモードになったことを確認

### 1-5. アクセストークンの取得

#### ステップA: Graph API Explorerで短期トークンを取得

1. [Graph API Explorer](https://developers.facebook.com/tools/explorer/) にアクセス
2. 右上のドロップダウンで作成したアプリを選択
3. 「アクセス許可を追加」で上記5つの権限をすべて選択
4. 「ユーザーアクセストークンを生成」をクリック → Facebook/Instagramアカウントで認証
5. 表示されたトークンをコピー（これは短期トークン、有効期限約1時間）

#### ステップB: 長期トークン（Long-Lived Token）に変換（有効期限60日）

以下のURLにブラウザでアクセス（各値を置換）:

```
https://graph.facebook.com/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=<APP_ID>
  &client_secret=<APP_SECRET>
  &fb_exchange_token=<SHORT_TERM_TOKEN>
```

返ってくるJSONの `access_token` が長期ユーザートークン。

#### ステップC: ページアクセストークンの取得

Instagramへの投稿にはページアクセストークン（type=PAGE）が必要。

```
https://graph.facebook.com/me/accounts?access_token=<LONG_LIVED_USER_TOKEN>
```

レスポンス例:
```json
{
  "data": [{
    "access_token": "EAAxxxxxxx...",   ← これがページアクセストークン
    "id": "348855281822862",           ← Facebook Page ID
    "name": "原っぱ大学"
  }]
}
```

**ページアクセストークンには有効期限がない**（ユーザーがアプリを削除しない限り）。

> **注意**: `META_ACCESS_TOKEN` としてセットするのはこのページアクセストークン（type=PAGE）。
> 長期ユーザートークンではない。

### 1-6. 必要なIDの確認と取得

#### Facebook Page ID
上記 `/me/accounts` のレスポンスの `id` フィールド。

#### Instagram Business Account ID
```
https://graph.facebook.com/<PAGE_ID>?fields=instagram_business_account&access_token=<PAGE_ACCESS_TOKEN>
```

レスポンス:
```json
{
  "instagram_business_account": {"id": "17841404542535531"},  ← META_IG_ACCOUNT_ID
  "id": "348855281822862"
}
```

> **よくある混同**: Business Manager ID（business.facebook.comのURL末尾の数字）とは別物。
> IG Account IDは`178...`のような長い数字。

### 1-7. 環境変数への設定

```bash
# .env
META_ACCESS_TOKEN=<ページアクセストークン>    # type=PAGE, 有効期限なし
META_IG_ACCOUNT_ID=<IG Business Account ID>  # 例: 17841404542535531
META_PAGE_ID=<Facebook Page ID>              # 例: 348855281822862
```

### 1-8. トークン有効期限の確認方法

```
https://graph.facebook.com/debug_token?input_token=<TOKEN>&access_token=<TOKEN>
```

長期ユーザートークンは60日で失効するが、ページアクセストークンは失効しない。
月1回確認を推奨。

---

## Part 2: Facebook スケジュール投稿の実装

FBはMeta APIが直接スケジュール投稿をサポートしているため、サーバー不要。

### 2-1. 写真のスケジュール投稿

```python
import requests
from datetime import datetime
import pytz

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
JST = pytz.timezone("Asia/Tokyo")

def schedule_fb_photo(image_path: str, caption: str, publish_at: datetime,
                      page_id: str, page_access_token: str) -> str:
    """
    Facebookページへ写真をスケジュール投稿する。
    publish_at: タイムゾーン付きdatetime（JSTで渡してもUTCで渡しても可）
    """
    unix_ts = int(publish_at.timestamp())

    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/photos",
            data={
                "caption": caption,
                "published": "false",          # スケジュール投稿
                "scheduled_publish_time": unix_ts,
                "access_token": page_access_token,
            },
            files={"source": f},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json().get("id", "")
```

### 2-2. 動画のスケジュール投稿

```python
def schedule_fb_video(video_path: str, caption: str, publish_at: datetime,
                      page_id: str, page_access_token: str) -> str:
    unix_ts = int(publish_at.timestamp())

    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/videos",
            data={
                "description": caption,
                "published": "false",
                "scheduled_publish_time": unix_ts,
                "access_token": page_access_token,
            },
            files={"source": f},
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json().get("id", "")
```

### 2-3. スケジュール済み投稿の確認場所

Meta Business SuiteのカレンダーUIには**表示されない**。確認方法:

- Facebookページ → 「プロフェッショナルダッシュボード」 → 「スケジュール済みの投稿」

---

## Part 3: Instagram スケジュール投稿の実装

### 3-1. 根本的な制約の再確認

IG APIの `scheduled_publish_time` パラメータはTech Provider申請が必要で、実質使用不可。  
**唯一の実用的な解決策は「指定時刻に即時投稿APIを呼び出すスケジューラーを自前で実装する」こと。**

### 3-2. IG即時投稿の仕組み

IG即時投稿は2ステップ:

1. **メディアコンテナ作成**: 画像URLとキャプションを送り、`container_id` を受け取る
2. **コンテナを公開**: `container_id` を `media_publish` に送り、実際に投稿する

```python
def publish_ig_photo_now(image_url: str, caption: str,
                         ig_account_id: str, access_token: str) -> str:
    """
    image_url: 公開アクセス可能なURL（ローカルファイル不可）
    """
    # Step 1: コンテナ作成
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]

    # Step 2: 公開
    resp2 = requests.post(
        f"{GRAPH_API_BASE}/{ig_account_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    resp2.raise_for_status()
    return resp2.json()["id"]
```

> **image_urlの制約**: IG APIはローカルファイルを受け付けない。公開HTTPSのURLが必要。  
> FBページに非公開アップロード → CDN URLを取得する方法が確実（後述）。

### 3-3. 画像の公開URL取得方法（FBページ経由）

ローカル画像をFBページに非公開アップロードしてCDN URLを取得する方法:

```python
def upload_photo_for_url(image_path: str, page_id: str, page_access_token: str) -> str:
    """
    画像をFBに非公開アップロードし、CDN URLを返す。
    返り値をIG投稿の image_url として使用する。
    """
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_API_BASE}/{page_id}/photos",
            data={"published": "false", "access_token": page_access_token},
            files={"source": f},
            timeout=60,
        )
    resp.raise_for_status()
    photo_id = resp.json()["id"]

    # CDN URLを取得
    url_resp = requests.get(
        f"{GRAPH_API_BASE}/{photo_id}",
        params={"fields": "images", "access_token": page_access_token},
    )
    url_resp.raise_for_status()
    images = url_resp.json().get("images", [])
    best = max(images, key=lambda x: x.get("width", 0))
    return best["source"]
```

> CDN URLの有効期限は長く（数週間〜数ヶ月）、週次スケジューリングには十分。

### 3-4. IGスケジューラーの実装選択肢

スケジューラーは以下3パターンから環境に合わせて選択:

| パターン | 向いているケース | 備考 |
|---------|----------------|------|
| A. VPS/クラウドサーバー (Docker) | すでにVPS/クラウドを運用している | 本ガイドの実装例はこれ |
| B. サーバーレス (AWS Lambda + EventBridge等) | クラウドを新規に利用する | コールドスタートに注意 |
| C. ローカルPC (cron + 常時起動) | 個人用途・テスト用 | PC電源OFFで失敗するリスクあり |

---

## Part 4: IGスケジューラー実装（VPS/Docker版）

### 4-1. アーキテクチャ

```
[HMCローカル / 自動化スクリプト]
    │ POST /schedule (APIキー認証)
    ▼
[クラウドサーバー: FastAPI + APScheduler]
    │ SQLiteにジョブ登録
    │ 1分間隔でワーカー実行
    ▼
[Meta Graph API: IG即時投稿]
```

### 4-2. サーバー要件

- Docker + docker-compose が使えるVPS/クラウドサーバー
- HTTPSが使えるドメインまたはサブドメイン（APIキーを平文で送らないため）
- ポート443が外部からアクセス可能

### 4-3. `app.py` — スケジューラーサーバー本体

```python
"""
Instagram 予約投稿スケジューラー API
FastAPI + APScheduler + SQLite によるジョブキュー管理。
Meta Graph APIのスケジュール機能（Tech Provider限定）の代替実装。
"""
import os
import sqlite3
import requests
import smtplib
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("ig_scheduler")

# ── 設定 ──────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "/data/scheduler.db")
API_KEY = os.environ.get("SCHEDULER_API_KEY", "")
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_IG_ACCOUNT_ID = os.environ.get("META_IG_ACCOUNT_ID", "")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
NOTIFY_TO = os.environ.get("NOTIFY_TO", "")


# ── DB ────────────────────────────────────────────────────────────────
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            platform    TEXT NOT NULL,
            image_url   TEXT NOT NULL,
            caption     TEXT NOT NULL,
            publish_at  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            post_id     TEXT,
            error_msg   TEXT,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        )
    """)
    conn.commit()
    conn.close()


# ── Meta API ──────────────────────────────────────────────────────────
def _publish_ig_photo(image_url: str, caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{META_IG_ACCOUNT_ID}/media",
        data={"image_url": image_url, "caption": caption, "access_token": META_ACCESS_TOKEN},
        timeout=30,
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]

    resp2 = requests.post(
        f"{GRAPH_API_BASE}/{META_IG_ACCOUNT_ID}/media_publish",
        data={"creation_id": container_id, "access_token": META_ACCESS_TOKEN},
        timeout=30,
    )
    resp2.raise_for_status()
    return resp2.json()["id"]


# ── メール通知 ────────────────────────────────────────────────────────
def send_failure_email(job_id: int, publish_at: str, error: str):
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP未設定のためメール通知をスキップ")
        return
    try:
        body = (
            f"IGスケジューラーで投稿エラーが発生しました。\n\n"
            f"ジョブID: {job_id}\n投稿予定: {publish_at}\nエラー: {error}\n\n"
            f"手動投稿が必要です。"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"[IGスケジューラー] 投稿失敗 job_id={job_id}"
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, [NOTIFY_TO], msg.as_string())
    except Exception as e:
        logger.error(f"メール送信失敗: {e}")


# ── ワーカー（1分間隔で実行） ─────────────────────────────────────────
def run_worker():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_conn()
    pending = conn.execute(
        "SELECT * FROM jobs WHERE status='pending' AND publish_at <= ?", (now,)
    ).fetchall()

    if not pending:
        conn.close()
        return

    for row in pending:
        job = dict(row)
        try:
            if job["platform"] == "ig_photo":
                post_id = _publish_ig_photo(job["image_url"], job["caption"])
            else:
                raise NotImplementedError(f"未対応platform: {job['platform']}")

            conn.execute(
                "UPDATE jobs SET status='published', post_id=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
                (post_id, job["id"]),
            )
            conn.commit()
            logger.info(f"投稿完了: job_id={job['id']} post_id={post_id}")

        except Exception as e:
            error_msg = str(e)
            conn.execute(
                "UPDATE jobs SET status='failed', error_msg=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
                (error_msg, job["id"]),
            )
            conn.commit()
            logger.error(f"投稿失敗: job_id={job['id']}: {error_msg}")
            send_failure_email(job["id"], job["publish_at"], error_msg)

    conn.close()


# ── FastAPI ───────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(run_worker, "interval", minutes=1, id="worker", max_instances=1)
    scheduler.start()
    logger.info("スケジューラー起動 (1分間隔)")
    yield
    scheduler.shutdown()


app = FastAPI(title="IG Scheduler", lifespan=lifespan)
JST = timezone(timedelta(hours=9))


def verify_key(x_api_key: str = Header()):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


class JobIn(BaseModel):
    platform: str    # 'ig_photo'
    image_url: str
    caption: str
    publish_at: str  # ISO 8601 with timezone e.g. "2026-04-29T20:00:00+09:00"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "time_jst": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
    }


@app.post("/schedule", dependencies=[Depends(verify_key)])
def create_job(body: JobIn):
    if body.platform not in ("ig_photo",):
        raise HTTPException(400, f"platform '{body.platform}' は未対応です（ig_photo のみ対応）")

    try:
        dt = datetime.fromisoformat(body.publish_at)
    except ValueError:
        raise HTTPException(400, "publish_at の形式が不正です（例: 2026-04-29T20:00:00+09:00）")

    if dt.tzinfo is None:
        raise HTTPException(400, "publish_at にタイムゾーン情報が必要です（例: +09:00）")

    dt_utc = dt.astimezone(timezone.utc)
    if dt_utc < datetime.now(timezone.utc) - timedelta(minutes=5):
        raise HTTPException(400, "publish_at が過去の時刻です")

    publish_at_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO jobs (platform, image_url, caption, publish_at) VALUES (?,?,?,?)",
        (body.platform, body.image_url, body.caption, publish_at_str),
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()

    dt_jst = dt.astimezone(JST)
    return {
        "job_id": job_id,
        "status": "scheduled",
        "platform": body.platform,
        "publish_at_jst": dt_jst.strftime("%Y-%m-%d %H:%M JST"),
        "publish_at_utc": publish_at_str,
    }


@app.get("/jobs", dependencies=[Depends(verify_key)])
def list_jobs(status: str = None, limit: int = 20):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status=? ORDER BY publish_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY publish_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.delete("/jobs/{job_id}", dependencies=[Depends(verify_key)])
def cancel_job(job_id: int):
    conn = get_conn()
    result = conn.execute(
        "UPDATE jobs SET status='cancelled', updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') "
        "WHERE id=? AND status='pending'",
        (job_id,),
    )
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(404, "ジョブが見つからないか、すでに処理済みです")
    return {"status": "cancelled", "job_id": job_id}
```

### 4-4. `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
```

### 4-5. `requirements.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
apscheduler>=3.10.0
requests>=2.31.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### 4-6. `docker-compose.yml`

**Nginx Proxy Manager (NPM) を使う場合**（推奨・HTTPS化が容易）:

```yaml
services:
  ig_scheduler:
    build: .
    container_name: ig_scheduler
    restart: unless-stopped
    ports:
      - "127.0.0.1:8100:8000"   # ローカルホスト経由でNPMがプロキシする
    volumes:
      - scheduler_data:/data
      - ./.env:/app/.env:ro
    env_file: .env
    networks:
      - proxy_net

volumes:
  scheduler_data:

networks:
  proxy_net:
    external: true
    name: proxy-manager_default   # NPMのネットワーク名に合わせる
```

**NPMなしで直接公開する場合**（簡易構成）:

```yaml
services:
  ig_scheduler:
    build: .
    container_name: ig_scheduler
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - scheduler_data:/data
      - ./.env:/app/.env:ro
    env_file: .env

volumes:
  scheduler_data:
```

> **Xserverの場合**: `docker-compose`（旧バイナリ）は使えるが `docker compose`（プラグイン）は使えない場合がある。`docker-compose --version` で確認すること。

### 4-7. `.env`（サーバー側）

```bash
# Meta API
META_ACCESS_TOKEN=<ページアクセストークン>
META_IG_ACCOUNT_ID=<IG Business Account ID>

# スケジューラー認証
SCHEDULER_API_KEY=<ランダムな長い文字列>  # openssl rand -hex 32 で生成推奨

# SQLite
DB_PATH=/data/scheduler.db

# 投稿失敗時のメール通知（任意）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<Gmailアドレス>
SMTP_PASS=<Gmailアプリパスワード>  # Googleアカウント → セキュリティ → アプリパスワード
NOTIFY_TO=<通知先メール>
```

### 4-8. HTTPS設定（Nginx Proxy Manager 使用）

1. **DNS設定**: サーバーのIPアドレス（例: `162.43.40.86`）に `A` レコードを追加
   - ホスト名: `ig-api`（フルドメインではなくサブドメイン部分のみ入力する場合が多い）
   - TTL: 3600（デフォルト）

2. **NPM管理画面**（ポート81）でプロキシホスト追加:
   - Domain Names: `ig-api.yourdomain.com`
   - Forward Hostname: `ig_scheduler`（コンテナ名）
   - Forward Port: `8000`
   - SSL: Let's Encrypt でSSL証明書を取得
     → DNSが完全に伝播してからSSL設定を行うこと（伝播前はエラーになる）
     → `dig A ig-api.yourdomain.com +short` でIPが返ってきたら伝播完了

3. **ファイアウォール設定**: VPSのコントロールパネルでポート80・443が開いているか確認
   - NPM管理用ポート81は設定完了後に閉じることを推奨

### 4-9. デプロイ手順

```bash
# サーバーへファイルをコピー
rsync -av --exclude='.env' ./ig_scheduler_files/ user@server:/path/to/ig_scheduler/

# サーバー上で .env を作成（初回のみ）
ssh user@server
nano /path/to/ig_scheduler/.env
# (上記 .env の内容を入力)

# コンテナ起動
cd /path/to/ig_scheduler
docker-compose up -d --build

# ヘルスチェック
curl https://ig-api.yourdomain.com/health
```

### 4-10. APIキー生成方法

```bash
openssl rand -hex 32
# 例: 7c04674670b482f1d22e850b4d8983efaa5a2ed6a4384bcac1015cc4fb7802ba
```

---

## Part 5: クライアント側の実装

自動化スクリプト（HMC等）からスケジューラーサーバーを呼び出す実装:

### 5-1. クライアント側の環境変数

```bash
# .env（ローカルのスクリプト側）
IG_SCHEDULER_API_URL=https://ig-api.yourdomain.com
IG_SCHEDULER_API_KEY=<サーバー側のSCHEDULER_API_KEYと同じ値>
```

### 5-2. スケジューラーサーバーへの投稿登録

```python
import os
import requests
from datetime import datetime

def schedule_ig_photo_via_server(image_url: str, caption: str, publish_at: datetime) -> str:
    """
    image_url: 公開HTTPSのURL（upload_photo_for_url()の戻り値等）
    publish_at: タイムゾーン付きdatetime（JST等、何でも可 → サーバー側でUTCに変換）
    返り値: job_id（文字列）
    """
    api_url = os.environ.get("IG_SCHEDULER_API_URL")
    api_key = os.environ.get("IG_SCHEDULER_API_KEY")

    resp = requests.post(
        f"{api_url}/schedule",
        json={
            "platform": "ig_photo",
            "image_url": image_url,
            "caption": caption,
            "publish_at": publish_at.isoformat(),  # タイムゾーン情報必須
        },
        headers={"x-api-key": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"IG予約完了: job_id={result['job_id']}, 投稿予定={result['publish_at_jst']}")
    return str(result["job_id"])
```

### 5-3. タイムゾーン処理の注意点

**`pytz` を使う場合の正しい書き方**:

```python
import pytz
from datetime import datetime

JST = pytz.timezone("Asia/Tokyo")

# ✅ 正しい: localize() を使う
publish_at = JST.localize(datetime(2026, 4, 29, 20, 0, 0))

# ❌ 誤り: tzinfo= で直接渡す（東京の歴史的LMT UTC+9:19が適用され19分ずれる）
publish_at = datetime(2026, 4, 29, 20, 0, 0, tzinfo=JST)
```

`timezone` を使う場合（pytz不要）:

```python
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
publish_at = datetime(2026, 4, 29, 20, 0, 0, tzinfo=JST)  # これはOK
```

### 5-4. ジョブの確認・キャンセル

```bash
# スケジュール済みジョブ一覧
curl -s -H "x-api-key: $IG_SCHEDULER_API_KEY" https://ig-api.yourdomain.com/jobs

# ステータスで絞り込み（pending/published/failed/cancelled）
curl -s -H "x-api-key: $IG_SCHEDULER_API_KEY" "https://ig-api.yourdomain.com/jobs?status=pending"

# ジョブキャンセル
curl -X DELETE -H "x-api-key: $IG_SCHEDULER_API_KEY" https://ig-api.yourdomain.com/jobs/<job_id>
```

---

## Part 6: サーバーレス版（AWS Lambda）の概要

VPSを持っていない場合のAWS Lambda + EventBridgeによる実装概要:

### 構成

```
[スクリプト] → [DynamoDB/RDS] にジョブ登録
[EventBridge cron] → 毎分 Lambda を起動
[Lambda] → DB から pending ジョブを取得 → IG即時投稿 → DB更新
```

### 注意点

- Lambda の最大実行時間: 15分（IG投稿は通常数秒なので問題なし）
- 毎分起動はコストがかかる。代替として5分間隔にし、投稿時刻の精度を±5分に許容するのも現実的
- コールドスタートによる遅延: VPS版より数秒遅れる可能性がある
- DynamoDB の TTL 機能を使って古いジョブを自動削除できる

---

## Part 7: トラブルシューティング

### `(#3) User must be on whitelist`

IGスケジュール投稿を試みた場合に発生。**解決策なし** — Tech Provider申請不可なため、本ガイドのスケジューラーサーバーを使用する。

### `(#200) Permissions error`

- アプリがDevelopmentモードになっている → Liveモードに変更
- 権限が不足している → Graph API Explorerで権限を追加して新しいトークンを取得

### `The user must be an administrator, editor, or moderator of the page`

- ページアクセストークンの取得に使ったユーザーがページの管理者でない
- `/me/accounts` でページトークンを再取得する

### 投稿はされているがFB Business Suiteのカレンダーに表示されない

正常動作。FB「プロフェッショナルダッシュボード」→「スケジュール済みの投稿」で確認する。

### IGスケジューラーコンテナが起動しない

```bash
# ログ確認
docker logs ig_scheduler

# よくある原因
# 1. .env ファイルが存在しない
# 2. SCHEDULER_API_KEY が空
# 3. /data ディレクトリへの書き込み権限がない
```

### SMTP設定: Gmailアプリパスワードの取得

通常のGmailパスワードではなくアプリパスワードが必要:

1. Googleアカウント → セキュリティ → 2段階認証を有効化
2. セキュリティ → アプリパスワード → アプリを選択（「メール」等）→ 生成
3. 生成された16文字のパスワードを `SMTP_PASS` に設定

> **注意**: `SMTP_PASS` にスペースが含まれる場合（例: `abcd efgh ijkl mnop`）、`sed` コマンドでの置換が難しい。`python3 -c "..."` でファイル書き換えする方が確実。

---

## まとめ: 最小実装チェックリスト

### Meta APIセットアップ
- [ ] Meta Developerアプリを「ビジネス」タイプで作成
- [ ] 5つの権限を追加
- [ ] アプリをLiveモードに変更
- [ ] ページアクセストークンを取得（`/me/accounts`経由）
- [ ] IG Account IDを取得（`/<PAGE_ID>?fields=instagram_business_account`）
- [ ] `.env` に `META_ACCESS_TOKEN`, `META_IG_ACCOUNT_ID`, `META_PAGE_ID` を設定

### Facebookスケジュール投稿
- [ ] `schedule_fb_photo()` を実装
- [ ] `published=false` + `scheduled_publish_time`（UNIXタイム）でPOST

### Instagramスケジュール投稿
- [ ] スケジューラーサーバーをVPS/クラウドにデプロイ（Docker推奨）
- [ ] HTTPS設定（Nginx Proxy Manager + Let's Encrypt 推奨）
- [ ] `SCHEDULER_API_KEY` を生成してサーバー `.env` に設定
- [ ] クライアント側 `.env` に `IG_SCHEDULER_API_URL`, `IG_SCHEDULER_API_KEY` を設定
- [ ] `schedule_ig_photo_via_server()` を実装
- [ ] ヘルスチェック: `curl https://ig-api.yourdomain.com/health`

---

*このガイドはMeta Graph API v21.0 (2026-04時点)の動作確認に基づいて作成されています。*  
*APIの仕様変更により内容が変わる可能性があります。*
