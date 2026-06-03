#!/usr/bin/env python3
"""garden-gaku-co — 会話 bot(段3 / 朝の対話の入口).

discord.py の常駐 gateway。master channel(#秘書)でのガクチョの発言に、
G-gaku-co のペルソナ + 今日の Garden 文脈 + 直近の会話履歴 を踏まえて返信する。
gateway に常時接続するので bot は Discord 上で「オンライン」表示になる。

- 頭脳: ホストの claude(サブスク認証)を subprocess で呼ぶ。
  --strict-mcp-config で MCP を読まず軽量化、--system-prompt にペルソナ、--model sonnet。
  --bare は OAuth を無効化する(API key 専用になる)ので使わない。
- 文脈は Python が MD を読んで prompt に同梱。さらに明確な指示があれば claude が
  active_tasks / backlog / triage board を Read+Edit して**書き戻す**(settings.json で
  garden-mirror/{hmc_tasks,garden} に path-scoped allow。Bash 等は禁止)。
- 会話継続: チャンネルごとに直近の発話を保持(プロセス内メモリ。永続記憶は後段で gaku-co から移植)。
"""
import asyncio
import collections
import datetime
import os
import subprocess
import traceback

import discord

import memory_logger

JST = datetime.timezone(datetime.timedelta(hours=9))
WEEKDAY_JA = "月火水木金土日"

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
MASTER_CHANNEL_ID = int(os.environ["DISCORD_MASTER_CHANNEL_ID"])
MIRROR_DIR = os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
HERE = os.path.dirname(os.path.abspath(__file__))
# Garden CHARTER(全 plot 共通の業務観・呼称・トーン・Output Style 質感)+ daily-pilot SKILL
# (本区画固有の手順・ファイル・判断ルール)を二段で同梱。SKILL は CHARTER を継承する。
# S30: mtime ベースの動的キャッシュ(_FileCache)に切り替え、編集 → 次 turn で反映
# (bot 再起動不要)。
CHARTER_PATH = os.environ.get(
    "GARDEN_CHARTER",
    "/home/vps-harappa/garden/CHARTER.md",
)
SKILL_PATH = os.environ.get(
    "DAILY_PILOT_SKILL",
    "/home/vps-harappa/garden/plots/daily-pilot/SKILL.md",
)

PERSONA_PATH = os.path.join(HERE, "persona", "g-gaku-co.md")
HISTORY_TURNS = 12  # 直近 N 発話を文脈に含める(プロセス内)
history = collections.defaultdict(lambda: collections.deque(maxlen=HISTORY_TURNS))


class _FileCache:
    """単一ファイルの mtime を見て、変わっていれば再読み込みする最小キャッシュ。

    S30: bot 再起動なしで SKILL/CHARTER/PERSONA の編集を反映させるための仕組み。
    I/O は mtime check の 1 stat だけ。中身が変わっていなければ Read しない。
    """

    def __init__(self, path: str):
        self.path = path
        self._mtime: float | None = None
        self._content: str = ""

    def get(self) -> str:
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError:
            return self._content  # ファイル消失時は最後の中身を維持(過敏な落とし方を避ける)
        if self._mtime is None or mtime > self._mtime:
            try:
                self._content = open(self.path, encoding="utf-8").read()
                self._mtime = mtime
            except OSError:
                pass  # I/O 失敗時は既存の content を維持
        return self._content


