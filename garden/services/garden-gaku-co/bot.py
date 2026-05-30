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

import discord

JST = datetime.timezone(datetime.timedelta(hours=9))
WEEKDAY_JA = "月火水木金土日"

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
MASTER_CHANNEL_ID = int(os.environ["DISCORD_MASTER_CHANNEL_ID"])
MIRROR_DIR = os.environ.get("MIRROR_DIR", "/home/vps-harappa/garden-mirror")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
HERE = os.path.dirname(os.path.abspath(__file__))
# daily-pilot 区画 SKILL(業務観・編集ルール・Output Style の単一の真実)。
# 起動時に同梱し、対話の判断知識として claude に渡す。SKILL を更新したら bot 再起動が必要。
SKILL_PATH = os.environ.get(
    "DAILY_PILOT_SKILL",
    "/home/vps-harappa/garden/plots/daily-pilot/SKILL.md",
)

PERSONA = open(os.path.join(HERE, "persona", "g-gaku-co.md"), encoding="utf-8").read()
SKILL = open(SKILL_PATH, encoding="utf-8").read()
HISTORY_TURNS = 12  # 直近 N 発話を文脈に含める(プロセス内)
history = collections.defaultdict(lambda: collections.deque(maxlen=HISTORY_TURNS))


ACTIVE_PATH = os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")
BACKLOG_PATH = os.path.join(MIRROR_DIR, "hmc_tasks", "backlog.md")


def triage_board_path(d: datetime.date) -> str:
    return os.path.join(MIRROR_DIR, "garden", "board", "triage",
                        f"{d.isoformat()}-morning-briefing.md")


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


def build_dialogue_prompt(convo: str, user_text: str, now: datetime.datetime) -> str:
    ctx = read_garden_context(now.date())
    weekday = WEEKDAY_JA[now.weekday()]
    return (
        "あなたは Discord master channel で庭師ガクチョと会話しています。\n"
        "判断知識は下記の daily-pilot SKILL に集約されています。SKILL の "
        "**Core Philosophy / Mode 2 (Conversation) / Output Style** に従って返答してください。\n"
        "編集権限の表 (active / backlog / board / スケジュール) は SKILL の Mode 2 を厳守。\n\n"
        + "──── daily-pilot SKILL ────\n"
        + SKILL
        + "\n──── SKILL ここまで ────\n\n"
        + f"[現在] {now:%Y/%m/%d} ({weekday}) {now:%H:%M} JST — これが「今」。日付はこの[現在]を信じる。\n"
        + "  ※ active_tasks は夜のレビュー後だと翌日のテンプレになっていることがある(見出しの日付を今日と誤認しない)。\n\n"
        + f"[操作対象ファイル(SKILL の編集権限表に従って使う)]\n"
        + f"- active_tasks: {ACTIVE_PATH}\n"
        + f"- backlog(締切の正本): {BACKLOG_PATH}\n"
        + f"- 今日の Triage board: {triage_board_path(now.date())}\n\n"
        + (f"[Garden の状況(現時点)]\n{ctx}\n\n" if ctx else "")
        + (f"[これまでの会話]\n{convo}\n\n" if convo else "")
        + f"[ガクチョの新しい発言]\n{user_text}\n\n"
        + "返答は SKILL の Output Style と persona に従って簡潔・自然に。\n"
        + "編集を行ったときは「反映した: …」と一行報告(即書き＋軽い報告)。\n"
        + "普通の会話・挨拶ではファイルを触らず会話だけ返す。\n"
    )


def run_claude(prompt: str, extra_args=None) -> str:
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--system-prompt", PERSONA,
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
    for i in range(0, len(reply), 1900):
        await message.channel.send(reply[i : i + 1900])


if __name__ == "__main__":
    client.run(TOKEN)
