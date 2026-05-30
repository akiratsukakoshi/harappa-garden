#!/usr/bin/env python3
"""send_pending.py — board/pending/*.md の status を検知して post_approval を実行する

cron `* * * * *` で 1 分毎起動(セッション21、(4) C 案)。

仕様(セッション21 拡張版):
  1. garden/board/pending/*.md を scan
  2. frontmatter `status` を検出:
     - `status: test` → ディスパッチ先を personal に強制 → 配信後 `status: pending` に戻す + テスト送信履歴を board 末尾に追記
     - `status: approved` → 通常ディスパッチ。ただし frontmatter `scheduled_send: YYYY-MM-DDTHH:MM+09:00` が未来なら skip(時刻到達まで待機)
  3. frontmatter `from_seed` に応じてディスパッチ:
     - shift_manager/monthly-shift-survey         → /api/send + /api/approve(staff LINE)
     - shift_manager/monthly-working-hours-confirmation → /api/send + /api/approve(staff LINE)
     - shift_manager/month-end-working-hours-prep → shell 実行(frontmatter.execute_command)
  4. 成功 → board を processed/ へ移動(test の場合は残置) + Discord master 通知
  5. 失敗 → pending 残置 + Discord master 通知

依存:
  - garden-gaku-co/.env(DISCORD_BOT_TOKEN, DISCORD_MASTER_CHANNEL_ID, GAKU_CO_API_URL)
  - garden-gaku-co/venv

実行:
  cron */1 * * * * /home/vps-harappa/garden/services/garden-gaku-co/run-send-pending.sh
"""

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

JST = timezone(timedelta(hours=9))

SCRIPT_DIR = Path(__file__).resolve().parent
GAKU_CO_API_URL = os.environ.get("GAKU_CO_API_URL", "https://bot.harappa.monster/api")
BOARD_PENDING = Path(os.environ.get("BOARD_PENDING", "/home/vps-harappa/garden-mirror/garden/board/pending"))
BOARD_PROCESSED = Path(os.environ.get("BOARD_PROCESSED", "/home/vps-harappa/garden-mirror/garden/board/processed"))
LOG_PATH = Path(os.environ.get("SEND_PENDING_LOG", "/home/vps-harappa/garden-mirror/garden/log/send-pending.log"))
LOCK_FILE = Path("/tmp/send-pending.lock")

DISPATCH_LINE_SEND = {
    "shift_manager/monthly-shift-survey",
    "shift_manager/monthly-working-hours-confirmation",
}
DISPATCH_SHELL = {
    "shift_manager/month-end-working-hours-prep",
}


def log(msg: str) -> None:
    line = f"[{datetime.now(JST).isoformat()}] {msg}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip())


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """簡易 YAML frontmatter parser(top-level スカラーのみ対応)"""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:]
    fm = {}
    for line in fm_text.split("\n"):
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        # クオート除去
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        fm[k] = v
    return fm, body


def extract_send_body(body: str) -> Optional[str]:
    """## 配信本文 セクション内の最初のコードブロックを抽出"""
    # セクションヘッダ位置
    sec_match = re.search(r"^##\s*配信本文\s*$", body, re.MULTILINE)
    if not sec_match:
        return None
    after_sec = body[sec_match.end():]
    # 次の `## ...` までを範囲とする
    next_sec = re.search(r"^##\s", after_sec, re.MULTILINE)
    section_text = after_sec[: next_sec.start()] if next_sec else after_sec
    # コードブロック
    code_match = re.search(r"```(?:\w+)?\n(.+?)\n```", section_text, re.DOTALL)
    if not code_match:
        return None
    return code_match.group(1).strip()


def http_post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {body}")