class _DirCache:
    """ディレクトリ内 `.md` 群を「全ファイルの最大 mtime」で監視・再読み込み。

    index_first: 該当する名前のファイルを先頭に置く(memory wiki の index.md 等)。
    """

    def __init__(self, dir_path: str, label_prefix: str = "", index_first: str | None = None):
        self.dir_path = dir_path
        self.label_prefix = label_prefix
        self.index_first = index_first
        self._mtime: float | None = None
        self._content: str = ""

    def get(self) -> str:
        try:
            files = sorted([
                f for f in os.listdir(self.dir_path)
                if f.endswith(".md") and not f.startswith(".")
            ])
        except FileNotFoundError:
            return self._content
        if not files:
            self._content = ""
            self._mtime = None
            return ""
        max_mtime = max(
            os.path.getmtime(os.path.join(self.dir_path, f)) for f in files
        )
        if self._mtime is not None and max_mtime <= self._mtime:
            return self._content
        parts = []
        order: list[str] = []
        if self.index_first and self.index_first in files:
            order.append(self.index_first)
        order.extend(f for f in files if f != self.index_first)
        for name in order:
            try:
                parts.append(
                    f"## {self.label_prefix}{name}\n"
                    + open(os.path.join(self.dir_path, name), encoding="utf-8").read()
                )
            except OSError:
                continue
        self._content = "\n\n".join(parts)
        self._mtime = max_mtime
        return self._content


class _MemoryPastRawCache:
    """memory raw の過去 N 日(today 除く)を、対象日 + ファイル mtime で再読み込み。

    日またぎ(対象日集合が変わった)or ingest-raw による frontmatter 書き換え(mtime 変化)で
    再ロード。bot 再起動なしで自動追随。
    """

    def __init__(self, raw_dir: str, days: int, label_prefix: str = "raw/"):
        self.raw_dir = raw_dir
        self.days = days
        self.label_prefix = label_prefix
        self._date: datetime.date | None = None
        self._mtime: float | None = None
        self._content: str = ""

    def get(self, today: datetime.date) -> str:
        target: list[tuple[datetime.date, str]] = []
        for delta in range(self.days, 0, -1):
            d = today - datetime.timedelta(days=delta)
            path = os.path.join(self.raw_dir, f"{d.isoformat()}.md")
            if os.path.exists(path):
                target.append((d, path))
        if not target:
            self._content = ""
            self._date = today
            self._mtime = None
            return ""
        max_mtime = max(os.path.getmtime(p) for _, p in target)
        if (
            self._date == today
            and self._mtime is not None
            and max_mtime <= self._mtime
        ):
            return self._content
        parts = []
        for d, path in target:
            try:
                parts.append(
                    f"## {self.label_prefix}{d.isoformat()}.md\n"
                    + open(path, encoding="utf-8").read()
                )
            except OSError:
                continue
        self._content = "\n\n".join(parts)
        self._date = today
        self._mtime = max_mtime
        return self._content


ACTIVE_PATH = os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")
BACKLOG_PATH = os.path.join(MIRROR_DIR, "hmc_tasks", "backlog.md")
# S27: board は vault 外(garden-mirror の外 = /home/vps-harappa/garden/board/)
BOARD_DIR = os.environ.get("BOARD_DIR", "/home/vps-harappa/garden/board")

# S30 Stage C: 永続記憶(memory wiki + 直近 RAW)を context にロード
# 三層分離 ADR(2026-05-31) / memory 正本ルール ADR(2026-06-03)
MEMORY_BASE = os.environ.get(
    "MEMORY_BASE",
    os.path.join(MIRROR_DIR, "garden", "memory", "master"),
)
MEMORY_WIKI_DIR = os.path.join(MEMORY_BASE, "wiki")
MEMORY_RAW_DIR = os.path.join(MEMORY_BASE, "raw")
MEMORY_RECENT_RAW_DAYS = 3      # 過去 N 日の RAW を起動時に静的ロード
MEMORY_MAX_CHARS = 30000        # 安全上限(context 肥大化防止)


def triage_board_path(d: datetime.date) -> str:
    return os.path.join(BOARD_DIR, "triage",
                        f"{d.isoformat()}-morning-briefing.md")


# S30: 動的再読み込みキャッシュ群(編集 → 次 turn で反映、bot 再起動不要)
_persona_cache = _FileCache(PERSONA_PATH)
_charter_cache = _FileCache(CHARTER_PATH)
_skill_cache = _FileCache(SKILL_PATH)
_memory_wiki_cache = _DirCache(
    MEMORY_WIKI_DIR, label_prefix="wiki/", index_first="index.md"
)
_memory_past_raw_cache = _MemoryPastRawCache(MEMORY_RAW_DIR, MEMORY_RECENT_RAW_DAYS)


