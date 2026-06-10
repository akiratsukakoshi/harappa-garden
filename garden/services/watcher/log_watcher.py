#!/usr/bin/env python3
"""log_watcher.py — 番人(Watcher): cron 失敗の沈黙を破る監視エージェント

S39 新設(2026-06-10)。Garden 語彙の「番人」の最小実装。

やること(10 分毎 cron):
  1. /home/vps-harappa/garden/log/*.log の「前回スキャン以降の追記分」だけを読み、
     エラーパターン(Traceback / ERROR / FAIL / Permission denied / exit code 非0)を検出
     → Discord master チャンネルに通知
  2. ハートビート: 高頻度 cron のログ鮮度を確認
     - send-pending.log(毎分)が 15 分以上更新なし → cron 全体が沈黙している可能性(S36 型障害)
     - bot-keepalive.log(2 分毎)が 15 分以上更新なし → 同上
     → 検出時に通知(同一警報は 6 時間に 1 回に抑制)

設計メモ:
  - オフセット管理: state ファイルに「各 log を何バイト目まで読んだか」を記録。
    再通知スパムを構造的に防ぐ(エラー行は一度しか通知されない)
  - ログローテーション(ファイル縮小)を検知したら offset を 0 に戻す
  - watcher.log(自分自身の出力)はスキャン対象外(通知ループ防止)
  - 依存: stdlib のみ(venv 不要)。Discord 認証は env(DISCORD_BOT_TOKEN /
    DISCORD_MASTER_CHANNEL_ID、run-watcher.sh が garden-gaku-co/.env を source)

実行:
  cron */10 * * * * /home/vps-harappa/garden/services/watcher/run-watcher.sh
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

LOG_DIR = Path(os.environ.get("WATCHER_LOG_DIR", "/home/vps-harappa/garden/log"))
STATE_PATH = LOG_DIR / ".watcher-state.json"
SELF_LOG_NAMES = {"watcher.log"}  # 自分の出力は見ない(ループ防止)

# エラーパターン(大文字小文字無視)。「0 failed」等の正常報告は除外
ERROR_RE = re.compile(
    r"(?i)(traceback \(most recent call last\)|\berror\b|\bFAIL\b|failed|"
    r"permission denied|command not found|no such file or directory|"
    r"exit[ _-]?code[:= ]*[1-9])"
)
NEGATE_RE = re.compile(r"(?i)(\b0 (errors?|failed)\b|error[s]?: ?0\b|fail(ed)?: ?0\b)")

# ハートビート: マーカーファイル名 → 許容無更新時間(分)
# *.log の mtime は「何か起きた時だけ」更新されるため生存確認に使えない。
# 各ラッパー(run-send-pending.sh / run-bot.sh)が起動の度に touch するマーカーを見る。
HEARTBEATS = {
    ".heartbeat-send-pending": 15,   # 毎分 cron。15 分無音 = cron が止まっている
    ".heartbeat-bot-keepalive": 15,  # 2 分毎 cron
}
HEARTBEAT_REALERT_HOURS = 6  # 同一警報の再通知間隔

MAX_LINES_PER_FILE = 8    # 1 ファイルあたり通知に載せる最大エラー行数
MAX_LINE_LEN = 180


def now_jst() -> datetime:
    return datetime.now(JST)


def log(msg: str) -> None:
    print(f"[{now_jst().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def notify_master(content: str) -> bool:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    channel = os.environ.get("DISCORD_MASTER_CHANNEL_ID")
    if not token or not channel:
        log("WARN: DISCORD_BOT_TOKEN / DISCORD_MASTER_CHANNEL_ID 未設定、通知スキップ")
        return False
    payload = json.dumps({"content": content[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        data=payload,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            # urllib デフォルト UA は Discord 側が 403 で弾く(send_pending.py と同じ UA を使う)
            "User-Agent": "garden-gaku-co (https://github.com/akiratsukakoshi/harappa-garden, 0.1)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError) as e:
        log(f"WARN: Discord 通知失敗: {e}")
        return False


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offsets": {}, "last_alerts": {}}


def save_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    tmp.replace(STATE_PATH)


def scan_new_errors(state: dict) -> dict:
    """各 log の追記分からエラー行を抽出。{filename: [lines]} を返す"""
    findings: dict = {}
    offsets = state.setdefault("offsets", {})
    first_run = not bool(offsets)
    for path in sorted(LOG_DIR.glob("*.log")):
        if path.name in SELF_LOG_NAMES:
            continue
        size = path.stat().st_size
        prev = offsets.get(path.name, None)
        if prev is None:
            # 初見のファイル: 既存内容は遡らない(導入時の過去ログ洪水を防ぐ)
            offsets[path.name] = size
            continue
        if size < prev:  # ローテーション/truncate
            prev = 0
        if size == prev:
            continue
        hits = []
        with open(path, "rb") as f:
            f.seek(prev)
            chunk = f.read(size - prev)
        for raw in chunk.decode("utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line:
                continue
            if ERROR_RE.search(line) and not NEGATE_RE.search(line):
                hits.append(line[:MAX_LINE_LEN])
        offsets[path.name] = size
        if hits:
            findings[path.name] = hits
    if first_run:
        log("初回実行: 既存ログは基準点として記録のみ(次回から差分監視)")
    return findings


def check_heartbeats(state: dict) -> list:
    """高頻度 cron のログ鮮度を確認。警報メッセージの list を返す"""
    alerts = []
    last_alerts = state.setdefault("last_alerts", {})
    now = now_jst()
    for name, max_min in HEARTBEATS.items():
        path = LOG_DIR / name
        if not path.exists():
            continue  # ラッパー未更新の移行期間は無視(touch が始まれば監視開始)
        age_min = (now.timestamp() - path.stat().st_mtime) / 60
        if age_min <= max_min:
            last_alerts.pop(f"heartbeat:{name}", None)  # 回復したら抑制解除
            continue
        key = f"heartbeat:{name}"
        last = last_alerts.get(key)
        if last:
            last_dt = datetime.fromisoformat(last)
            if (now - last_dt) < timedelta(hours=HEARTBEAT_REALERT_HOURS):
                continue  # 抑制中
        last_alerts[key] = now.isoformat()
        alerts.append(
            f"💤 `{name}` が {int(age_min)} 分更新されていません"
            f"(許容 {max_min} 分)。cron が沈黙している可能性(S36 型)。\n"
            f"→ `ssh harappa` して `crontab -l` / 実行ビット / "
            f"`tail /home/vps-harappa/garden/log/{name}` を確認"
        )
    return alerts


def main() -> int:
    if not LOG_DIR.is_dir():
        log(f"FAIL: LOG_DIR が無い: {LOG_DIR}")
        return 1
    state = load_state()

    findings = scan_new_errors(state)
    heartbeat_alerts = check_heartbeats(state)

    if findings:
        parts = [f"🚨 番人: cron ログにエラー検出({now_jst().strftime('%m/%d %H:%M')})"]
        for name, lines in findings.items():
            shown = lines[:MAX_LINES_PER_FILE]
            more = f"\n…ほか {len(lines) - len(shown)} 行" if len(lines) > len(shown) else ""
            body = "\n".join(shown)
            parts.append(f"**{name}** ({len(lines)} 行)\n```\n{body}\n```{more}")
        notify_master("\n".join(parts))
        log(f"ALERT: {sum(len(v) for v in findings.values())} 行 / {len(findings)} ファイル")

    for alert in heartbeat_alerts:
        notify_master(f"🚨 番人: {alert}")
        log("ALERT: " + alert.splitlines()[0])

    if not findings and not heartbeat_alerts:
        log("OK: 異常なし")

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
