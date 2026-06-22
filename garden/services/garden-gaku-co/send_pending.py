#!/usr/bin/env python3
"""send_pending.py — board/pending/*.md の status を検知して post_approval を実行する

cron `* * * * *` で 1 分毎起動(セッション21、(4) C 案)。

仕様(S21 + S22 dummy 化 + S24 承認依頼通知 + 連鎖解除 + S25 連続失敗ガード):
  1. garden/board/pending/*.md を scan
  2. frontmatter `status` を検出:
     - `status: pending` (S24)
         - `blocked: true` なら通知しない(まだ判断不能なため)
         - `notified_at` 未設定なら Discord master に承認依頼通知 → frontmatter に notified_at 追記で冪等化
     - `status: test` → ディスパッチ先を personal に強制 → 配信後 `status: pending` に戻す + テスト送信履歴を board 末尾に追記
     - `status: approved` → 通常ディスパッチ。ただし frontmatter `scheduled_send: YYYY-MM-DDTHH:MM+09:00` が未来なら skip(時刻到達まで待機)
  2.5. 連続失敗ガード(S25): ディスパッチ失敗時は board frontmatter に
       `fail_count` / `last_fail_at` / `last_fail_reason` を記録。
       2 回目以降は ❌ 通知を抑制(spam を止める)。
       SEND_PENDING_FAIL_THRESHOLD(default 3)回失敗した `status: approved` board は
       board/failed/{name}.FAILED.md に自動隔離し、⚠️ 通知を 1 回だけ出す。
       `status: test` は庭師の試行錯誤フェーズなので隔離せず通知だけ抑制。
       成功時は fail 系 frontmatter を掃除して clean に。
  3. ディスパッチモード判定(S22):
     - 優先順位: board frontmatter `dispatch_mode` > env `SEND_PENDING_DEFAULT_MODE` > "production"
     - `dummy` モード(from_seed ∈ DISPATCH_LINE_SEND の場合のみ適用):
       LINE 配信を行わず、Discord master に本文プレビューを流す(ガクチョが手動で LINE staff グループへコピー)
     - test mode(personal LINE)と shell 種は dummy の影響を受けない
  4. frontmatter `from_seed` に応じてディスパッチ:
     - shift_manager/monthly-shift-survey         → /api/send + /api/approve(staff LINE) / dummy 時は Discord master 流し
     - shift_manager/monthly-working-hours-confirmation → 同上
     - shift_manager/month-end-working-hours-prep → shell 実行(frontmatter.execute_command)
  5. 成功 → board を processed/ へ移動(test の場合は残置) + Discord master 通知
  6. 失敗 → pending 残置 + Discord master 通知
  7. (S24)shell 種 month-end-working-hours-prep 成功時、同 target_month の monthly-working-hours-confirmation の
     blocked を外し、scheduled_send を当日 19:00 に設定(過去なら 2 分後)→ 次の cron で pending 通知が走り承認依頼が届く

依存:
  - garden-gaku-co/.env(DISCORD_BOT_TOKEN, DISCORD_MASTER_CHANNEL_ID, GAKU_CO_API_URL,
                       SEND_PENDING_DEFAULT_MODE=dummy|production)
  - garden-gaku-co/venv

実行:
  cron */1 * * * * /home/vps-harappa/garden/services/garden-gaku-co/run-send-pending.sh
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# S27: 承認判断の客観事実(コドモン CSV 存在チェック等)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_facts

JST = timezone(timedelta(hours=9))

SCRIPT_DIR = Path(__file__).resolve().parent
GAKU_CO_API_URL = os.environ.get("GAKU_CO_API_URL", "https://bot.harappa.monster/api")
BOARD_PENDING = Path(os.environ.get("BOARD_PENDING", "/home/vps-harappa/garden/board/pending"))
BOARD_PROCESSED = Path(os.environ.get("BOARD_PROCESSED", "/home/vps-harappa/garden/board/processed"))
BOARD_FAILED = Path(os.environ.get("BOARD_FAILED", "/home/vps-harappa/garden/board/failed"))
LOG_PATH = Path(os.environ.get("SEND_PENDING_LOG", "/home/vps-harappa/garden/log/send-pending.log"))
LOCK_FILE = Path("/tmp/send-pending.lock")

# 連続失敗ガード(S25): status: approved の board がディスパッチ失敗を N 回繰り返したら
# board/failed/ に自動退避し、毎分の ❌ 通知ループを止める。閾値は env で上書き可。
try:
    FAIL_THRESHOLD = max(1, int(os.environ.get("SEND_PENDING_FAIL_THRESHOLD", "3")))
except ValueError:
    FAIL_THRESHOLD = 3

# 連続失敗時に ❌ 通知を抑制するためのモジュールフラグ + 直近失敗理由バッファ。
# notify_master は本フラグを見て ❌ 通知をスキップし、process_one が write_fail_state /
# quarantine_to_failed で reason を再利用する。
_SUPPRESS_FAIL_NOTIFY: bool = False
_LAST_FAIL_REASON: Optional[str] = None

# board 運用ルールは単一レジストリ board_registry に集約(S56 一元管理)。
# 配信ルーティングの集合もレジストリから導出する(ここで個別管理しない)。
import board_registry as breg  # noqa: E402

DISPATCH_LINE_SEND = breg.line_send_seeds()
DISPATCH_SHELL = breg.shell_seeds()


def classify_board(seed: str, fm: dict, body: str) -> tuple[str, str]:
    """board の (種別ラベル, 日本語タイトル) を返す(レジストリ委譲)。"""
    return breg.classify(seed, fm, body)


# S22: dummy 化(garden-gaku-co 統合完了までの暫定運用)
DEFAULT_DISPATCH_MODE = os.environ.get("SEND_PENDING_DEFAULT_MODE", "production").strip().lower()


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
    """## 配信本文 セクション内の最初のコードブロックを抽出

    見出しは「配信本文」を含む `## ...` 行に部分一致(S24: 装飾絵文字/補足カッコ許容)。
    例: `## 配信本文` / `## 📋 配信本文(編集可)` / `## 📨 配信本文`
    """
    sec_match = re.search(r"^##\s.*配信本文.*$", body, re.MULTILINE)
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
    """Discord master channel に庭師通知(send.py と同等)

    S25: ❌ で始まる失敗通知は、process_one が `_SUPPRESS_FAIL_NOTIFY = True` を
    立てている間は Discord に投げない(連続失敗ガード)。ただし `_LAST_FAIL_REASON`
    には常に最新の理由を残すので、自動隔離通知に再利用できる。
    """
    global _LAST_FAIL_REASON
    if content.startswith("❌"):
        _LAST_FAIL_REASON = content.replace("\n", " / ")[:300]
        if _SUPPRESS_FAIL_NOTIFY:
            return
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


def dispatch_dummy(fm: dict, body: str, board_path: Path) -> bool:
    """dummy ディスパッチ: LINE 配信せず、Discord master に本文プレビューを流す(S22)

    ガクチョが Discord で本文を受け取り、自分の手で LINE staff グループにコピーする運用。
    garden-gaku-co 統合完了までの暫定。
    """
    message = extract_send_body(body)
    if not message:
        log(f"[{board_path.name}] FAIL(dummy): 配信本文セクションのコードブロックが見つかりません")
        notify_master(f"❌ dummy 失敗: {board_path.name}\n→ ## 配信本文 内のコードブロックがありません")
        return False

    seed = fm.get("from_seed", "?")
    sched = fm.get("scheduled_send", "?")
    header = (
        f"📨 **dummy: 本配信用本文(手動コピーしてください)**\n"
        f"→ board: `{board_path.name}`\n"
        f"→ from_seed: `{seed}`\n"
        f"→ scheduled_send: `{sched}`\n"
        f"→ 宛先: LINE staff グループ\n"
        f"────────\n"
    )
    full = header + message
    # Discord メッセージは 2000 文字制限、notify_master は 1900 で truncate するため分割送信
    chunk_size = 1800
    if len(full) <= chunk_size:
        notify_master(full)
    else:
        notify_master(header + "(本文長いため分割送信)")
        # message を chunk 分割
        for i in range(0, len(message), chunk_size):
            notify_master(f"```\n{message[i:i+chunk_size]}\n```")

    log(f"[{board_path.name}] DUMMY dispatched to Discord master (seed={seed})")
    return True


# S39: execute_command の許可リスト(shell injection 対策)
# - 実行ファイルはこの prefix 配下の絶対パスのみ許可(S38 の「絶対パス規律」と整合)
# - 引数は安全な文字種のみ(シェルメタ文字を含む board は実行前に拒否)
# - 実行は shell=False(メタ文字が紛れても解釈されない二重防御)
EXEC_ALLOWED_PREFIXES = tuple(
    p for p in os.environ.get(
        "EXEC_ALLOWED_PREFIXES", "/home/vps-harappa/garden/services/"
    ).split(":") if p
)
SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9._/:=@+,-]+$")


def validate_execute_command(cmd: str) -> tuple[Optional[list], str]:
    """execute_command を検証し (argv, "") か (None, 理由) を返す"""
    try:
        argv = shlex.split(cmd)
    except ValueError as e:
        return None, f"コマンドのパースに失敗: {e}"
    if not argv:
        return None, "コマンドが空"
    exe = argv[0]
    if not exe.startswith("/") or not exe.startswith(EXEC_ALLOWED_PREFIXES):
        return None, f"実行ファイルが許可リスト外: {exe}(許可 prefix: {', '.join(EXEC_ALLOWED_PREFIXES)})"
    bad = [a for a in argv if not SAFE_ARG_RE.match(a)]
    if bad:
        return None, f"引数に許可外の文字: {bad}"
    return argv, ""


def dispatch_shell(fm: dict, body: str, board_path: Path) -> bool:
    """shell 実行ディスパッチ: frontmatter.execute_command を検証して実行(S39 allowlist 化)"""
    cmd = fm.get("execute_command")
    if not cmd:
        log(f"[{board_path.name}] FAIL: frontmatter.execute_command が空")
        notify_master(f"❌ shell 実行失敗: {board_path.name}\n→ execute_command が未設定")
        return False
    argv, reason = validate_execute_command(cmd)
    if argv is None:
        log(f"[{board_path.name}] FAIL: execute_command 検証 NG: {reason}")
        notify_master(f"❌ shell 実行拒否(allowlist): {board_path.name}\n→ {reason}")
        return False
    try:
        result = subprocess.run(
            argv,
            shell=False,
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


# S27: frontmatter に書かれる「既知の URL」フィールド。承認判断のため Discord に貼る。
KNOWN_URL_FIELDS: list[tuple[str, str]] = [
    ("working_hours_url", "📊 稼働シート"),
    ("form_url", "📝 フォーム"),
]

# 配信本文プレビューの最大文字数(Discord 2000 字制限内に収めるため余裕を持たせる)
DISCORD_BODY_PREVIEW_LIMIT = 900


def extract_known_urls(fm: dict) -> list[tuple[str, str]]:
    """frontmatter から既知の URL フィールドを拾う(label, url)。"""
    result: list[tuple[str, str]] = []
    for key, label in KNOWN_URL_FIELDS:
        v = (fm.get(key) or "").strip()
        if v:
            result.append((label, v))
    return result


def extract_checklist(body: str) -> list[str]:
    """本文から markdown チェックリスト行を抽出。`- [ ]` / `- [x]` 両方拾う。"""
    items: list[str] = []
    for line in body.split("\n"):
        if re.match(r"^\s*-\s+\[[ xX]\]\s+", line):
            items.append(line.strip())
    return items


def truncate_for_discord(text: str, limit: int = DISCORD_BODY_PREVIEW_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…(以降 {len(text) - limit} 文字省略。全文は「board 見せて」)"


def build_pending_notice(board_path: Path, fm: dict, body: str) -> str:
    """承認依頼の Discord 通知メッセージを組み立て(S27)。

    モック合意(セッション27): 種別ヘッダ + 関連URL + 客観事実 + 本文プレビュー or
    チェックリスト + ガクコへの伝え方ガイドの順。Obsidian 前提の文言は除く。
    """
    seed = (fm.get("from_seed") or "?").strip()
    target_month = (fm.get("target_month") or "").strip()
    scheduled = (fm.get("scheduled_send") or "").strip()
    is_shell = seed in DISPATCH_SHELL
    is_line_send = seed in DISPATCH_LINE_SEND

    kind, title = classify_board(seed, fm, body)

    lines: list[str] = [
        f"📋 **承認依頼: {title}**",
        f"📋 種別: {kind}",
        f"🌱 種: `{seed}`",
        f"📄 board: `{board_path.name}`",
    ]
    if target_month:
        lines.append(f"📅 対象月: `{target_month}`")
    if scheduled:
        lines.append(f"⏰ 配信予定: `{scheduled}`")
    if is_shell:
        cmd = (fm.get("execute_command") or "").strip()
        if cmd:
            lines.append(f"⚙️ 発火: `{cmd}`")

    # 既知の URL フィールド(label に絵文字含むので prefix は付けない)
    known_urls = extract_known_urls(fm)
    if known_urls:
        lines.append("")
        for label, url in known_urls:
            lines.append(f"{label}: {url}")

    # 客観事実(コドモン CSV 存在チェック等)
    try:
        facts = board_facts.collect_facts(seed, fm)
    except Exception as e:
        facts = [("(facts エラー)", str(e)[:200])]
    if facts:
        lines.append("")
        for label, value in facts:
            lines.append(f"{label}: {value}")

    # 配信本文プレビュー(LINE 配信種のみ。900 字 truncate)
    if is_line_send:
        preview = extract_send_body(body)
        if preview:
            lines.append("")
            lines.append("📝 **配信本文プレビュー**:")
            lines.append("```")
            lines.append(truncate_for_discord(preview))
            lines.append("```")
        else:
            lines.append("")
            lines.append("⚠️ 配信本文セクション(`## 配信本文` 内のコードブロック)が未検出。"
                         "承認しても dummy 失敗になります。「board 見せて」で確認してください。")

    # チェックリスト(shell 種など)
    if is_shell:
        checklist = extract_checklist(body)
        if checklist:
            lines.append("")
            lines.append("✅ **チェックリスト**(目視確認用 — 自動判定はしません):")
            for item in checklist[:10]:
                lines.append(item)
            if len(checklist) > 10:
                lines.append(f"  …他 {len(checklist) - 10} 件(全文は「board 見せて」)")

    # ガクコへの伝え方ガイド
    lines.append("")
    lines.append("──────")
    lines.append("**ガクコに自然言語で伝えてください**:")
    if is_shell:
        lines.append("✅ 承認 → 「承認」「集計まわして」「OK」")
        lines.append("❌ 却下 → 「キャンセル」「却下」「待って」")
        lines.append("👀 全文 → 「board 見せて」")
    else:
        lines.append("✅ 承認 → 「承認」「OK」(配信予定時刻に staff へ)")
        lines.append("🧪 テスト送信 → 「テスト送って」(ガクチョ個人 LINE)")
        lines.append("❌ 却下 → 「キャンセル」「却下」")
        lines.append("✏️ 編集 → 「本文の XX を YY に変えて承認」")
        lines.append("👀 全文 → 「board 見せて」")
    lines.append("(曖昧ならガクコが聞き返します)")

    return "\n".join(lines)


def notify_pending(board_path: Path, fm: dict) -> None:
    """status: pending 初回検知時に Discord master へ承認依頼通知 + frontmatter に notified_at 追記(S24/S27)

    冪等: notified_at が既にあれば呼ばれない前提(process_one 側で gating)。
    S27: 本文プレビュー + 客観事実 + ガクコへの伝え方ガイドを含む強化版。
    """
    # 本文を読む(プレビュー用)
    body = ""
    try:
        text = board_path.read_text(encoding="utf-8")
        _, body = parse_frontmatter(text)
    except Exception as e:
        log(f"[{board_path.name}] WARN: body read error: {e}")

    notice = build_pending_notice(board_path, fm, body)
    notify_master(notice)

    # frontmatter に notified_at を追記(冪等化)
    try:
        text = board_path.read_text(encoding="utf-8")
        timestamp = datetime.now(JST).isoformat()
        new_text = text.replace("\n---\n", f"\nnotified_at: {timestamp}\n---\n", 1)
        board_path.write_text(new_text, encoding="utf-8")
        log(f"[{board_path.name}] notified pending → notified_at: {timestamp}")
    except Exception as e:
        log(f"[{board_path.name}] WARN: notified_at write error: {e}")


def unblock_confirmation(target_month: str) -> None:
    """month-end-working-hours-prep 成功後、同 target_month の confirmation board の blocked を外す(S24)

    - blocked: true → blocked: false
    - scheduled_send を当日 19:00 に設定(過去なら 2 分後)
    - notified_at をリセット(削除)して、次の cron で承認依頼通知が走るようにする
    - 既に blocked: false なら何もしない(冪等)
    """
    if not target_month:
        log("[unblock] target_month empty → skip")
        return
    for path in BOARD_PENDING.glob("*-monthly-working-hours-confirmation.md"):
        try:
            text = path.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
        except Exception as e:
            log(f"[unblock] read error {path.name}: {e}")
            continue
        if fm.get("target_month", "").strip() != target_month:
            continue
        if fm.get("blocked", "").strip().lower() != "true":
            log(f"[unblock] {path.name} already unblocked → skip")
            return

        # scheduled_send 計算
        now = datetime.now(JST)
        target = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if target < now:
            target = now + timedelta(minutes=2)
        sched_str = target.strftime("%Y-%m-%dT%H:%M:%S+09:00")

        new_text = text
        new_text = re.sub(r"^blocked:\s*true\s*$", "blocked: false", new_text, count=1, flags=re.MULTILINE)
        new_text = re.sub(r"^blocked_reason:.*\n", "", new_text, count=1, flags=re.MULTILINE)
        new_text = re.sub(r"^notified_at:.*\n", "", new_text, count=1, flags=re.MULTILINE)
        if re.search(r"^scheduled_send:", new_text, flags=re.MULTILINE):
            new_text = re.sub(r"^scheduled_send:.*$", f"scheduled_send: {sched_str}", new_text, count=1, flags=re.MULTILINE)
        else:
            new_text = new_text.replace("\n---\n", f"\nscheduled_send: {sched_str}\n---\n", 1)

        try:
            path.write_text(new_text, encoding="utf-8")
            log(f"[unblock] {path.name}: blocked=false, scheduled_send={sched_str}")
            notify_master(
                f"🔓 **稼働確認票の配信ロック解除**\n"
                f"📄 board: `garden/board/pending/{path.name}`\n"
                f"⏰ scheduled_send: `{sched_str}`\n"
                f"\n次の 1 分以内に承認依頼通知が改めて届きます。"
            )
        except Exception as e:
            log(f"[unblock] write error {path.name}: {e}")
        return
    log(f"[unblock] no matching confirmation board for target_month={target_month}")


def get_fail_count(fm: dict) -> int:
    try:
        return int(fm.get("fail_count", "0"))
    except (TypeError, ValueError):
        return 0


def _upsert_frontmatter_field(text: str, key: str, value: str) -> str:
    """frontmatter の top-level スカラーを upsert(あれば書き換え、なければ末尾 --- の直前に追加)"""
    pattern = rf"^{re.escape(key)}:.*$"
    if re.search(pattern, text, flags=re.MULTILINE):
        return re.sub(pattern, f"{key}: {value}", text, count=1, flags=re.MULTILINE)
    return text.replace("\n---\n", f"\n{key}: {value}\n---\n", 1)


def write_fail_state(board_path: Path, count: int, reason: Optional[str]) -> None:
    """board frontmatter に fail_count / last_fail_at / last_fail_reason を upsert(S25)"""
    try:
        text = board_path.read_text(encoding="utf-8")
    except Exception as e:
        log(f"[{board_path.name}] WARN: write_fail_state read error: {e}")
        return
    ts = datetime.now(JST).isoformat()
    safe_reason = (reason or "(理由不明)").replace("\n", " / ").replace('"', "'")[:300]
    text = _upsert_frontmatter_field(text, "fail_count", str(count))
    text = _upsert_frontmatter_field(text, "last_fail_at", ts)
    text = _upsert_frontmatter_field(text, "last_fail_reason", f'"{safe_reason}"')
    try:
        board_path.write_text(text, encoding="utf-8")
    except Exception as e:
        log(f"[{board_path.name}] WARN: write_fail_state write error: {e}")


def clear_fail_state(board_path: Path) -> None:
    """成功時 / 隔離前に fail_count 系 frontmatter を削除(S25)"""
    try:
        text = board_path.read_text(encoding="utf-8")
    except Exception as e:
        log(f"[{board_path.name}] WARN: clear_fail_state read error: {e}")
        return
    changed = False
    for key in ("fail_count", "last_fail_at", "last_fail_reason"):
        new_text = re.sub(rf"^{re.escape(key)}:.*\n", "", text, count=1, flags=re.MULTILINE)
        if new_text != text:
            changed = True
            text = new_text
    if changed:
        try:
            board_path.write_text(text, encoding="utf-8")
        except Exception as e:
            log(f"[{board_path.name}] WARN: clear_fail_state write error: {e}")


def quarantine_to_failed(board_path: Path, count: int, reason: Optional[str]) -> None:
    """連続失敗 board を board/failed/{name}.FAILED.md に移動 + Discord 通知(S25)

    既に同名がある場合はタイムスタンプを追記して衝突回避。退避通知は ❌ ではなく ⚠️ で
    プレフィクスを変えるので、`_SUPPRESS_FAIL_NOTIFY` の影響を受けない。
    """
    BOARD_FAILED.mkdir(parents=True, exist_ok=True)
    dest = BOARD_FAILED / f"{board_path.stem}.FAILED.md"
    if dest.exists():
        ts = datetime.now(JST).strftime("%Y%m%dT%H%M%S")
        dest = BOARD_FAILED / f"{board_path.stem}.FAILED.{ts}.md"
    try:
        shutil.move(str(board_path), dest)
    except Exception as e:
        log(f"[{board_path.name}] WARN: quarantine move error: {e}")
        return
    log(f"[{board_path.name}] auto-quarantined → {dest}")
    notify_master(
        "⚠️ **board 自動隔離(連続失敗 {count} 回)**\n"
        "→ 元: `garden/board/pending/{src}`\n"
        "→ 退避先: `garden/board/failed/{dst}`\n"
        "→ 直近の理由: {reason}\n"
        "→ 原因解消後は退避ファイルを修正して pending/ に戻すか、種を再キックして新規 board を起こしてください".format(
            count=count,
            src=board_path.name,
            dst=dest.name,
            reason=reason or "(不明)",
        )
    )


def process_one(board_path: Path) -> None:
    try:
        text = board_path.read_text(encoding="utf-8")
    except Exception as e:
        log(f"[{board_path.name}] FAIL: read error: {e}")
        return

    fm, body = parse_frontmatter(text)
    status = fm.get("status", "").strip()

    # S24: status: pending の初回検知通知(冪等)
    if status == "pending":
        if fm.get("blocked", "").strip().lower() == "true":
            return  # 判断不能のため通知しない
        if fm.get("notified_at", "").strip():
            return  # 通知済み
        notify_pending(board_path, fm)
        return

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
    fail_count = get_fail_count(fm)

    # S25 連続失敗ガード: 2 回目以降のディスパッチ試行では ❌ 通知を抑制する。
    # notify_master が prefix を見て自動で sink するので、各 dispatch_* 関数側の改修は不要。
    global _SUPPRESS_FAIL_NOTIFY, _LAST_FAIL_REASON
    _SUPPRESS_FAIL_NOTIFY = fail_count > 0
    _LAST_FAIL_REASON = None

    try:
        effective_mode = fm.get("dispatch_mode", "").strip().lower() or DEFAULT_DISPATCH_MODE

        if from_seed in DISPATCH_LINE_SEND:
            # status: test(personal LINE)は dummy の影響を受けない(自分宛なので漏洩リスクなし)
            if not is_test and effective_mode == "dummy":
                log(f"[{board_path.name}] dispatch_mode=dummy → Discord master へ流す")
                ok = dispatch_dummy(fm, body, board_path)
            else:
                group = "personal" if is_test else "staff"
                ok = dispatch_line_send(fm, body, board_path, group=group)
        elif from_seed in DISPATCH_SHELL:
            if is_test:
                # shell 実行(集計など) は test 対応しない
                log(f"[{board_path.name}] WARN: status: test は shell dispatch では未対応(approved にしてください)")
                notify_master(f"⚠️ shell 種は status: test 非対応: {board_path.name}\n→ 集計などは approved で実行されます")
                return
            ok = dispatch_shell(fm, body, board_path)
            # S24: 月末稼働表生成成功時、対応する confirmation の blocked を外す
            if ok and from_seed == "shift_manager/month-end-working-hours-prep":
                unblock_confirmation(fm.get("target_month", "").strip())
        elif breg.is_registered(from_seed):
            # 登録済みだが自動配信なし(CONVERSATIONAL=会話承認 / FYI=通知のみ)。
            # status:approved に達しても send_pending は配信しない。誤って approved に
            # された board をエラーループさせず、静かに processed/ へ片付ける(罠の解消)。
            model = breg.approval_model(from_seed)
            log(f"[{board_path.name}] {model} 種(自動配信なし)→ archive。"
                f"承認は会話/別経路。SNS 等の予約は『〜予約して』で実行")
            ok = True
        else:
            # 真の未登録 = board_registry に無い。lint で事前検知すべき構成ミス。
            log(f"[{board_path.name}] FAIL: 未登録の from_seed(board_registry に無い): {from_seed}")
            notify_master(
                f"❌ 未登録の board 種: {board_path.name}\n→ {from_seed}\n"
                f"→ board_registry.py に登録してください(board lint 参照)")
            ok = False
    finally:
        _SUPPRESS_FAIL_NOTIFY = False

    if ok:
        # 成功時は fail 系 frontmatter を掃除してから移動 / 復帰
        if fail_count > 0:
            clear_fail_state(board_path)
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
        return

    # 失敗: fail_count を 1 増やして frontmatter に記録
    new_count = fail_count + 1
    write_fail_state(board_path, new_count, _LAST_FAIL_REASON)
    log(f"[{board_path.name}] fail_count: {fail_count} → {new_count} (threshold={FAIL_THRESHOLD})")

    # status: approved の board のみ閾値到達で auto-quarantine。
    # status: test は庭師の試行錯誤フェーズなので隔離せず、通知だけ抑制して放置。
    if not is_test and new_count >= FAIL_THRESHOLD:
        quarantine_to_failed(board_path, new_count, _LAST_FAIL_REASON)


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


def iter_pending_boards():
    """pending/ の status=pending board を (path, fm, body) で古い順に yield。

    pending/ には処理済み(status=processed/registered 等)の board が混ざり得るため、
    「本当に承認待ち」だけを返す唯一の窓口にする(朝ブリーフィング・ダッシュボード共用)。
    """
    if not BOARD_PENDING.exists():
        return
    for path in sorted(BOARD_PENDING.glob("*.md")):
        if path.name == "placeholder.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        if (fm.get("status") or "").strip() != "pending":
            continue
        yield path, fm, body


def cmd_list_pending() -> None:
    """status=pending の board を markdown 一覧で stdout に出す(朝ブリーフィング/ダッシュボード共用)。"""
    rows = list(iter_pending_boards())
    if not rows:
        print("(承認待ちの board はありません)")
        return
    for path, fm, body in rows:
        seed = (fm.get("from_seed") or "?").strip()
        kind, title = classify_board(seed, fm, body)
        created = (fm.get("created") or "").strip()[:10]
        sched = (fm.get("scheduled_send") or "").strip()
        blocked = (fm.get("blocked") or "").strip().lower() == "true"
        extra = []
        if blocked:
            extra.append("⛔blocked")
        if sched:
            extra.append(f"⏰{sched}")
        suffix = (" / " + " ".join(extra)) if extra else ""
        cmark = f" / 作成 {created}" if created else ""
        print(f"- **{title}**({kind}) — `{path.name}`{cmark}{suffix}")


# 終端ステータス: pending/ に居座らせず processed/ へ片付ける(承認や配信を伴わない種も含む)
TERMINAL_STATUSES = {"processed", "registered", "done", "completed", "sent", "skipped", "scheduled"}


def relocate_terminal_boards() -> None:
    """pending/ の終端ステータス board を processed/ へ移し、pending/=承認待ち を保つ。

    pending/ に status=processed/registered が混ざると「未承認はどれか」が分からなくなる
    (実害あり)。毎分の send-pending で軽く掃除する。移動は終端 status のみ・冪等。
    """
    if not BOARD_PENDING.exists():
        return
    BOARD_PROCESSED.mkdir(parents=True, exist_ok=True)
    for path in sorted(BOARD_PENDING.glob("*.md")):
        if path.name == "placeholder.md":
            continue
        try:
            fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        status = (fm.get("status") or "").strip().lower()
        if status in TERMINAL_STATUSES:
            try:
                path.replace(BOARD_PROCESSED / path.name)
                log(f"[{path.name}] 終端 status={status} → processed/ へ片付け")
            except OSError as e:
                log(f"[{path.name}] WARN: processed/ への片付け失敗: {e}")


def main() -> None:
    load_env()

    if not acquire_lock():
        return  # 静かに

    try:
        if not BOARD_PENDING.exists():
            return
        relocate_terminal_boards()
        for path in sorted(BOARD_PENDING.glob("*.md")):
            process_one(path)
    finally:
        release_lock()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list-pending":
        try:
            load_env()
        except Exception:
            pass
        cmd_list_pending()
    else:
        main()
