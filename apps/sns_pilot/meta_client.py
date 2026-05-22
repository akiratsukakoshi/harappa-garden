"""
Meta Graph API クライアント
- Instagram Business Account への投稿スケジューリング
- Facebook Page への投稿スケジューリング
- Insights データ取得
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from modules.utils import setup_logger

load_dotenv()
logger = setup_logger("MetaClient")

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class MetaClient:
    def __init__(self):
        self.access_token = os.environ.get("META_ACCESS_TOKEN")
        self.ig_account_id = os.environ.get("META_IG_ACCOUNT_ID")
        self.page_id = os.environ.get("META_PAGE_ID")

        if not all([self.access_token, self.ig_account_id, self.page_id]):
            raise EnvironmentError(
                "META_ACCESS_TOKEN / META_IG_ACCOUNT_ID / META_PAGE_ID が .env に未設定です。"
                "セットアップ手順: docs/sns_pilot_setup.md を参照してください。"
            )

    def _get(self, path, params=None, token=None):
        params = params or {}
        params["access_token"] = token or self.access_token
        resp = requests.get(f"{GRAPH_API_BASE}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, data=None, token=None):
        data = data or {}
        data["access_token"] = token or self.access_token
        resp = requests.post(f"{GRAPH_API_BASE}{path}", data=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_page_access_token(self) -> str:
        """ページアクセストークンを返す。META_ACCESS_TOKEN はすでにページトークン。"""
        return self.access_token

    # ──────────────────────────────────────────────
    # Facebook: 画像を一時アップロードして公開URLを取得
    # （Instagram Graph APIは公開URLが必須のため）
    # ──────────────────────────────────────────────

    def upload_photo_for_url(self, image_path: str) -> str:
        """
        画像をFacebookページに非公開でアップロードし、CDN URLを返す。
        返り値のURLをInstagramのimage_urlに使用する。
        """
        logger.info(f"FB一時アップロード: {image_path}")
        page_token = self.get_page_access_token()
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API_BASE}/{self.page_id}/photos",
                data={
                    "published": "false",
                    "access_token": page_token,
                },
                files={"source": f},
                timeout=60,
            )
        if not resp.ok:
            logger.error(f"FB写真アップロードエラー詳細: {resp.text}")
        resp.raise_for_status()
        photo_id = resp.json()["id"]
        logger.info(f"FB一時アップロード完了: photo_id={photo_id}")

        # CDN URLを取得
        url_resp = self._get(f"/{photo_id}", {"fields": "images"})
        images = url_resp.get("images", [])
        if not images:
            raise RuntimeError(f"画像URLの取得に失敗しました: photo_id={photo_id}")

        # 最大解像度のURLを返す
        best = max(images, key=lambda x: x.get("width", 0))
        cdn_url = best["source"]
        logger.info(f"CDN URL取得: {cdn_url[:80]}...")
        return cdn_url

    # ──────────────────────────────────────────────
    # Instagram: 写真投稿スケジュール
    # ──────────────────────────────────────────────

    def schedule_ig_photo_via_server(self, image_url: str, caption: str, publish_at: datetime) -> str:
        """
        クラウドサーバーのキューにIG写真投稿を登録する。
        Meta Graph APIのスケジュール機能（Tech Provider限定）の代替。
        image_url: FBにアップ済みのCDN URL（upload_photo_for_url()の戻り値）
        """
        api_url = os.environ.get("IG_SCHEDULER_API_URL")
        api_key = os.environ.get("IG_SCHEDULER_API_KEY")
        if not api_url or not api_key:
            raise EnvironmentError(
                "IG_SCHEDULER_API_URL / IG_SCHEDULER_API_KEY が .env に未設定です。"
            )
        resp = requests.post(
            f"{api_url}/schedule",
            json={
                "platform": "ig_photo",
                "image_url": image_url,
                "caption": caption,
                "publish_at": publish_at.isoformat(),
            },
            headers={"x-api-key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(
            f"IGサーバー予約完了: job_id={result['job_id']}, 投稿予定={result['publish_at_jst']}"
        )
        return str(result["job_id"])

    def schedule_ig_photo(self, image_url: str, caption: str, publish_at: datetime) -> str:
        """
        Instagramフィード写真投稿を予約する。
        ※ Meta側の制限（Tech Provider申請が必要）のため現在は動作しない。
           schedule_ig_photo_via_server() を使用すること。
        image_url: 公開アクセス可能な画像URL（Google Drive公開リンク等）
        publish_at: 投稿予定時刻（JST datetime → UTCに変換して送信）
        返り値: media container ID
        """
        unix_ts = int(publish_at.timestamp())
        logger.info(f"IG写真コンテナ作成: {publish_at.strftime('%Y-%m-%d %H:%M')} JST")

        result = self._post(f"/{self.ig_account_id}/media", {
            "image_url": image_url,
            "caption": caption,
            "published": "false",
            "scheduled_publish_time": unix_ts,
        })
        container_id = result["id"]

        # コンテナを予約キューに登録
        publish_result = self._post(f"/{self.ig_account_id}/media_publish", {
            "creation_id": container_id,
        })
        logger.info(f"IG写真予約完了: container={container_id}, post={publish_result.get('id')}")
        return publish_result.get("id", container_id)

    def schedule_ig_carousel(self, image_urls: list[str], caption: str, publish_at: datetime) -> str:
        """
        Instagram カルーセル（複数写真）投稿を予約する。
        image_urls: 公開アクセス可能な画像URLのリスト（upload_photo_for_url()で取得）
        ※ scheduled_publish_time は Tech Provider 申請が必要。
           schedule_ig_carousel_via_server() の利用を推奨。
        """
        unix_ts = int(publish_at.timestamp())
        logger.info(f"IGカルーセルコンテナ作成: {len(image_urls)}枚, {publish_at.strftime('%Y-%m-%d %H:%M')} JST")

        # Step1: 各画像のカルーセルアイテムコンテナを作成
        children = []
        for url in image_urls:
            result = self._post(f"/{self.ig_account_id}/media", {
                "image_url": url,
                "is_carousel_item": "true",
            })
            children.append(result["id"])
            logger.info(f"  カルーセルアイテム作成: {result['id']}")

        # Step2: カルーセルコンテナを作成
        result = self._post(f"/{self.ig_account_id}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "published": "false",
            "scheduled_publish_time": unix_ts,
        })
        container_id = result["id"]

        # Step3: 予約キューに登録
        publish_result = self._post(f"/{self.ig_account_id}/media_publish", {
            "creation_id": container_id,
        })
        logger.info(f"IGカルーセル予約完了: container={container_id}, post={publish_result.get('id')}")
        return publish_result.get("id", container_id)

    def schedule_ig_carousel_via_server(self, image_urls: list[str], caption: str, publish_at: datetime) -> str:
        """
        カルーセル投稿をスケジューラーサーバー経由で予約する。
        schedule_ig_photo_via_server() のカルーセル版。
        """
        api_url = os.environ.get("IG_SCHEDULER_API_URL")
        api_key = os.environ.get("IG_SCHEDULER_API_KEY")
        if not api_url or not api_key:
            raise EnvironmentError(
                "IG_SCHEDULER_API_URL / IG_SCHEDULER_API_KEY が .env に未設定です。"
            )
        resp = requests.post(
            f"{api_url}/schedule",
            json={
                "platform": "ig_carousel",
                "image_urls": image_urls,
                "caption": caption,
                "publish_at": publish_at.isoformat(),
            },
            headers={"x-api-key": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(
            f"IGカルーセルサーバー予約完了: job_id={result['job_id']}, 投稿予定={result['publish_at_jst']}"
        )
        return str(result["job_id"])

    def schedule_ig_reel(self, video_url: str, caption: str, publish_at: datetime) -> str:
        """
        Instagram Reels 投稿を予約する。
        video_url: 公開アクセス可能な動画URL
        """
        unix_ts = int(publish_at.timestamp())
        logger.info(f"IG Reelsコンテナ作成: {publish_at.strftime('%Y-%m-%d %H:%M')} JST")

        result = self._post(f"/{self.ig_account_id}/media", {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "published": "false",
            "scheduled_publish_time": unix_ts,
        })
        container_id = result["id"]

        publish_result = self._post(f"/{self.ig_account_id}/media_publish", {
            "creation_id": container_id,
        })
        logger.info(f"IG Reels予約完了: container={container_id}, post={publish_result.get('id')}")
        return publish_result.get("id", container_id)

    # ──────────────────────────────────────────────
    # Facebook: 写真投稿スケジュール
    # ──────────────────────────────────────────────

    def schedule_fb_photo(self, image_path: str, caption: str, publish_at: datetime) -> str:
        """
        Facebookページへ写真投稿を予約する（バイナリアップロード）。
        image_path: ローカルファイルパス
        """
        unix_ts = int(publish_at.timestamp())
        logger.info(f"FB写真予約: {publish_at.strftime('%Y-%m-%d %H:%M')} JST")
        page_token = self.get_page_access_token()

        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API_BASE}/{self.page_id}/photos",
                data={
                    "caption": caption,
                    "published": "false",
                    "scheduled_publish_time": unix_ts,
                    "access_token": page_token,
                },
                files={"source": f},
                timeout=60,
            )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"FB写真予約完了: post_id={result.get('id')}")
        return result.get("id", "")

    def schedule_fb_video(self, video_path: str, caption: str, publish_at: datetime) -> str:
        """
        FaceookページへReels/動画投稿を予約する。
        """
        unix_ts = int(publish_at.timestamp())
        logger.info(f"FB動画予約: {publish_at.strftime('%Y-%m-%d %H:%M')} JST")
        page_token = self.get_page_access_token()

        with open(video_path, "rb") as f:
            resp = requests.post(
                f"{GRAPH_API_BASE}/{self.page_id}/videos",
                data={
                    "description": caption,
                    "published": "false",
                    "scheduled_publish_time": unix_ts,
                    "access_token": page_token,
                },
                files={"source": f},
                timeout=120,
            )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"FB動画予約完了: video_id={result.get('id')}")
        return result.get("id", "")

    # ──────────────────────────────────────────────
    # Insights 取得
    # ──────────────────────────────────────────────

    def get_recent_posts(self, limit: int = 10) -> list[dict]:
        """直近の投稿一覧を取得（IG）。like_count・comments_count も含む。"""
        result = self._get(
            f"/{self.ig_account_id}/media",
            {"fields": "id,caption,timestamp,media_type,permalink,like_count,comments_count", "limit": limit},
        )
        return result.get("data", [])

    def get_post_insights(self, media_id: str) -> dict:
        """
        投稿単位のインサイトを取得。
        返り値例: {"reach": 1200, "saved": 45, "shares": 12, "comments_count": 8,
                   "impressions": 1500, "plays": None}
        """
        metrics = "reach,saved,shares,comments"
        try:
            result = self._get(f"/{media_id}/insights", {"metric": metrics})
            data = {item["name"]: item["values"][0]["value"] for item in result.get("data", [])}
        except Exception as e:
            logger.warning(f"投稿 {media_id} のインサイト取得失敗: {e}")
            data = {}

        # Reels用: video_views（v22以降はこちら）
        try:
            reels_result = self._get(f"/{media_id}/insights", {
                "metric": "video_views"
            })
            for item in reels_result.get("data", []):
                data[item["name"]] = item["values"][0]["value"]
        except Exception:
            pass

        return data

    def get_account_insights(self, days: int = 7) -> dict:
        """
        アカウント全体のインサイトを取得（フォロワー数・リーチ等）。
        """
        result = self._get(
            f"/{self.ig_account_id}/insights",
            {
                "metric": "reach,follower_count",
                "period": "day",
                "since": int((datetime.now().timestamp()) - days * 86400),
                "until": int(datetime.now().timestamp()),
            },
        )
        summary = {}
        for metric in result.get("data", []):
            name = metric["name"]
            values = metric.get("values", [])
            summary[name] = sum(v["value"] for v in values)
        return summary

    def get_follower_count(self) -> int:
        """現在のフォロワー数を取得"""
        result = self._get(f"/{self.ig_account_id}", {"fields": "followers_count"})
        return result.get("followers_count", 0)