def notify_master(content: str) -> None:
    """Discord master channel に庭師通知(send.py と同等)"""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    channel = os.environ.get("DISCORD_MASTER_CHANNEL_ID")
    if not token or not channel:
        log("[notify] DISCORD_BOT_TOKEN / DISCORD_MASTER_CHANNEL_ID missing — skipping")
        return
    api = "https://discord.com/api/v10"
    req = urllib.request.Request(
        f"{api}/channels/{channel}/messages",
        data=json.dumps({"content": content[:1900]}).encode("utf-8"),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "garden-gaku-co (https://github.com/akiratsukakoshi/harappa-garden, 0.1)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        log(f"[notify] HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")


def dispatch_line_send(fm: dict, body: str, board_path: Path, group: str = "staff") -> bool:
    """LINE 配信ディスパッチ: /api/send → /api/approve

    group: "staff"(本配信) or "personal"(テスト配信、ガクチョ個人)
    """
    message = extract_send_body(body)
    if not message:
        log(f"[{board_path.name}] FAIL: 配信本文セクションのコードブロックが見つかりません")
        notify_master(f"❌ 配信失敗: {board_path.name}\n→ ## 配信本文 内のコードブロックがありません")
        return False

    try:
        res1 = http_post_json(
            f"{GAKU_CO_API_URL}/send",
            {"group": group, "message": message, "require_approval": False},
        )
    except Exception as e:
        log(f"[{board_path.name}] FAIL: /api/send error: {e}")
        notify_master(f"❌ /api/send 失敗: {board_path.name}\n{e}")
        return False

    pending_id = res1.get("id")
    # staff は強制承認制 → status:pending が期待値、personal は即送信で status:ok
    if group == "staff":
        if res1.get("status") != "pending" or not pending_id:
            log(f"[{board_path.name}] FAIL: unexpected /api/send response: {res1}")
            notify_master(f"❌ /api/send 想定外レスポンス: {res1}")
            return False
        try:
            res2 = http_post_json(f"{GAKU_CO_API_URL}/approve/{pending_id}", {})
        except Exception as e:
            log(f"[{board_path.name}] FAIL: /api/approve error: {e} (pending_id={pending_id})")
            notify_master(f"❌ /api/approve 失敗 (id={pending_id}): {e}")
            return False
        if res2.get("status") != "sent":
            log(f"[{board_path.name}] FAIL: /api/approve unexpected response: {res2}")
            notify_master(f"❌ /api/approve 想定外: {res2}")
            return False
    else:
        # personal は即送信
        if res1.get("status") not in ("ok", "sent"):
            log(f"[{board_path.name}] FAIL: unexpected /api/send response: {res1}")
            notify_master(f"❌ /api/send (personal) 想定外: {res1}")
            return False

    log(f"[{board_path.name}] SENT to group={group} id={pending_id}")
    msg_preview = message[:200] + ('...' if len(message) > 200 else '')
    label = "テスト配信" if group == "personal" else "本配信"
    notify_master(f"✅ {label}完了: {board_path.name}\n→ group={group}\n→ {msg_preview}")
    return True


def dispatch_shell(fm: dict, body: str, board_path: Path) -> bool:
    """shell 実行ディスパッチ: frontmatter.execute_command を実行"""
    cmd = fm.get("execute_command")
    if not cmd:
        log(f"[{board_path.name}] FAIL: frontmatter.execute_command が空")
        notify_master(f"❌ shell 実行失敗: {board_path.name}\n→ execute_command が未設定")
        return False
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,  # 10 分
        )
    except subprocess.TimeoutExpired:
        log(f"[{board_path.name}] FAIL: shell timeout (600s)")
        notify_master(f"❌ shell タイムアウト: {board_path.name}")
        return False
    except Exception as e:
        log(f"[{board_path.name}] FAIL: shell error: {e}")
        notify_master(f"❌ shell 実行エラー: {board_path.name}\n{e}")
        return False

    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").splitlines()[-5:]
        log(f"[{board_path.name}] FAIL: shell exit={result.returncode}\n{result.stderr[:500]}")
        notify_master(f"❌ shell 失敗 (exit={result.returncode}): {board_path.name}\n```\n{chr(10).join(tail)}\n```")
        return False

    # 出力から URL 抽出(generate_working_hours.py が `✓ 完了: https://...` を出す)
    url_match = re.search(r"https://docs\.google\.com/spreadsheets/\S+", result.stdout)
    url_str = url_match.group(0) if url_match else "(URL 抽出失敗)"

    log(f"[{board_path.name}] EXECUTED ok: {url_str}")
    notify_master(f"✅ 集計完了: {board_path.name}\n→ {url_str}\n→ 放サボ列(オレンジセル)の手入力をお願いします")
    return True


