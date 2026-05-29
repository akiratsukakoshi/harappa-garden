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


ACTIVE_PATH = os.path.join(MIRROR_DIR, "hmc_tasks", "active_tasks.md")
BACKLOG_PATH = os.path.join(MIRROR_DIR, "hmc_tasks", "backlog.md")


def triage_board_path(d: datetime.date) -> str:
    return os.path.join(MIRROR_DIR, "garden", "board", "triage",
                        f"{d.isoformat()}-morning-briefing.md")


def build_dialogue_prompt(convo: str, user_text: str, now: datetime.datetime) -> str:
    ctx = read_garden_context()
    weekday = WEEKDAY_JA[now.weekday()]
    board = triage_board_path(now.date())
    return (
        "あなたは Discord で庭師ガクチョと会話しています。朝の対話では、会話の結論を"
        "Garden のタスク MD に**書き戻す**ことができます。\n\n"
        + f"[現在] {now:%Y/%m/%d} ({weekday}) {now:%H:%M} JST — これが「今」。日付はこの[現在]を信じる。\n"
        + "  ※ active_tasks は夜のレビュー後だと翌日のテンプレになっていることがある(見出しの日付を今日と誤認しない)。\n\n"
        + (f"[Garden の状況(現時点)]\n{ctx}\n\n" if ctx else "")
        + (f"[これまでの会話]\n{convo}\n\n" if convo else "")
        + f"[ガクチョの新しい発言]\n{user_text}\n\n"
        + "── 返答の方針 ──\n"
        + "ガクコとして簡潔・自然に返す。挨拶には挨拶で返す。畳みかけない。\n\n"
        + "── タスク変更の書き戻し(明確な指示があった時だけ) ──\n"
        + "対象を Read してから Edit する。編集対象:\n"
        + f"- active_tasks: {ACTIVE_PATH}\n"
        + f"- backlog(締切の正本): {BACKLOG_PATH}\n"
        + f"- 今日の Triage board: {board}\n"
        + "ルール:\n"
        + "- 完了(「終わった」等): active の該当行を `- [ ]` → `- [x]`(夜の night-review が archive に転記)。\n"
        + "- 締切変更(「金曜に」「来週」等): backlog.md の該当タスクの締切を書き換える(正本)。active の `(MM/DD締切)` 表記も揃える。\n"
        + "- 追加(「〇〇追加して」): active の `## 追加` セクションに `- [ ] 〇〇` を足す。\n"
        + "- Triage への回答: board の該当 Q の選択肢にチェックを入れる。回答が新タスクを生むなら `## 追加` にも足す。\n"
        + "- 今日はやらない/後回し: active で `- [ ]` のまま(夜に自動で持ち越される)。無理に消さない。\n"
        + "- `## スケジュール`(カレンダー)は編集しない。\n"
        + "- 解釈に迷う指示は、書く前にひとこと確認する。\n"
        + "変更したら「反映した: …」と簡潔に報告(即書き＋軽い報告)。\n"
        + "普通の会話・挨拶・質問では**ファイルを編集せず**会話だけ返す。\n\n"
        + "── Triage の締め ──\n"
        + "その日の Triage を全部消化したら『今日のブリーフ、これで確定でいい?』と一度だけ確認する"
        + "(勝手に確定にしない)。ガクチョが ok 等で答えたら board の status を triage-done に更新する。\n"
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
