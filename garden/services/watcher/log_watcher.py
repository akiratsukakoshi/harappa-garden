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

サブコマンド:
  log_watcher.py summary — 朝ブリーフィング用サマリを stdout に出す(S40)。
    watcher.log から「番人自身の生存」(相互監視)と「過去24時間のアラート」を要約。
    Discord 通知はせず、常に exit 0(morning-briefing の computed_inputs から呼ばれる)。
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

# ig_scheduler の失敗ジョブ監視(S56)。投稿失敗はログでなくコンテナ内 DB に残るため、
# ログ走査では拾えない。API を直接照会して未通知の failed を 1 回ずつ通知する。
IG_SCHED_ENV = Path(os.environ.get("IG_SCHEDULER_ENV_FILE", "/home/vps-harappa/ig_scheduler/.env"))
IG_SCHED_URL = os.environ.get("IG_SCHEDULER_LOCAL_URL", "http://127.0.0.1:8100")
IG_FAIL_TRACK_MAX = 200  # state に保持する alerted job id の上限

# board 規約 lint(S56 一元管理 enforcement)。board_lint は garden-gaku-co 配下にあるため path 注入。
GAKU_CO_DIR = os.environ.get("GAKU_CO_DIR", "/home/vps-harappa/garden/services/garden-gaku-co")


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


def _ig_api_key():
    """ig_scheduler の .env から SCHEDULER_API_KEY を読む(無ければ None)。"""
    try:
        for raw in IG_SCHED_ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("SCHEDULER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def check_ig_scheduler_failures(state: dict) -> list:
    """ig_scheduler の失敗ジョブ(status=failed)を検出して通知メッセージの list を返す。

    投稿失敗はログでなく ig_scheduler の DB に残る(コンテナ内)。ログ走査では拾えないため
    API を直接照会する。未通知の failed だけを 1 回ずつ通知(state["ig_failed_alerted"] で
    id を追跡)。初回実行は既存 failed を基準記録のみ(過去の失敗で洪水にしない)。
    """
    alerts: list = []
    first_run = "ig_failed_alerted" not in state
    alerted = state.setdefault("ig_failed_alerted", [])
    alerted_set = set(alerted)

    key = _ig_api_key()
    if not key:
        return alerts  # ig_scheduler 不在/鍵読めず = 静かにスキップ
    try:
        req = urllib.request.Request(f"{IG_SCHED_URL}/jobs", headers={"x-api-key": key})
        with urllib.request.urlopen(req, timeout=15) as resp:
            jobs = json.load(resp)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as e:
        log(f"WARN: ig_scheduler 照会失敗: {e}")
        return alerts

    for j in jobs:
        if j.get("status") != "failed":
            continue
        jid = j.get("id")
        if jid in alerted_set:
            continue
        alerted_set.add(jid)
        alerted.append(jid)
        if first_run:
            continue  # 基準記録のみ(通知しない)
        cap = (j.get("caption") or "").replace("\n", " ")[:40]
        alerts.append(
            f"📵 IG 投稿失敗(ig_scheduler job {jid} / {j.get('platform')})\n"
            f"  予定: {j.get('publish_at')}\n"
            f"  error: {(j.get('error_msg') or '')[:140]}\n"
            f"  caption: {cap}…\n"
            f"  → 画像URL失効(FB CDN)等が原因。`schedule` で再予約を"
        )
    if len(alerted) > IG_FAIL_TRACK_MAX:
        del alerted[: len(alerted) - IG_FAIL_TRACK_MAX]
    if first_run:
        log(f"ig_scheduler: 初回 = 既存 failed {len(alerted)} 件を基準記録(通知なし)")
    return alerts


def check_board_lint(state: dict) -> list:
    """board 規約違反(ERROR)を board_lint で検出し、新規違反のみ通知する。

    違反は修正されるまで残るため、毎回通知せず「前回見えていなかった違反」だけ通知する
    (解消されたら集合から落ちる=再発時に再通知)。WARN は静かに(ノイズ回避)。
    """
    alerts: list = []
    try:
        if GAKU_CO_DIR not in sys.path:
            sys.path.insert(0, GAKU_CO_DIR)
        import board_lint
        viol = board_lint.collect_violations()
    except Exception as e:
        log(f"WARN: board_lint 実行失敗: {e}")
        return alerts
    errors = sorted({m for sev, m in viol if sev == "ERROR"})
    prev = set(state.get("board_lint_seen", []))
    for m in errors:
        if m not in prev:
            alerts.append(
                f"🧹 board 規約違反(ERROR): {m}\n"
                f"→ board_registry.py 登録 or board 修正を(`board_lint.py` 参照)")
    state["board_lint_seen"] = errors  # 解消された違反は落とす(再発時に再通知)
    return alerts


def summary() -> int:
    """朝ブリーフィング用サマリ(S40)。watcher.log を読むだけ。常に exit 0。

    番人 cron は */10 で毎回 log() を watcher.log に書くため、mtime の鮮度が
    そのまま番人自身の生存確認になる(番人は自分の死を通知できない → 朝に拾う)。
    """
    lines = []
    watcher_log = LOG_DIR / "watcher.log"
    now = now_jst()

    if not watcher_log.exists():
        lines.append("- ⚠️ 番人ログが見つかりません(watcher 未稼働の可能性)")
        print("\n".join(lines))
        return 0

    age_min = int((now.timestamp() - watcher_log.stat().st_mtime) / 60)
    if age_min > 30:
        lines.append(
            f"- ⚠️ 番人が {age_min} 分動いていません(cron */10 のはず)。"
            f"crontab / 実行ビットの確認を(S36 型)"
        )
    else:
        lines.append(f"- 番人稼働中(最終実行 {age_min} 分前)")

    alerts = []
    cutoff = now - timedelta(hours=24)
    try:
        text = watcher_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for ln in text.splitlines():
        m = re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (ALERT: .+)$", ln)
        if not m:
            continue
        try:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
        except ValueError:
            continue
        if ts >= cutoff:
            alerts.append((ts, m.group(2)))

    if alerts:
        lines.append(f"- 🚨 過去24時間のアラート: {len(alerts)} 件(各詳細は Discord master に通知済み)")
        for ts, msg in alerts[-5:]:
            lines.append(f"  - [{ts.strftime('%m/%d %H:%M')}] {msg[:140]}")
        if len(alerts) > 5:
            lines.append(f"  - …ほか {len(alerts) - 5} 件")
    else:
        lines.append("- 過去24時間のアラート: 0 件")

    print("\n".join(lines))
    return 0


def main() -> int:
    if not LOG_DIR.is_dir():
        log(f"FAIL: LOG_DIR が無い: {LOG_DIR}")
        return 1
    state = load_state()

    findings = scan_new_errors(state)
    heartbeat_alerts = check_heartbeats(state)
    try:
        ig_alerts = check_ig_scheduler_failures(state)
    except Exception as e:  # 監視が本体を巻き込んで落ちないように保険
        log(f"WARN: ig_scheduler チェックで例外: {e}")
        ig_alerts = []
    try:
        lint_alerts = check_board_lint(state)
    except Exception as e:
        log(f"WARN: board_lint チェックで例外: {e}")
        lint_alerts = []

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

    for alert in ig_alerts:
        notify_master(alert)
        log("ALERT: " + alert.splitlines()[0])

    for alert in lint_alerts:
        notify_master(alert)
        log("ALERT: " + alert.splitlines()[0])

    if not findings and not heartbeat_alerts and not ig_alerts and not lint_alerts:
        log("OK: 異常なし")

    save_state(state)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        sys.exit(summary())
    sys.exit(main())
