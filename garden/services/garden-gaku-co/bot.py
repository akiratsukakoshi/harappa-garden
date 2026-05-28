#!/usr/bin/env python3
"""garden-gaku-co — 会話 bot(段3 / 朝の対話の入口).

discord.py の常駐 gateway。master channel(#秘書)でのガクチョの発言に、
G-gaku-co のペルソナ + 今日の Garden 文脈 + 直近の会話履歴 を踏まえて返信する。
gateway に常時接続するので bot は Discord 上で「オンライン」表示になる。

- 頭脳: ホストの claude(サブスク認証)を subprocess で呼ぶ。
  --strict-mcp-config で MCP を読まず軽量化、--system-prompt にペルソナ、--model sonnet。
  --bare は OAuth を無効化する(API key 専用になる)ので使わない。
- v1 は read-only(文脈は Python が MD を読んで prompt に同梱)。タスク更新は次段。
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

PERSONA = open(os.path.join(HERE, "persona", "g-gaku-co.md"), encoding="utf-8").read()
HISTORY_TURNS = 12  # 直近 N 発話を文脈に含める(プロセス内)
history = collections.defaultdict(lambda: collections.deque(maxlen=HISTORY_TURNS))


def read_garden_context() -> str:
    """今日の active_tasks と board/triage を read-only で読み、文脈にする。"""
    parts = []
    active = os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")
    if os.path.exists(active):
        parts.append("## active_tasks.md\n" + open(active, encoding="utf-8").read())
    triage_dir = os.path.join(MIRROR_DIR, "garden", "board", "triage")
    if os.path.isdir(triage_dir):
        for name in sorted(os.listdir(triage_dir)):
            if name.endswith(".md"):
                parts.append(
                    f"## board/triage/{name}\n"
                    + open(os.path.join(triage_dir, name), encoding="utf-8").read()
                )
    return "\n\n".join(parts)[:6000]  # 長すぎる場合は安全に切る


def ask_claude(channel_id: int, user_text: str) -> str:
    ctx = read_garden_context()
    convo = "\n".join(history[channel_id])
    now = datetime.datetime.now(JST)
    weekday = WEEKDAY_JA[now.weekday()]
    prompt = (
        "あなたは Discord で庭師ガクチョと会話しています。\n\n"
        + f"[現在] {now:%Y/%m/%d} ({weekday}) {now:%H:%M} JST — これが「今」。日付はこの[現在]を信じる。\n"
        + "  ※ active_tasks は夜のレビュー後だと翌日のテンプレになっていることがある(見出しの日付を今日と誤認しない)。\n\n"
        + (f"[Garden の状況]\n{ctx}\n\n" if ctx else "")
        + (f"[これまでの会話]\n{convo}\n\n" if convo else "")
        + f"[ガクチョの新しい発言]\n{user_text}\n\n"
        + "上記を踏まえ、ガクコとして返答してください。簡潔に、自然に。\n"
        + "挨拶には自然に挨拶で返す。未処理の確認事項があっても、いきなり yes/no を畳みかけず、必要なら軽く触れる程度に。\n"
        + "（重要）ファイル読み取りやコマンド等のツールは使わない。上の文脈と会話だけを根拠に答える。"
        + "文脈に無いことは無理に調べず、必要なら『その情報は手元にない。教えて』と返す。"
    )
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--system-prompt", PERSONA,
        "--strict-mcp-config",
        # v1 は read-only 会話。ツールを使わせない(文脈は上で注入済み)
        "--disallowedTools", "Bash Edit Read Write Glob Grep WebFetch WebSearch NotebookEdit TodoWrite Task",
        "--model", "sonnet",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=150, cwd=HERE)
    except subprocess.TimeoutExpired:
        return "(考えるのに時間がかかりすぎました。もう一度送ってください)"
    if proc.returncode != 0:
        return f"(内部エラー: claude rc={proc.returncode})"
    return proc.stdout.strip() or "(返答が空でした)"


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


client.run(TOKEN)
