"""
週次投稿スケジューリングスクリプト
使い方: python apps/sns_pilot/schedule_posts.py data/sns_pilot/drafts/2026-04-21.md

ドラフトMDを読み込み、Meta Graph APIで3本（火・木・土）を一括予約する。
IG写真投稿はGoogle Drive永久URLを経由（FB CDN URLは期限切れになるため使用不可）。FB投稿はバイナリ直接。
"""
import sys
import os
import re
import json
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apps.sns_pilot.meta_client import MetaClient
from apps.sns_pilot.drive_uploader import DriveUploader
from modules.utils import setup_logger

load_dotenv()
logger = setup_logger("SchedulePosts")

JST = pytz.timezone("Asia/Tokyo")

with open("apps/sns_pilot/config.json") as f:
    CONFIG = json.load(f)

IMAGES_DIR = CONFIG["images_dir"]
IMAGES_BASE = os.path.dirname(IMAGES_DIR)  # data/sns_pilot/images


def find_image(filename: str) -> str | None:
    """selected/ → candidates/ の順で画像ファイルを探す"""
    for subdir in ("selected", "candidates", "carry_over"):
        path = os.path.join(IMAGES_BASE, subdir, filename)
        if os.path.exists(path):
            return path
    # フルパス指定の場合
    if os.path.exists(filename):
        return filename
    return None


# ──────────────────────────────────────────────
# ドラフトMDパーサー
# ──────────────────────────────────────────────

def parse_draft(md_path: str) -> list[dict]:
    """
    ドラフトMDから投稿情報を抽出する。
    返り値: [
      { "weekday": "火", "date_str": "04/22", "purpose": "B",
        "format": "フィード", "image": "filename.jpg",
        "caption": "本文+ハッシュタグ", "hour": 20, "minute": 0 }
    ]
    """
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    # 人間修正版セクションがある場合はそちらを優先（旧ドラフト対応）
    if "HUMAN修正案" in content:
        content = content.split("HUMAN修正案")[1]

    posts = []
    # 新旧フォーマット両対応（## / ### で区切られている）
    blocks = re.split(r"\n#{2,3} ", content)
    for block in blocks[1:]:
        post = _parse_block(block)
        if post:
            posts.append(post)
    return posts


def _parse_block(block: str) -> dict | None:
    lines = block.strip().split("\n")
    header = lines[0]

    weekday_map = {"月曜日": "月", "火曜日": "火", "水曜日": "水", "木曜日": "木",
                   "金曜日": "金", "土曜日": "土", "日曜日": "日"}

    # 新フォーマット: "火曜日（04/22）- B: 既存共感"
    m = re.match(r"(.+?)（(\d{2}/\d{2})）.*?[-–]\s*(.+?):", header)
    if m:
        weekday_full, date_str, purpose_key = m.group(1), m.group(2), m.group(3).strip()
        weekday = weekday_map.get(weekday_full, weekday_full)
    else:
        # 旧フォーマット: "**2/11 (水) 【目的：A:新規・集客】**"
        m2 = re.match(r"\*{0,2}(\d{1,2})/(\d{1,2})\s*\((.)\)", header)
        if not m2:
            return None
        month, day = m2.group(1), m2.group(2)
        date_str = f"{int(month):02d}/{int(day):02d}"
        weekday = m2.group(3)
        purpose_match = re.search(r"【目的[：:]\s*([A-C])", header)
        purpose_key = purpose_match.group(1) if purpose_match else "B"

    fmt = "Reels" if "reels" in header.lower() or "リール" in header.lower() else "フィード"

    def extract(label):
        m = re.search(rf"\*\*{label}\*\*:\s*(.+)", block)
        return m.group(1).strip().strip("`") if m else ""

    # 画像パス（カルーセルは " / " 区切りで複数）
    raw_image = extract("画像") or extract("素材")
    images_list = []
    if raw_image:
        # 括弧内の注釈（candidates/ 等）を除去してから分割
        clean_image = re.sub(r"[（(][^）)]*[）)]", "", raw_image).strip()
        for part in re.split(r"\s+/\s+", clean_image):
            fname = re.split(r"[\s（(]", part.strip())[0].strip("`()")
            if fname and not fname.startswith("←") and "." in fname:
                images_list.append(fname)
    image = images_list[0] if images_list else ""
    time_str = extract("投稿時間")
    hour, minute = 20, 0
    if time_str:
        try:
            hour, minute = int(time_str.split(":")[0]), int(time_str.split(":")[1])
        except Exception:
            pass

    # 本文: 新フォーマット(**本文**:) / 旧フォーマット(**投稿案**:) 両対応
    body_m = (re.search(r"\*\*本文\*\*:\n([\s\S]+?)(?=\n\*\*|$)", block) or
              re.search(r"\*\*投稿案\*\*:\n([\s\S]+?)(?=\n\*\*|$)", block) or
              re.search(r"\*\*キャプション\*\*:\n([\s\S]+?)(?=\n\*\*|$)", block))
    tag_m = re.search(r"\*\*ハッシュタグ\*\*:\s*(.+)", block)

    body = body_m.group(1).strip() if body_m else ""
    tags = tag_m.group(1).strip() if tag_m else ""
    caption = f"{body}\n\n{tags}".strip() if tags else body

    if not caption:
        logger.warning(f"キャプションが見つかりません: {header}")
        return None

    return {
        "weekday": weekday,
        "date_str": date_str,
        "purpose": purpose_key,
        "format": fmt,
        "image": image,
        "images": images_list,
        "caption": caption,
        "hour": hour,
        "minute": minute,
    }


# ──────────────────────────────────────────────
# 投稿日時の計算（MDの日付文字列 → JST datetime）
# ──────────────────────────────────────────────