def _read_memory_today_raw(today: datetime.date) -> str:
    """当日 raw/{YYYY-MM-DD}.md を毎 turn 再読み込みして返す(進行中ファイル)。"""
    path = os.path.join(MEMORY_RAW_DIR, f"{today.isoformat()}.md")
    if not os.path.exists(path):
        return ""
    try:
        return f"## raw/{today.isoformat()}.md(進行中)\n" + open(path, encoding="utf-8").read()
    except OSError:
        return ""


# 起動時ウォームアップ(最初の対話で全 Read が走る遅延を避ける + 起動エラーを早期検知)
try:
    _persona_cache.get()
    _charter_cache.get()
    _skill_cache.get()
    _memory_wiki_cache.get()
    _memory_past_raw_cache.get(datetime.datetime.now(JST).date())
except Exception:
    print("[bot] warmup load failed — running with possibly empty caches", flush=True)
    traceback.print_exc()


def read_garden_context(today: datetime.date) -> str:
    """今日の active_tasks と今日の triage board を read-only で読み、文脈にする。

    過去日の board は読まない(古い Triage を「今の判断事項」と誤認するのを防ぐ)。
    過去ログを参照したい時は会話の中で claude が Read することで取りに行く。
    """
    parts = []
    active = os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")
    if os.path.exists(active):
        parts.append("## active_tasks.md\n" + open(active, encoding="utf-8").read())
    today_board = triage_board_path(today)
    if os.path.exists(today_board):
        parts.append(
            f"## board/triage/{os.path.basename(today_board)}\n"
            + open(today_board, encoding="utf-8").read()
        )
    return "\n\n".join(parts)[:6000]  # 長すぎる場合は安全に切る


def list_pending_boards() -> list[str]:
    """S27: VPS の `garden/board/pending/` のファイル一覧を返す。

    ガクコは Bash/Glob を持たないので、shift_manager 系の承認指示
    (「ダミーテスト承認」「シフト募集 OK」等)が来たとき
    どの board を編集すべきかを特定できるよう、prompt に事前注入する。
    """
    pending_dir = os.path.join(BOARD_DIR, "pending")
    try:
        return sorted([
            f for f in os.listdir(pending_dir)
            if f.endswith(".md") and not f.startswith(".")
        ])
    except Exception:
        return []