def parse_scheduled_send(value: str) -> Optional[datetime]:
    """frontmatter `scheduled_send: YYYY-MM-DDTHH:MM+09:00` をパース"""
    if not value:
        return None
    try:
        # Python 3.11+ で fromisoformat が +09:00 を解釈可
        return datetime.fromisoformat(value)
    except Exception:
        return None


def reset_test_status(board_path: Path) -> None:
    """status: test → status: pending に戻す + テスト送信履歴を末尾に追記"""
    try:
        text = board_path.read_text(encoding="utf-8")
        # frontmatter の status 行だけ書き換え
        new_text = re.sub(r"^status:\s*test\s*$", "status: pending", text, count=1, flags=re.MULTILINE)
        # 末尾に履歴追記(同じファイルに何度もテスト送信できるよう)
        timestamp = datetime.now(JST).isoformat()
        history_line = f"\n<!-- test_sent_at: {timestamp} -->\n"
        new_text += history_line
        board_path.write_text(new_text, encoding="utf-8")
        log(f"[{board_path.name}] status: test → pending(履歴追記)")
    except Exception as e:
        log(f"[{board_path.name}] WARN: reset_test_status error: {e}")


def process_one(board_path: Path) -> None:
    try:
        text = board_path.read_text(encoding="utf-8")
    except Exception as e:
        log(f"[{board_path.name}] FAIL: read error: {e}")
        return

    fm, body = parse_frontmatter(text)
    status = fm.get("status", "").strip()
    if status not in ("approved", "test"):
        return  # 静かにスキップ

    from_seed = fm.get("from_seed", "").strip()

    # scheduled_send 解釈(approved のみ、test は即時送信)
    if status == "approved":
        sched = parse_scheduled_send(fm.get("scheduled_send", "").strip())
        if sched:
            now = datetime.now(JST)
            if now < sched:
                # 静かに skip(次の cron 起動で再評価)
                return

    log(f"[{board_path.name}] {status} detected: from_seed={from_seed}")

    is_test = (status == "test")

    if from_seed in DISPATCH_LINE_SEND:
        group = "personal" if is_test else "staff"
        ok = dispatch_line_send(fm, body, board_path, group=group)
    elif from_seed in DISPATCH_SHELL:
        if is_test:
            # shell 実行(集計など) は test 対応しない
            log(f"[{board_path.name}] WARN: status: test は shell dispatch では未対応(approved にしてください)")
            notify_master(f"⚠️ shell 種は status: test 非対応: {board_path.name}\n→ 集計などは approved で実行されます")
            return
        ok = dispatch_shell(fm, body, board_path)
    else:
        log(f"[{board_path.name}] FAIL: unknown from_seed: {from_seed}")
        notify_master(f"❌ 未知の from_seed: {board_path.name}\n→ {from_seed}")
        return

    if ok:
        if is_test:
            # テスト送信は pending に戻す(本配信は別途 approved で)
            reset_test_status(board_path)
        else:
            BOARD_PROCESSED.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(board_path), BOARD_PROCESSED / board_path.name)
                log(f"[{board_path.name}] moved to processed/")
            except Exception as e:
                log(f"[{board_path.name}] WARN: move error: {e}")


def load_env() -> None:
    """garden-gaku-co/.env を読み込む(python-dotenv 非依存の最小実装)"""
    env_path = SCRIPT_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def acquire_lock() -> bool:
    """並行実行防止(crontab で 1 分毎起動なので、長時間処理に被ったら次を skip)"""
    if LOCK_FILE.exists():
        # stale lock 判定: 30 分以上前なら無効
        try:
            mtime = LOCK_FILE.stat().st_mtime
            if (datetime.now().timestamp() - mtime) < 30 * 60:
                return False
            LOCK_FILE.unlink()
        except Exception:
            pass
    try:
        LOCK_FILE.write_text(str(os.getpid()))
        return True
    except Exception:
        return False


def release_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def main() -> None:
    load_env()

    if not acquire_lock():
        return  # 静かに

    try:
        if not BOARD_PENDING.exists():
            return
        for path in sorted(BOARD_PENDING.glob("*.md")):
            process_one(path)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
