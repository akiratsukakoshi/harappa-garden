"""
週次振り返りレポート生成スクリプト
使い方: python apps/sns_pilot/weekly_report.py

先週月曜0:00〜日曜23:59（JST）のMeta Insightsを取得 → Googleスプレッドシートに記録 → MDレポートを出力
"""
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from apps.sns_pilot.meta_client import MetaClient
from apps.sns_pilot.sheets_client import SNSSheetsClient
from modules.utils import setup_logger

load_dotenv()
logger = setup_logger("WeeklyReport")

with open("apps/sns_pilot/config.json") as f:
    CONFIG = json.load(f)

TARGET_NON_FOLLOWER_RATE = CONFIG["reels_target_non_follower_reach_rate"]
TARGET_3SEC_RATE = CONFIG["reels_target_3sec_retention_rate"]

WEEKDAY_JP = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
PURPOSE_LABEL = {"B": "既存共感", "A": "新規獲得", "C": "哲学共有", "reels": "新規リーチ"}


def classify_post(post: dict) -> dict:
    """投稿の形式・目的を media_type と曜日から推定する"""
    ts = datetime.fromisoformat(post["timestamp"].replace("Z", "+00:00"))
    weekday = WEEKDAY_JP[ts.weekday()]
    is_video = post.get("media_type") == "VIDEO"
    fmt = "Reels" if is_video else "フィード"
    # Reelsは曜日によらず目的=reels、フィードは曜日で目的を推定
    if is_video:
        purpose = "reels"
    else:
        purpose = {"火": "B", "土": "A/C"}.get(weekday, "不明")
    return {"weekday": weekday, "format": fmt, "purpose": purpose, "ts": ts}


def calculate_non_follower_rate(reach: int, followers: int) -> float | None:
    """非フォロワーリーチ率の近似計算"""
    if not reach or not followers:
        return None
    # フォロワーへの到達は最大でもフォロワー数まで
    estimated_follower_reach = min(reach, followers)
    non_follower_reach = max(0, reach - estimated_follower_reach)
    return round(non_follower_reach / reach, 3) if reach > 0 else None


def generate_ai_comment(post_rows: list[dict], weekly_data: dict) -> str:
    """
    簡易AIコメント（ルールベース）。
    本格的なLLM分析はSKILLレイヤーで行うため、ここでは傾向の文字列を返す。
    """
    comments = []

    # Reels非フォロワーリーチ率
    reels_rows = [r for r in post_rows if r.get("format") == "Reels"]
    if reels_rows and reels_rows[0].get("non_follower_reach_rate"):
        rate = reels_rows[0]["non_follower_reach_rate"]
        if rate >= TARGET_NON_FOLLOWER_RATE:
            comments.append(f"Reelsのフォロワー外リーチ率 {rate:.0%} → 目標達成")
        else:
            comments.append(f"Reelsのフォロワー外リーチ率 {rate:.0%} → 目標({TARGET_NON_FOLLOWER_RATE:.0%})未達。フックを改善する余地あり")

    # 最高保存数の投稿目的
    feed_rows = [r for r in post_rows if r.get("format") == "フィード" and r.get("saved")]
    if feed_rows:
        top = max(feed_rows, key=lambda x: x.get("saved", 0))
        comments.append(f"最高保存数: {top['purpose']}目的投稿（{top.get('saved')}件）→ 来週も同目的を維持推奨")

    # フォロワー増加
    diff = weekly_data.get("followers_diff", 0)
    if diff > 0:
        comments.append(f"フォロワー +{diff}人")
    elif diff < 0:
        comments.append(f"フォロワー {diff}人（減少）→ 内容の見直しを検討")

    return " / ".join(comments) if comments else "データ不足のためコメント生成できませんでした"


def get_last_week_range() -> tuple[datetime, datetime]:
    """先週の月曜0:00〜日曜23:59（JST）を返す"""
    JST = ZoneInfo("Asia/Tokyo")
    today = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    # 今日の曜日（月=0）から先週月曜を算出
    days_since_monday = today.weekday()  # 今日が月曜なら0
    last_monday = today - timedelta(days=days_since_monday + 7)
    last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return last_monday, last_sunday