def build_dialogue_prompt(convo: str, user_text: str, now: datetime.datetime) -> str:
    ctx = read_garden_context(now.date())
    weekday = WEEKDAY_JA[now.weekday()]
    pending_boards = list_pending_boards()
    pending_block = ""
    if pending_boards:
        pending_block = (
            "[現在 pending 中の board(ガクチョが Discord で「承認」「テスト送って」等と"
            "言うときの候補ファイル群。フルパス: " + os.path.join(BOARD_DIR, "pending") + "/)]\n"
            + "\n".join(f"- {b}" for b in pending_boards)
            + "\n承認応答ルールの詳細は "
            + "/home/vps-harappa/garden/plots/shift_manager/SKILL.md の Mode 5 を Read。\n\n"
        )
    # S30: 永続記憶 = wiki + 過去 RAW(mtime 動的キャッシュ)+ 当日 RAW(毎 turn 再読み込み)
    memory_wiki = _memory_wiki_cache.get()
    memory_past_raw = _memory_past_raw_cache.get(now.date())
    memory_today = _read_memory_today_raw(now.date())
    memory_block = "\n\n".join(
        p for p in (memory_wiki, memory_past_raw, memory_today) if p
    )[:MEMORY_MAX_CHARS]
    return (
        "あなたは Discord master channel で庭師ガクチョと会話しています。\n"
        "判断知識は CHARTER(Garden 全 plot 共通の業務観・呼称・トーン・Output Style 質感)と "
        "daily-pilot SKILL(本区画固有の手順・ファイル・判断ルール)の二段で集約されています。\n"
        "両方に従って返答してください。SKILL は CHARTER を継承します。\n"
        "編集権限の表 (active / backlog / board / スケジュール) は SKILL の Mode 2 を厳守。\n\n"
        + "──── Garden CHARTER ────\n"
        + _charter_cache.get()
        + "\n──── CHARTER ここまで ────\n\n"
        + "──── daily-pilot SKILL ────\n"
        + _skill_cache.get()
        + "\n──── SKILL ここまで ────\n\n"
        + f"[現在] {now:%Y/%m/%d} ({weekday}) {now:%H:%M} JST — これが「今」。日付はこの[現在]を信じる。\n"
        + "  ※ active_tasks は夜のレビュー後だと翌日のテンプレになっていることがある(見出しの日付を今日と誤認しない)。\n\n"
        + f"[操作対象ファイル(SKILL の編集権限表に従って使う)]\n"
        + f"- active_tasks: {ACTIVE_PATH}\n"
        + f"- backlog(締切の正本): {BACKLOG_PATH}\n"
        + f"- 今日の Triage board: {triage_board_path(now.date())}\n"
        + f"- board pending ディレクトリ: {os.path.join(BOARD_DIR, 'pending')}/\n\n"
        + pending_block
        + (f"[Garden の状況(現時点)]\n{ctx}\n\n" if ctx else "")
        + (
            "[直近の記憶(memory wiki + 最近 RAW、mtime 動的キャッシュ + 当日は毎 turn 最新)]\n"
            "※ 過去の判断・対話の振り返り。今と矛盾する古い記述は今の発言を優先。\n"
            f"{memory_block}\n\n"
            if memory_block else ""
        )
        + (f"[これまでの会話]\n{convo}\n\n" if convo else "")
        + f"[ガクチョの新しい発言]\n{user_text}\n\n"
        + "返答は SKILL の Output Style と persona に従って簡潔・自然に。\n"
        + "編集を行ったときは「反映した: …」と一行報告(即書き＋軽い報告)。\n"
        + "普通の会話・挨拶ではファイルを触らず会話だけ返す。\n"
    )


def run_claude(prompt: str, extra_args=None) -> str:
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--system-prompt", _persona_cache.get(),
        "--strict-mcp-config",
        # Read/Edit/Write は settings.json で garden-mirror/{hmc_tasks,garden} に path-scoped allow。
        # 危険・不要なツールだけ明示的に禁止する。
        "--disallowedTools", "Bash Glob Grep WebFetch WebSearch NotebookEdit TodoWrite Task",
        "--model", "sonnet",
    ] + (extra_args or [])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=200, cwd=HERE)
    except subprocess.TimeoutExpired:
        return "(考えるのに時間がかかりすぎました。もう一度送ってください)"
    if proc.returncode != 0:
        return f"(内部エラー: claude rc={proc.returncode})"
    return proc.stdout.strip() or "(返答が空でした)"


def ask_claude(channel_id: int, user_text: str) -> str:
    convo = "\n".join(history[channel_id])
    now = datetime.datetime.now(JST)
    return run_claude(build_dialogue_prompt(convo, user_text, now))


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"[bot] online as {client.user} (master={MASTER_CHANNEL_ID})", flush=True)


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.channel.id != MASTER_CHANNEL_ID:
        return
    text = (message.content or "").strip()
    if not text:
        return
    async with message.channel.typing():
        reply = await asyncio.to_thread(ask_claude, message.channel.id, text)
    history[message.channel.id].append(f"ガクチョ: {text}")
    history[message.channel.id].append(f"ガクコ: {reply}")
    # S22 Stage A: master scope の RAW logging(対話を捨てない)
    # ADR: docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md
    try:
        memory_logger.append_turn("master", user_text=text, bot_reply=reply)
    except Exception:
        # RAW logging 失敗が対話を止めないように
        print("[bot] memory_logger.append_turn failed:", flush=True)
        traceback.print_exc()
    for i in range(0, len(reply), 1900):
        await message.channel.send(reply[i : i + 1900])


if __name__ == "__main__":
    client.run(TOKEN)