def resolve_publish_dt(date_str: str, hour: int, minute: int, base_year: int = None) -> datetime:
    """
    "04/22" + 20:00 → 2026-04-22 20:00 JST
    """
    year = base_year or datetime.now().year
    month, day = int(date_str.split("/")[0]), int(date_str.split("/")[1])
    dt = JST.localize(datetime(year, month, day, hour, minute))
    # 年をまたぐケース（12月→1月）
    if dt < datetime.now(JST) - timedelta(days=30):
        dt = JST.localize(datetime(year + 1, month, day, hour, minute))
    return dt


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def main(draft_path: str, dry_run: bool = False):
    logger.info(f"=== 週次投稿スケジューリング開始 ===")
    logger.info(f"ドラフト: {draft_path}")

    posts = parse_draft(draft_path)
    if not posts:
        logger.error("投稿データが見つかりませんでした。ドラフトMDの形式を確認してください。")
        return

    meta = MetaClient() if not dry_run else None
    drive = DriveUploader() if not dry_run else None
    base_year = datetime.now().year

    results = []
    for post in posts:
        publish_dt = resolve_publish_dt(post["date_str"], post["hour"], post["minute"], base_year)
        image_local = os.path.join(IMAGES_DIR, post["image"]) if post["image"] else None

        logger.info(f"\n--- {post['weekday']}曜日 ({post['date_str']}) {post['format']} [{post['purpose']}] ---")
        logger.info(f"  投稿時間: {publish_dt.strftime('%Y-%m-%d %H:%M')} JST")
        logger.info(f"  画像: {image_local}")
        logger.info(f"  キャプション: {post['caption'][:60]}...")

        if dry_run:
            logger.info("  [DRY RUN] スキップ")
            results.append({"post": post, "status": "dry_run"})
            continue

        try:
            if post["format"] == "Reels":
                # Reels: video URLが必要。image フィールドに動画ファイルパスが入る想定
                if not image_local or not os.path.exists(image_local):
                    logger.warning("  Reels動画ファイルが見つかりません。スキップします。")
                    results.append({"post": post, "status": "skipped_no_file"})
                    continue
                # FB動画予約（バイナリ）
                fb_id = meta.schedule_fb_video(image_local, post["caption"], publish_dt)
                # IG Reels: FBにアップして CDN URL取得
                video_url = meta.upload_photo_for_url(image_local)
                ig_id = meta.schedule_ig_reel(video_url, post["caption"], publish_dt)
                results.append({"post": post, "status": "scheduled", "ig_id": ig_id, "fb_id": fb_id})

            else:
                # フィード写真（シングル or カルーセル）
                images = post.get("images") or ([post["image"]] if post["image"] else [])
                if not images:
                    logger.warning(f"  画像ファイルが指定されていません。スキップします。")
                    results.append({"post": post, "status": "skipped_no_file"})
                    continue

                if len(images) > 1:
                    # カルーセル: Drive永久URLでスケジューラーに登録
                    logger.info(f"  カルーセル投稿: {len(images)}枚")
                    image_urls = []
                    for img_file in images:
                        img_local = find_image(img_file)
                        if not img_local:
                            logger.warning(f"  カルーセル画像が見つかりません: {img_file}")
                            continue
                        url = drive.upload_and_get_public_url(img_local)
                        image_urls.append(url)
                    if not image_urls:
                        logger.warning("  カルーセル画像が1枚も見つかりません。スキップします。")
                        results.append({"post": post, "status": "skipped_no_file"})
                        continue
                    ig_id = meta.schedule_ig_carousel_via_server(image_urls, post["caption"], publish_dt)
                    # FB: 1枚目のみ（カルーセルはFB側では非対応）
                    fb_local = find_image(images[0])
                    fb_id = meta.schedule_fb_photo(fb_local, post["caption"], publish_dt) if fb_local else ""
                    results.append({"post": post, "status": "scheduled", "ig_id": ig_id, "fb_id": fb_id})

                else:
                    # シングル写真: Drive永久URLでスケジューラーに登録
                    image_local = find_image(images[0])
                    if not image_local:
                        logger.warning(f"  画像ファイルが見つかりません: {images[0]}")
                        results.append({"post": post, "status": "skipped_no_file"})
                        continue
                    image_url = drive.upload_and_get_public_url(image_local)
                    ig_id = meta.schedule_ig_photo_via_server(image_url, post["caption"], publish_dt)
                    fb_id = meta.schedule_fb_photo(image_local, post["caption"], publish_dt)
                    results.append({"post": post, "status": "scheduled", "ig_id": ig_id, "fb_id": fb_id})

            logger.info(f"  ✓ 予約完了")

        except Exception as e:
            logger.error(f"  ✗ エラー: {e}")
            results.append({"post": post, "status": "error", "error": str(e)})

    # 結果サマリー
    logger.info("\n=== スケジューリング結果 ===")
    for r in results:
        p = r["post"]
        status_icon = "✓" if r["status"] == "scheduled" else ("⚠" if r["status"].startswith("skip") else "✗")
        logger.info(f"  {status_icon} {p['weekday']}（{p['date_str']}）{p['format']}: {r['status']}")

    scheduled = [r for r in results if r["status"] == "scheduled"]
    logger.info(f"\n完了: {len(scheduled)}/{len(posts)} 件を予約しました")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python apps/sns_pilot/schedule_posts.py <draft_path> [--dry-run]")
        print("例:     python apps/sns_pilot/schedule_posts.py data/sns_pilot/drafts/2026-04-21.md")
        sys.exit(1)

    dry = "--dry-run" in sys.argv
    main(sys.argv[1], dry_run=dry)
