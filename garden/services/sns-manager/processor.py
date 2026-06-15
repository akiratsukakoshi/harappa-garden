#!/usr/bin/env python3
"""sns-manager — 原っぱ大学の SNS 運用(HMC sns_pilot の transplant 移植、S45)

Garden 化の差分(業務知識は継承、起動と承認だけ Garden に変える):
- HMC drive_uploader(投稿画像を Drive にアップ)→ drive_reader(ガクチョが置いた
  候補画像を Drive から DL)に方向転換。新フロー = 金:ガクチョ設置 / 土:Garden セレクト
- credentials.json(SA)→ lib/google_sa.py(GOOGLE_SA_FILE、expense/invoice の SA 流用)
- 投稿予約は VPS の ig_scheduler(meta_client.schedule_*_via_server)を共用
- セレクト・文案の creative 判断は processor では行わない。種プロンプト内で Claude が
  画像を Read して選び/書き、board でガクチョの剪定を通す(daily-pilot 型)

使い方:
    python processor.py fetch-images --week YYYY-MM-DD   # Drive 候補画像 → temp にDL + 一覧
    python processor.py report [--dry-run]               # 先週の Meta Insights → Sheet + MD
    python processor.py schedule --image PATH --caption-file PATH \
        --publish-at 2026-06-16T20:00:00 [--platform both|ig|fb] [--dry-run]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from lib.utils import setup_logger, ensure_directory

logger = setup_logger("SNSManager")
load_dotenv()

JST = ZoneInfo("Asia/Tokyo")
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(_BASE_DIR, "temp")
REPORTS_DIR = os.path.join(_BASE_DIR, "temp", "reports")

with open(os.path.join(_BASE_DIR, "config", "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)

TARGET_NON_FOLLOWER_RATE = CONFIG["reels_target_non_follower_reach_rate"]
TARGET_3SEC_RATE = CONFIG["reels_target_3sec_retention_rate"]

WEEKDAY_JP = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}


# ──────────────────────────────────────────────
# fetch-images: Drive 候補画像を DL
# ──────────────────────────────────────────────

def cmd_fetch_images(week: str):
    from lib.drive_reader import DriveReader

    folder_id = os.getenv("SNS_DRIVE_FOLDER_ID")
    if not folder_id:
        logger.error("SNS_DRIVE_FOLDER_ID が未設定です。")
        sys.exit(1)

    reader = DriveReader()
    images = reader.list_images(folder_id)
    if not images:
        print("no candidate images")
        return

    dest = os.path.join(TEMP_DIR, f"candidates-{week}")
    ensure_directory(dest)
    print(f"候補画像 {len(images)} 件 → {dest}")
    for img in images:
        local = os.path.join(dest, img["name"])
        reader.download(img["id"], local)
        print(f"  {img['name']}  (id={img['id']})  -> {local}")
    print("downloaded")


# ──────────────────────────────────────────────
# schedule: 承認済みの画像+文案を ig_scheduler / FB に予約
# ──────────────────────────────────────────────

def _archive_used_images(paths):
    """投稿に使った画像の Drive 原本を used/(使用済み)フォルダへ移動する。

    ローカルファイル名で候補フォルダ直下を引き当てて move する。Drive に同名が
    無い場合(アドホックでローカル画像を直接渡した等)は黙ってスキップ。
    """
    folder_id = os.getenv("SNS_DRIVE_FOLDER_ID")
    if not folder_id:
        logger.info("SNS_DRIVE_FOLDER_ID 未設定のため使用済み移動をスキップ")
        return

    from lib.drive_reader import DriveReader
    reader = DriveReader()
    used_id = None
    for p in paths:
        name = os.path.basename(p)
        found = reader.find_image_by_name(folder_id, name)
        if not found:
            logger.info(f"使用済み移動スキップ(Drive 候補に同名なし): {name}")
            continue
        if used_id is None:
            used_id = reader.ensure_used_folder(folder_id)
        reader.move_to_used(found["id"], folder_id, used_id)
        logger.info(f"使用済みへ移動: {name} → 使用済み/")


def cmd_schedule(image, images, caption_file, publish_at, platform, dry_run, no_archive=False):
    # 画像リストを構築(--images 優先。2 枚以上ならカルーセル)
    if images:
        paths = [p.strip() for p in images.split(",") if p.strip()]
    elif image:
        paths = [image]
    else:
        logger.error("--image か --images のどちらかが必要です。")
        sys.exit(1)
    for p in paths:
        if not os.path.exists(p):
            logger.error(f"画像が見つかりません: {p}")
            sys.exit(1)
    if len(paths) > 10:
        logger.error("カルーセルは最大 10 枚です。")
        sys.exit(1)

    with open(caption_file, encoding="utf-8") as f:
        caption = f.read().strip()
    if not caption:
        logger.error("caption が空です。")
        sys.exit(1)

    # publish_at: ローカル(JST naive)文字列 → aware
    dt = datetime.fromisoformat(publish_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    kind = "カルーセル" if len(paths) > 1 else "単写真"
    logger.info(f"予約: {dt.strftime('%Y-%m-%d %H:%M %Z')} / platform={platform} / {kind} {len(paths)}枚")
    for p in paths:
        logger.info(f"  画像: {p}")
    logger.info(f"caption: {caption[:60]}...")

    if dry_run:
        print(f"[DRY RUN] would schedule {platform}({kind} {len(paths)}枚) at {dt.isoformat()}")
        return

    from lib.meta_client import MetaClient
    meta = MetaClient()
    result = {}
    if platform in ("both", "ig"):
        if len(paths) > 1:
            result["ig_id"] = meta.schedule_ig_carousel_via_server(paths, caption, dt)
        else:
            result["ig_id"] = meta.schedule_ig_photo_via_server(paths[0], caption, dt)
    if platform in ("both", "fb"):
        if len(paths) > 1:
            result["fb_id"] = meta.schedule_fb_carousel(paths, caption, dt)
        else:
            result["fb_id"] = meta.schedule_fb_photo(paths[0], caption, dt)
    print("scheduled:", json.dumps(result, ensure_ascii=False))

    # 予約成功後に Drive 原本を used/ へ退避(予約は完了済みなので失敗しても致命ではない)
    if not no_archive:
        try:
            _archive_used_images(paths)
        except Exception as e:
            logger.warning(f"使用済みフォルダへの移動に失敗(投稿予約は完了済み): {e}")


# ──────────────────────────────────────────────
# report: 先週の Meta Insights → Sheet + MD(HMC weekly_report.py 移植)
# ──────────────────────────────────────────────

def _classify_post(post):
    ts = datetime.fromisoformat(post["timestamp"].replace("Z", "+00:00"))
    weekday = WEEKDAY_JP[ts.weekday()]
    is_video = post.get("media_type") == "VIDEO"
    fmt = "Reels" if is_video else "フィード"
    purpose = "reels" if is_video else {"火": "B", "土": "A/C"}.get(weekday, "不明")
    return {"weekday": weekday, "format": fmt, "purpose": purpose, "ts": ts}


def _non_follower_rate(reach, followers):
    if not reach or not followers:
        return None
    estimated_follower_reach = min(reach, followers)
    non_follower_reach = max(0, reach - estimated_follower_reach)
    return round(non_follower_reach / reach, 3) if reach > 0 else None


def _last_week_range():
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return last_monday, last_sunday


def _ai_comment(post_rows, weekly_data):
    comments = []
    reels_rows = [r for r in post_rows if r.get("format") == "Reels"]
    if reels_rows and reels_rows[0].get("non_follower_reach_rate"):
        rate = reels_rows[0]["non_follower_reach_rate"]
        if rate >= TARGET_NON_FOLLOWER_RATE:
            comments.append(f"Reelsのフォロワー外リーチ率 {rate:.0%} → 目標達成")
        else:
            comments.append(
                f"Reelsのフォロワー外リーチ率 {rate:.0%} → 目標({TARGET_NON_FOLLOWER_RATE:.0%})未達。フックに改善余地"
            )
    feed_rows = [r for r in post_rows if r.get("format") == "フィード" and r.get("saved")]
    if feed_rows:
        top = max(feed_rows, key=lambda x: x.get("saved", 0))
        comments.append(f"最高保存数: {top['purpose']}目的({top.get('saved')}件)→ 来週も同目的を維持推奨")
    diff = weekly_data.get("followers_diff", 0)
    if diff > 0:
        comments.append(f"フォロワー +{diff}人")
    elif diff < 0:
        comments.append(f"フォロワー {diff}人(減少)→ 内容の見直しを検討")
    return " / ".join(comments) if comments else "データ不足のためコメント生成できませんでした"


def _build_report_md(weekly, posts):
    lines = [
        f"# SNS週次レポート {weekly['week']}〜{weekly.get('week_end', '')}",
        "",
        "## アカウントサマリー(Instagram)",
        f"- フォロワー数: **{weekly['followers']:,}** (前週比 {weekly['followers_diff']:+d})",
        f"- 総リーチ(IG合計): **{weekly['total_reach']:,}**",
        "",
        "## 投稿別パフォーマンス(Instagram)",
        "| 投稿日 | 曜日 | 形式 | 目的 | リーチ | いいね | 保存 | シェア | コメント |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(posts, key=lambda x: x.get("date", "")):
        vv = r.get("video_views")
        vv_str = f"(再生{vv:,})" if vv else ""
        lines.append(
            f"| {r['date']} | {r['weekday']} | {r['format']}{vv_str} | {r['purpose']} "
            f"| {r.get('reach', 0):,} | {r.get('likes', 0):,} | {r.get('saved', 0):,} "
            f"| {r.get('shares', 0):,} | {r.get('comments', 0):,} |"
        )
    lines += ["", "## Reels指標"]
    reels = next((r for r in posts if r["format"] == "Reels"), None)
    if reels:
        rate = reels.get("non_follower_reach_rate")
        rate_str = f"{rate:.1%}" if rate else "取得中"
        icon = "✓" if (rate and rate >= TARGET_NON_FOLLOWER_RATE) else "△"
        vv = reels.get("video_views")
        lines += [
            f"- リーチ: **{reels.get('reach', 0):,}**",
            f"- 再生数: **{vv:,}**" if vv else "- 再生数: 取得中",
            f"- フォロワー外リーチ率: **{rate_str}** {icon}(目標: {TARGET_NON_FOLLOWER_RATE:.0%})",
        ]
    else:
        lines.append("- Reels投稿なし")
    lines += [
        "",
        "## 投稿時間分析",
        "| 投稿日 | 曜日 | 投稿時間 | リーチ |",
        "|---|---|---|---|",
    ]
    for r in sorted(posts, key=lambda x: x.get("date", "")):
        lines.append(f"| {r['date']} | {r['weekday']} | {r.get('post_time', '')} | {r.get('reach', 0):,} |")
    lines += ["", "## 今週の気づき・次週への提案", f"> {weekly['ai_comment']}"]
    return "\n".join(lines)


def cmd_report(dry_run: bool):
    from lib.meta_client import MetaClient
    meta = MetaClient()

    recent_posts = meta.get_recent_posts(limit=15)
    week_start, week_end = _last_week_range()
    logger.info(f"集計期間: {week_start:%Y-%m-%d} 〜 {week_end:%Y-%m-%d}")

    this_week = [
        p for p in recent_posts
        if week_start
        <= datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")).astimezone(week_start.tzinfo)
        <= week_end
    ]
    logger.info(f"対象投稿: {len(this_week)} 件")

    follower_count = meta.get_follower_count()
    account_insights = meta.get_account_insights(days=14)

    post_rows = []
    for post in this_week:
        insights = meta.get_post_insights(post["id"])
        info = _classify_post(post)
        reach = insights.get("reach", 0)
        post_rows.append({
            "date": info["ts"].strftime("%Y-%m-%d"),
            "weekday": info["weekday"], "format": info["format"], "purpose": info["purpose"],
            "post_time": info["ts"].strftime("%H:%M"), "reach": reach,
            "likes": post.get("like_count", 0), "saved": insights.get("saved", 0),
            "shares": insights.get("shares", 0), "comments": post.get("comments_count", 0),
            "video_views": insights.get("video_views"),
            "non_follower_reach_rate": _non_follower_rate(reach, follower_count),
            "3sec_retention": None, "permalink": post.get("permalink", ""),
        })

    total_reach = sum(r.get("reach", 0) for r in post_rows)
    feed_b = next((r for r in post_rows if r["purpose"] == "B"), {})
    feed_ac = next((r for r in post_rows if r["purpose"] in ("A/C", "A", "C")), {})
    reels = next((r for r in post_rows if r["format"] == "Reels"), {})
    top = max(post_rows, key=lambda x: x.get("saved", 0), default={})
    top_label = (
        f"{top.get('weekday')}({top.get('date', '')[-5:]}) {top.get('purpose')} 保存{top.get('saved', 0)}件"
        if top else ""
    )
    weekly = {
        "week": week_start.strftime("%Y-%m-%d"), "week_end": week_end.strftime("%Y-%m-%d"),
        "followers": follower_count, "followers_diff": account_insights.get("follower_count", 0),
        "total_reach": total_reach, "feed_b_reach": feed_b.get("reach", ""),
        "feed_ac_reach": feed_ac.get("reach", ""), "reels_reach": reels.get("reach", ""),
        "reels_non_follower_rate": reels.get("non_follower_reach_rate", ""),
        "reels_3sec_rate": reels.get("3sec_retention", ""), "top_post": top_label,
    }
    weekly["ai_comment"] = _ai_comment(post_rows, weekly)

    report = _build_report_md(weekly, post_rows)

    if dry_run:
        logger.info("[DRY RUN] Sheets 書き込みスキップ")
    else:
        from lib.sheets_client import SNSSheetsClient
        sheets = SNSSheetsClient()
        sheets.append_post_log(post_rows)
        sheets.append_weekly_summary(weekly)
        if reels:
            sheets.append_reels_kpi({
                "date": reels.get("date"), "reach": reels.get("reach"),
                "plays": reels.get("video_views"),
                "non_follower_reach_rate": reels.get("non_follower_reach_rate"),
                "3sec_retention": reels.get("3sec_retention"), "shares": reels.get("shares"),
                "dm_sends": None, "permalink": reels.get("permalink"),
            })

    ensure_directory(REPORTS_DIR)
    now_jst = datetime.now(JST)
    path = os.path.join(REPORTS_DIR, f"{now_jst:%Y-%m-%d}_weekly.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"レポート出力: {path}")
    print(report)


def main():
    parser = argparse.ArgumentParser(description="sns-manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch-images", help="Drive 候補画像を DL")
    p_fetch.add_argument("--week", required=True, help="その週の月曜日 YYYY-MM-DD")

    p_report = sub.add_parser("report", help="先週の Meta Insights → Sheet + MD")
    p_report.add_argument("--dry-run", action="store_true")

    p_sched = sub.add_parser("schedule", help="承認済み画像+文案を予約(単写真 or カルーセル)")
    p_sched.add_argument("--image", help="単一画像のパス(後方互換)")
    p_sched.add_argument("--images", help="カルーセル: 2〜10 枚をカンマ区切り 'a.jpg,b.jpg'")
    p_sched.add_argument("--caption-file", required=True)
    p_sched.add_argument("--publish-at", required=True, help="JST ISO 例 2026-06-16T20:00:00(任意日時=単発も可)")
    p_sched.add_argument("--platform", default="both", choices=["both", "ig", "fb"])
    p_sched.add_argument("--dry-run", action="store_true")
    p_sched.add_argument("--no-archive", action="store_true",
                         help="使用済み画像の Drive used/ への移動を抑止(既定は移動する)")

    args = parser.parse_args()
    if args.command == "fetch-images":
        cmd_fetch_images(args.week)
    elif args.command == "report":
        cmd_report(args.dry_run)
    elif args.command == "schedule":
        cmd_schedule(args.image, args.images, args.caption_file, args.publish_at,
                     args.platform, args.dry_run, args.no_archive)


if __name__ == "__main__":
    main()
