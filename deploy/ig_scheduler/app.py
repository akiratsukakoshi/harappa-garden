"""
Instagram 予約投稿スケジューラー API
Xserverクラウド (Docker) で稼働。HMCからPOSTで投稿データを受け取り、
指定時刻にMeta Graph APIで即時投稿する。
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

# ── 設定 ───────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "/data/scheduler.db")
API_KEY = os.environ.get("SCHEDULER_API_KEY", "")
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_IG_ACCOUNT_ID = os.environ.get("META_IG_ACCOUNT_ID", "")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
NOTIFY_TO = os.environ.get("NOTIFY_TO", "tukapontas@gmail.com")


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
    logger.info(f"DB初期化完了: {DB_PATH}")


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
            f"ジョブID: {job_id}\n"
            f"投稿予定: {publish_at}\n"
            f"エラー: {error}\n\n"
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
        logger.info(f"エラーメール送信: {NOTIFY_TO}")
    except Exception as e:
        logger.error(f"メール送信失敗: {e}")


# ── ワーカー（1分間隔で実行） ──────────────────────────────────────────
def run_worker():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_conn()
    pending = conn.execute(
        "SELECT * FROM jobs WHERE status='pending' AND publish_at <= ?", (now,)
    ).fetchall()

    if not pending:
        conn.close()
        return

    logger.info(f"処理対象: {len(pending)} 件")
    for row in pending:
        job = dict(row)
        logger.info(f"投稿開始: job_id={job['id']} platform={job['platform']}")
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