def main():
    logger.info("=== 週次レポート生成開始 ===")

    meta = MetaClient()
    sheets = SNSSheetsClient()

    # ── 1. 先週（月〜日）の投稿を取得 ──
    recent_posts = meta.get_recent_posts(limit=15)
    week_start, week_end = get_last_week_range()
    logger.info(f"集計期間: {week_start.strftime('%Y-%m-%d')} 〜 {week_end.strftime('%Y-%m-%d')}")

    this_week_posts = [
        p for p in recent_posts
        if week_start
        <= datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")).astimezone(week_start.tzinfo)
        <= week_end
    ]
    logger.info(f"対象投稿: {len(this_week_posts)} 件")

    # ── 2. 各投稿のInsightsを取得 ──
    follower_count = meta.get_follower_count()
    account_insights = meta.get_account_insights(days=14)  # 先週分をカバーするため14日

    post_rows = []
    for post in this_week_posts:
        insights = meta.get_post_insights(post["id"])
        meta_info = classify_post(post)
        reach = insights.get("reach", 0)
        non_follower_rate = calculate_non_follower_rate(reach, follower_count)

        row = {
            "date": meta_info["ts"].strftime("%Y-%m-%d"),
            "weekday": meta_info["weekday"],
            "format": meta_info["format"],
            "purpose": meta_info["purpose"],
            "post_time": meta_info["ts"].strftime("%H:%M"),
            "reach": reach,
            "likes": post.get("like_count", 0),       # media APIから取得（インサイトより正確）
            "saved": insights.get("saved", 0),
            "shares": insights.get("shares", 0),
            "comments": post.get("comments_count", 0), # media APIから取得
            "video_views": insights.get("video_views"),  # Reels専用
            "non_follower_reach_rate": non_follower_rate,
            "3sec_retention": None,
            "permalink": post.get("permalink", ""),
            "fb_likes": None,    # Facebook側（手動補完または将来自動化）
            "fb_shares": None,
            "fb_comments": None,
        }
        post_rows.append(row)

    # ── 3. 週次サマリーデータ集計 ──
    total_reach = sum(r.get("reach", 0) for r in post_rows)
    feed_b = next((r for r in post_rows if r["purpose"] == "B"), {})
    feed_ac = next((r for r in post_rows if r["purpose"] in ("A/C", "A", "C")), {})
    reels = next((r for r in post_rows if r["format"] == "Reels"), {})

    # フォロワー増減（Insightsから）
    follower_diff_raw = account_insights.get("follower_count", 0)

    # 最高パフォーマンス投稿
    top_post = max(post_rows, key=lambda x: x.get("saved", 0), default={})
    top_label = (f"{top_post.get('weekday')}（{top_post.get('date','')[-5:]}）"
                 f"{top_post.get('purpose')} 保存{top_post.get('saved',0)}件") if top_post else ""

    weekly_data = {
        "week": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "followers": follower_count,
        "followers_diff": follower_diff_raw,
        "total_reach": total_reach,
        "feed_b_reach": feed_b.get("reach", ""),
        "feed_ac_reach": feed_ac.get("reach", ""),
        "reels_reach": reels.get("reach", ""),
        "reels_non_follower_rate": reels.get("non_follower_reach_rate", ""),
        "reels_3sec_rate": reels.get("3sec_retention", ""),
        "top_post": top_label,
        "ai_comment": generate_ai_comment(post_rows, {"followers_diff": follower_diff_raw}),
    }

    # ── 4. Sheetsに記録 ──
    sheets.append_post_log(post_rows)
    sheets.append_weekly_summary(weekly_data)

    if reels:
        sheets.append_reels_kpi({
            "date": reels.get("date"),
            "reach": reels.get("reach"),
            "plays": reels.get("video_views"),
            "non_follower_reach_rate": reels.get("non_follower_reach_rate"),
            "3sec_retention": reels.get("3sec_retention"),
            "shares": reels.get("shares"),
            "dm_sends": None,
            "permalink": reels.get("permalink"),
        })

    # ── 5. MDレポート出力 ──
    now = datetime.now()
    report = _build_report_md(weekly_data, post_rows)
    report_path = f"data/sns_pilot/reports/{now.strftime('%Y-%m-%d')}_weekly.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"レポート出力: {report_path}")
    print("\n" + report)
    return report


def _build_report_md(weekly: dict, posts: list[dict]) -> str:
    week_start = weekly["week"]
    week_end = weekly.get("week_end", "")
    lines = [
        f"# SNS週次レポート {week_start}〜{week_end}",
        "",
        "## アカウントサマリー（Instagram）",
        f"- フォロワー数: **{weekly['followers']:,}** （前週比 {weekly['followers_diff']:+d}）",
        f"- 総リーチ（IG合計）: **{weekly['total_reach']:,}**",
        "",
        "## 投稿別パフォーマンス（Instagram）",
        "| 投稿日 | 曜日 | 形式 | 目的 | リーチ | いいね | 保存 | シェア | コメント |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(posts, key=lambda x: x.get("date", "")):
        vv = r.get("video_views")
        vv_str = f"（再生{vv:,}）" if vv else ""
        lines.append(
            f"| {r['date']} | {r['weekday']} | {r['format']}{vv_str} | {r['purpose']} "
            f"| {r.get('reach', 0):,} | {r.get('likes', 0):,} | {r.get('saved', 0):,} "
            f"| {r.get('shares', 0):,} | {r.get('comments', 0):,} |"
        )

    lines += [
        "",
        "## Facebookデータ（手動補完）",
        "> ※ Facebook側のリーチ・いいね・シェアはMeta Business Suiteで確認して記入してください。",
        "| 投稿日 | FB いいね | FB シェア | FB コメント |",
        "|---|---|---|---|",
    ]
    for r in sorted(posts, key=lambda x: x.get("date", "")):
        lines.append(
            f"| {r['date']} | {r.get('fb_likes') or '-'} | {r.get('fb_shares') or '-'} | {r.get('fb_comments') or '-'} |"
        )

    lines += [
        "",
        "## Reels指標",
    ]
    reels = next((r for r in posts if r["format"] == "Reels"), None)
    if reels:
        rate = reels.get("non_follower_reach_rate")
        rate_str = f"{rate:.1%}" if rate else "取得中"
        target_icon = "✓" if (rate and rate >= TARGET_NON_FOLLOWER_RATE) else "△"
        vv = reels.get("video_views")
        lines += [
            f"- リーチ: **{reels.get('reach', 0):,}**",
            f"- 再生数: **{vv:,}**" if vv else "- 再生数: 取得中",
            f"- フォロワー外リーチ率: **{rate_str}** {target_icon}（目標: {TARGET_NON_FOLLOWER_RATE:.0%}）",
            f"- 3秒視聴率: {reels.get('3sec_retention') or '取得中'}",
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
        lines.append(f"| {r['date']} | {r['weekday']} | {r.get('post_time','')} | {r.get('reach', 0):,} |")

    lines += [
        "",
        "## 今週の気づき・次週への提案",
        f"> {weekly['ai_comment']}",
        "",
        "---",
        f"_自動生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
