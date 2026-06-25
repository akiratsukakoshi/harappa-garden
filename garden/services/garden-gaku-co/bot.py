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
import traceback

import discord

import memory_logger
from brain.runner import resolve_runner

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
# S38: expense_processor 区画。daily-pilot は常時ロード、expense は話題検知時のみ
# 追加ロードする(プロンプト肥大化を避けるルーティング)。実処理 = processor.py を
# Bash で叩く(settings.json で当該 venv の python だけ scoped allow)。
EXPENSE_SKILL_PATH = os.environ.get(
    "EXPENSE_PROCESSOR_SKILL",
    "/home/vps-harappa/garden/plots/expense_processor/SKILL.md",
)
EXPENSE_WORKDIR = "/home/vps-harappa/garden/services/expense-processor"
# expense_processor のトリガー語(ユーザー発言 or 直近会話に含まれたら SKILL を足す)。
# SKILL frontmatter topics の中から、誤検知しにくい明確な語を選ぶ。
EXPENSE_TOPICS = (
    "経費", "レシート", "領収書", "クレカ", "クレジットカード", "明細",
    "費目", "勘定科目", "freee", "Freee", "PayPay", "イオン", "コスモ",
)

# S40: shift_manager Mode 4 手動ルート(シフト回答集計)のトリガー語。
# 「シフト集計まわして」で aggregate_responses.py を直接実行できるようにする(遅れ回答の再集計用)。
SHIFT_WORKDIR = "/home/vps-harappa/garden/services/shift-manager"
SHIFT_AGG_TOPICS = ("シフト集計", "シフト確定", "アンケート集計", "回答集計")

# S41: invoice_processor 区画。expense と同じ「話題検知時のみ SKILL + 実行手段を追加ロード」方式。
# 「領収書/freee」等は expense 側のトリガーに既にあるため、請求書系の明確な語だけにする。
INVOICE_SKILL_PATH = os.environ.get(
    "INVOICE_PROCESSOR_SKILL",
    "/home/vps-harappa/garden/plots/invoice_processor/SKILL.md",
)
INVOICE_WORKDIR = "/home/vps-harappa/garden/services/invoice-processor"
INVOICE_TOPICS = ("請求書", "インボイス", "invoice", "請求漏れ", "月次支払", "支払処理")

# S42: field_assistant 区画(フィールド運営アシスタント、core_team 向け区画の master 側窓口)。
FIELD_SKILL_PATH = os.environ.get(
    "FIELD_ASSISTANT_SKILL",
    "/home/vps-harappa/garden/plots/field_assistant/SKILL.md",
)
FIELD_WORKDIR = "/home/vps-harappa/garden/services/field-assistant"
FIELD_TOPICS = (
    "名簿", "参加者", "体験者", "フィールド予定", "現場責任者", "月謝", "振替",
    "週初めリマインド", "当日ブリーフ", "天気", "風速", "降水",
)

# S45: sns_manager 区画(SNS 運用、master 窓口)。話題検知時のみ SKILL + 実行手段を追加ロード。
# 「投稿」単独は誤発火しやすいため、SNS が明確な語だけにする。
SNS_SKILL_PATH = os.environ.get(
    "SNS_MANAGER_SKILL",
    "/home/vps-harappa/garden/plots/sns_manager/SKILL.md",
)
SNS_WORKDIR = "/home/vps-harappa/garden/services/sns-manager"
SNS_TOPICS = (
    "sns", "SNS", "インスタ", "instagram", "投稿文案", "画像セレクト",
    "投稿予約", "reels", "リール", "フィード投稿", "週次レポート", "sns レポート",
)

# S47: finance 区画(財務 — 売上記帳 / データ整合性 / 財務分析、master 窓口)。
# 話題検知時のみ SKILL + 実行手段を追加ロード。財務が明確な語だけにする(「売上」単独は誤発火しやすい)。
FINANCE_SKILL_PATH = os.environ.get(
    "FINANCE_SKILL",
    "/home/vps-harappa/garden/plots/finance/SKILL.md",
)
FINANCE_WORKDIR = "/home/vps-harappa/garden/services/finance"
FINANCE_TOPICS = (
    "財務", "売上記帳", "振替伝票", "部門監査", "部門漏れ", "データ整合性",
    "未登録明細", "PL", "損益", "キャッシュフロー", "着地予測", "財務分析", "売上CSV",
)

# S49: client_steward 区画(クライアント soil の世話役、master 窓口)。話題検知時のみ
# SKILL + sweep 実行手段を追加ロード。sweep は read-only digest(soil 書込なし)。
CLIENT_SKILL_PATH = os.environ.get(
    "CLIENT_STEWARD_SKILL",
    "/home/vps-harappa/garden/plots/client_steward/SKILL.md",
)
CLIENT_WORKDIR = "/home/vps-harappa/garden/services/client-steward"
CLIENT_TOPICS = (
    "クライアント", "client", "案件", "toB", "MTI", "エムティーアイ",
)

# S54: scribe 区画(会議録の番人)。Plaud はローカル WSL の MCP トークンでのみ読めるため、
# VPS の bot は録音を読めない。「録音スイープして」を検知したら VPS にリクエストマーカーを置き、
# ローカル WSL の poll cron(scribe-poll.sh)が拾って run-local.sh を実行する(数分レイテンシ)。
SCRIBE_TOPICS = (
    "録音スイープ", "会議録まわして", "録音整理", "録音まわして",
    "会議録スイープ", "録音を整理", "録音をスイープ",
)
SCRIBE_REQUEST_MARKER = os.environ.get(
    "SCRIBE_REQUEST_MARKER",
    "/home/vps-harappa/garden/inbox/scribe/requested.flag",
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
_expense_skill_cache = _FileCache(EXPENSE_SKILL_PATH)
_invoice_skill_cache = _FileCache(INVOICE_SKILL_PATH)
_field_skill_cache = _FileCache(FIELD_SKILL_PATH)
_sns_skill_cache = _FileCache(SNS_SKILL_PATH)
_finance_skill_cache = _FileCache(FINANCE_SKILL_PATH)
_client_skill_cache = _FileCache(CLIENT_SKILL_PATH)
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
    _expense_skill_cache.get()
    _invoice_skill_cache.get()
    _sns_skill_cache.get()
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
    # S38: expense_processor は話題検知時のみ SKILL + 実行手段を追加ロード
    expense_block = ""
    if any(t in f"{convo}\n{user_text}" for t in EXPENSE_TOPICS):
        _py = f"{EXPENSE_WORKDIR}/.venv/bin/python"
        _script = f"{EXPENSE_WORKDIR}/processor.py"
        expense_block = (
            "──── expense_processor SKILL(経費区画 — 話題検知でロード)────\n"
            + _expense_skill_cache.get()
            + "\n──── expense SKILL ここまで ────\n\n"
            + "[経費の実行手段 — あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)]\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与。cd や相対パスだと拒否されます):\n"
            + f"  {_py} {_script} extract                          # input → working CSV(末尾に絶対パスを出力)\n"
            + f"  {_py} {_script} to-sheet <working_csv>           # CSV → レビュー用 Sheets タブ。REVIEW_SHEET_URL / REVIEW_TAB を出力\n"
            + f"  {_py} {_script} from-sheet <REVIEW_TAB>          # 編集済みタブ → 新 working CSV。REVIEWED_CSV を出力\n"
            + f"  {_py} {_script} upload <csv> --dry-run           # 登録内容を確認(件数・合計・Tax)\n"
            + f"  {_py} {_script} upload <csv>                     # Freee 本登録 + アーカイブ\n"
            + "  (processor.py は内部パスが絶対なので cwd 不問。各コマンドの標準出力から次の入力パス/URL を拾う)\n\n"
            + "・「経費まわして」等(Mode 2)→ extract → **to-sheet** で Sheets 化 → "
            + "board/pending/{今日}-expense-draft.md に候補一覧 + frontmatter(review_sheet_url / review_tab / working_csv)を起草 → "
            + "Discord に **Sheet URL つき**で1行通知(「件数が多ければ Sheet で直接編集、少しならチャットでも、編集したら『承認』」)。"
            + "input 空(抽出0)なら board を作らず「スキップ」通知。\n"
            + "・承認(Mode 3)→ **from-sheet <review_tab>** で編集後 CSV を取得 → その CSV を **upload --dry-run** で "
            + "件数・合計額・税区分を1行提示 → ガクチョ OK で本登録(--dry-run なし)→ board を processed/ へ移動。\n"
            + "・少量をチャットで直す場合は working CSV を Edit(working/ 配下のみ許可)して直接 upload でもよいが、"
            + "Sheet を出した後は from-sheet を正とする(二重編集を避ける)。\n"
            + "・本登録は不可逆。dry-run の確認を取らずに upload(--dry-run なし)を実行しないこと。\n\n"
        )
    # S41: invoice_processor は話題検知時のみ SKILL + 実行手段を追加ロード(expense と同方式)
    invoice_block = ""
    if any(t in f"{convo}\n{user_text}" for t in INVOICE_TOPICS):
        _ipy = f"{INVOICE_WORKDIR}/.venv/bin/python"
        _iproc = f"{INVOICE_WORKDIR}/processor.py"
        invoice_block = (
            "──── invoice_processor SKILL(請求書区画 — 話題検知でロード)────\n"
            + _invoice_skill_cache.get()
            + "\n──── invoice SKILL ここまで ────\n\n"
            + "[請求書の実行手段 — あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)]\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与。cd や相対パスだと拒否されます):\n"
            + f"  {_ipy} {_iproc} fetch                             # Gmail → Drive Inbox(FETCHED_FILES を出力。ラベルでべき等)\n"
            + f"  {_ipy} {_iproc} extract                           # Drive Inbox → working CSV(スタッフ照合つき。REVIEW_CSV を出力)\n"
            + f"  {_ipy} {_iproc} check --month YYYY-MM             # 稼働突合(請求漏れ検出。CHECK_MISSING を出力)\n"
            + f"  {_ipy} {_iproc} to-sheet <csv> --tab YYYYMM       # CSV → レビュー用 Sheets タブ(REVIEW_SHEET_URL を出力)\n"
            + f"  {_ipy} {_iproc} from-sheet <tab>                  # 編集済みタブ → 新 CSV(REVIEWED_CSV を出力)\n"
            + f"  {_ipy} {_iproc} external --month YYYY-MM --append-sheet YYYYMM  # 外部スタッフ(区分=追加)の稼働金額をタブに追記(S43。再実行は二重注意)\n"
            + f"  {_ipy} {_iproc} register --file <csv> --dry-run   # 登録内容を確認(件数・合計)\n"
            + f"  {_ipy} {_iproc} register --file <csv>             # Freee 本登録 + Gmail 処理済 + Drive 移動\n"
            + "  (processor.py は内部パスが絶対なので cwd 不問。各コマンドの標準出力から次の入力パス/URL を拾う)\n\n"
            + "・「請求書まわして」等(Mode 1)→ fetch → extract(0件なら「スキップ」通知で終了)→ "
            + "check --month {前月} → to-sheet --tab {前月YYYYMM} → "
            + "board/pending/{今日}-invoice-draft.md に候補一覧 + frontmatter(target_month / working_csv / review_sheet_url / review_tab)を起草 → "
            + "Discord に **Sheet URL + 請求漏れリスト** つきで通知(漏れの人への催促はガクチョの領分、自動催促しない)。\n"
            + "・承認(Mode 2)→ **from-sheet <review_tab>** で編集後 CSV を取得 → **register --dry-run** で "
            + "件数・合計額を1行提示 → ガクチョ OK で本登録(--dry-run なし)→ board を processed/ へ移動。\n"
            + "・本登録は不可逆。dry-run の確認を取らずに register(--dry-run なし)を実行しないこと。\n\n"
        )
    # S42: field_assistant(フィールド運営アシスタント)— 話題検知時のみ実行手段を追加ロード
    field_block = ""
    if any(t in f"{convo}\n{user_text}" for t in FIELD_TOPICS):
        _fpy = f"{FIELD_WORKDIR}/.venv/bin/python"
        _fproc = f"{FIELD_WORKDIR}/processor.py"
        field_block = (
            "──── field_assistant SKILL(フィールド運営区画 — 話題検知でロード)────\n"
            + _field_skill_cache.get()
            + "\n──── field SKILL ここまで ────\n\n"
            + "[フィールド運営の実行手段 — あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)]\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与):\n"
            + f"  {_fpy} {_fproc} roster --date YYYY-MM-DD             # 参加者名簿(テキスト)\n"
            + f"  {_fpy} {_fproc} roster --date YYYY-MM-DD --to-sheet  # + フル名簿をスプシ出力(URL を出力)\n"
            + f"  {_fpy} {_fproc} weekly --dry-run                     # 週初めリマインドのプレビュー\n"
            + f"  {_fpy} {_fproc} brief --date YYYY-MM-DD --dry-run    # D-2 ブリーフのプレビュー\n"
            + f"  {_fpy} {_fproc} furikae --month YYYY-MM --dry-run    # 月謝未消化チェックのプレビュー\n"
            + f"  {_fpy} {_fproc} weather --place <会場名/地名> --date YYYY-MM-DD  # 天気・気温・風(16日先まで。地名は何でも可)\n"
            + "・「○日の名簿出して」→ roster。アレルギー・連絡先などフル詳細を求められた時だけ --to-sheet。\n"
            + "・「○○の□日の天気は?」→ weather(「あさって」等は日付に変換してから)。\n"
            + "・--dry-run なしの weekly / brief / furikae は LINE core_team へ実配信される。"
            + "ガクチョの明示依頼なしに実配信しないこと。\n"
            + "・この区画は read-only(STORES API は参照系のみ)。Freee や金額の話は expense/invoice 区画の領分。\n\n"
        )
    # S45: sns_manager(SNS 運用)— 話題検知時のみ SKILL + 実行手段を追加ロード(master 窓口)
    sns_block = ""
    if any(t in f"{convo}\n{user_text}" for t in SNS_TOPICS):
        _npy = f"{SNS_WORKDIR}/.venv/bin/python"
        _nproc = f"{SNS_WORKDIR}/processor.py"
        sns_block = (
            "──── sns_manager SKILL(SNS 運用区画 — 話題検知でロード)────\n"
            + _sns_skill_cache.get()
            + "\n──── sns SKILL ここまで ────\n\n"
            + "[SNS の実行手段 — あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)]\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与):\n"
            + f"  {_npy} {_nproc} fetch-images --week YYYY-MM-DD     # Drive 候補画像を DL(その週の月曜)\n"
            + f"  {_npy} {_nproc} report [--dry-run]                 # 先週の Meta Insights → Sheet + MD レポート\n"
            + f"  {_npy} {_nproc} schedule --image PATH --caption-file PATH --publish-at YYYY-MM-DDTHH:MM:SS [--platform both|ig|fb] [--dry-run]\n"
            + f"     カルーセルは --image の代わりに --images 'a.jpg,b.jpg'(2〜10 枚。IG=カルーセル / FB=アルバム[複数写真])\n"
            + "・イレギュラー単発(「明日 20 時にこの画像で投稿作って」等)も可 = --publish-at に任意日時。週次カレンダーに縛られない(SKILL Mode A3)。\n"
            + "・「画像セレクトして」→ fetch-images → DL 画像を Read で見て火(B 既存共感)・土(A/C 交互)用 2 枚を選定 → "
            + "board/pending/{今日}-sns-select.md に描写・選定理由・一言コメント欄つきで起草 → Discord 通知。\n"
            + "・「文案作って」→ 承認済の sns-select board(画像+一言コメント)を読む → ガクチョー文体で火・土の文案 → "
            + "board/pending/{今日}-sns-caption.md に起草 → Discord 通知。⭐一言コメントを必ず起点に、ゼロから創作しない。\n"
            + "・承認 → 各投稿について schedule で IG(ig_scheduler 経由)+ FB に予約(火 20:00 / 土 8:00)。"
            + "承認前に予約しない(外部公開は不可逆)。\n"
            + "・「先週の SNS レポート」→ report。標準出力の MD レポートをそのまま提示。\n"
            + "・文体は SNS_STRATEGY.md と SKILL の文体ルール厳守(塚越が著者・Garden が整形者)。\n\n"
        )
    # S47: finance(財務 — 売上記帳 / データ整合性 / 財務分析)— 話題検知時のみ SKILL + 実行手段を追加ロード(master 窓口)
    finance_block = ""
    if any(t in f"{convo}\n{user_text}" for t in FINANCE_TOPICS):
        _fipy = f"{FINANCE_WORKDIR}/.venv/bin/python"
        finance_block = (
            "──── finance SKILL(財務区画 — 話題検知でロード)────\n"
            + _finance_skill_cache.get()
            + "\n──── finance SKILL ここまで ────\n\n"
            + "[財務の実行手段 — あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)]\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与。cd や相対パスだと拒否されます):\n"
            + "・Mode I 売上記帳(書込):\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/importer.py fetch                       # Drive 売上CSV → input/\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/importer.py generate --month YYYY-MM   # input → 振替伝票候補 review CSV(入金ベース=全行をその月末起票。REVIEW_CSV/EXTRACT_ROWS/SECTION_MISSING)\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/importer.py to-sheet <csv> --tab YYYYMM # レビュー用 Sheets(REVIEW_SHEET_URL / REVIEW_TAB)\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/importer.py from-sheet <tab>            # 編集後タブ → CSV(REVIEWED_CSV)\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/importer.py register <csv> --dry-run    # 振替伝票の件数・合計を確認\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/importer.py register <csv>              # Freee 本登録(manual_journal)+ Drive 原本を processed へ\n"
            + "・Mode D データ整合性(書込・破壊的):\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/auditor.py scan --month YYYY-MM         # 部門漏れ + 未登録明細(AUDIT_MISSING / AUDIT_CSV / UNREGISTERED_TXNS)\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/auditor.py to-sheet <csv> --tab audit YYYYMM\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/auditor.py from-sheet <tab>\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/auditor.py apply <csv> --dry-run        # PUT 内容を確認(必須)\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/auditor.py apply <csv>                  # 部門を Freee に反映(PUT /deals。ロールバック無し)\n"
            + "・Mode A 財務分析(read-only):\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/analyzer.py check|pl|cf|summary         # データ品質 / PL / CF / サマリー(SUMMARY_JSON)\n"
            + f"  {_fipy} {FINANCE_WORKDIR}/analyzer.py targets --set-revenue N --set-operating-profit N\n\n"
            + "・「売上記帳まわして」(Mode I)→ fetch → generate(0件なら「スキップ」通知)→ to-sheet → "
            + "board/pending/{今日}-sales-import.md に候補 + frontmatter(target_month / review_csv / review_sheet_url / review_tab)→ "
            + "Discord に **Sheet URL** つきで通知。承認 → from-sheet → register --dry-run → 本登録。\n"
            + "・「部門監査まわして」「データ整合性チェック」(Mode D)→ scan → 部門漏れあれば to-sheet + board、"
            + "未登録明細は status 内訳を board に出す。承認 → from-sheet → apply --dry-run → 本適用。\n"
            + "・「財務見せて」「PL見せて」「キャッシュ大丈夫?」(Mode A)→ summary / pl / cf を叩き、"
            + "SKILL の議論フレームに沿って数値+論点で投げかける(read-only)。\n"
            + "・Freee 書込(register / apply)は不可逆。**必ず dry-run の確認を取ってから**本実行。未登録明細の自動登録は当面しない。\n\n"
        )
    # S49: client_steward(クライアント soil の世話役)— 話題検知時のみ SKILL + sweep 実行手段(master 窓口)
    client_block = ""
    if any(t in f"{convo}\n{user_text}" for t in CLIENT_TOPICS):
        _cspy = f"{CLIENT_WORKDIR}/.venv/bin/python"
        _cssweep = f"{CLIENT_WORKDIR}/sweep_client.py"
        client_block = (
            "──── client_steward SKILL(クライアント区画 — 話題検知でロード)────\n"
            + _client_skill_cache.get()
            + "\n──── client_steward SKILL ここまで ────\n\n"
            + "[クライアントの実行手段 — あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)]\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与):\n"
            + f"  {_cspy} {_cssweep}                                  # 全 active client の差分 digest(read-only)\n"
            + f"  {_cspy} {_cssweep} --client mti --since YYYY-MM-DD  # 1社・指定日以降の digest\n"
            + f"  {_cspy} {_cssweep} --commit-watermark               # 週次種が使う差分同期(watermark を進める)\n\n"
            + "・「クライアント見て」「MTI どうなってる」→ sweep を read-only で叩き、digest(要フォロー / "
            + "finance シグナル / 動いたスレッド / 登場担当者)を提示。\n"
            + "・soil への書込・確度変更・新規案件確定・freee反映の断定は **しない**(board → ガクチョ剪定)。\n"
            + "・手動の対話確認では --commit-watermark を付けない(週次種だけが watermark を進める)。\n"
            + "・担当者の実名はメール署名のみ採用(Plaud 話者は採用しない)。詳細は SKILL の承認境界を厳守。\n\n"
        )
    # S54: scribe(会議録の番人)— Plaud はローカル WSL でのみ読める。VPS の bot は読めないので、
    # 「録音スイープして」を検知したら VPS にリクエストマーカーを置く(ローカル poll cron が拾って実行)。
    scribe_block = ""
    if any(t in f"{convo}\n{user_text}" for t in SCRIBE_TOPICS):
        marker_ok = False
        try:
            os.makedirs(os.path.dirname(SCRIBE_REQUEST_MARKER), exist_ok=True)
            with open(SCRIBE_REQUEST_MARKER, "a"):
                pass
            marker_ok = True
        except Exception as e:
            print(f"[scribe] request marker write failed: {e}", flush=True)
        scribe_block = (
            "[録音スイープ — scribe 区画(S54)。Plaud はローカル WSL の MCP でのみ読めます]\n"
            + (
                "✅ 依頼マーカーを VPS に置きました。ローカル WSL の poll cron(〜10分間隔)が拾って "
                "録音スイープを実行し、digest(soil 取り込み + リネーム提案)を Discord master に届けます。\n"
                if marker_ok else
                "⚠️ 依頼マーカーの設置に失敗しました。ローカル WSL で直接 run-local.sh を実行してください。\n"
            )
            + "・あなた(VPS)は Plaud に到達できないため、ここで録音を読むことはできません。\n"
            + "・ガクチョには「録音スイープの依頼を受けた。数分後に結果(soil 取り込み + リネーム提案)が届く」と一言伝えてください。\n"
            + "・日次は毎朝 07:30 にローカル cron で自動実行されます(この手動依頼は臨時実行用)。\n\n"
        )
    # S40: shift_manager Mode 4 手動ルート(シフト回答集計)— 話題検知時のみ実行手段を追加ロード
    shift_agg_block = ""
    if any(t in f"{convo}\n{user_text}" for t in SHIFT_AGG_TOPICS):
        _spy = f"{SHIFT_WORKDIR}/.venv/bin/python"
        _sagg = f"{SHIFT_WORKDIR}/aggregate_responses.py"
        shift_agg_block = (
            "[シフト回答集計 — shift_manager Mode 4 の手動ルート(S40)]\n"
            + "あなたは Bash で以下だけ実行できます(settings.json で許可済・他は不可)。\n"
            + "⚠️ 必ず **絶対パス + cd なし** で実行(権限はこの絶対パス形式にのみ付与):\n"
            + f"  {_spy} {_sagg} --month YYYY-MM                          # Forms 回答 → シフト調整シート Shift_Work_YYYY-MM タブ\n"
            + f"  {_spy} {_sagg} --month YYYY-MM --output_suffix _test    # _test タブに書く(正規タブを汚さず確認)\n"
            + "・「シフト集計まわして」→ 対象月は明示があればそれ、無ければ翌月。実行前に「◯月分を集計します」と一言宣言してから実行。\n"
            + "・既存タブには手動行・既存データを保持してマージ(再実行安全)。遅れ回答が来た後の再集計も同コマンドでよい。\n"
            + "・完了したら標準出力から件数・人数を拾い、タブ名 Shift_Work_{対象月} とあわせて1行報告。\n"
            + "・pending に monthly-shift-finalize の board がある場合は board 承認ルート(SKILL Mode 5)を優先"
            + "(status: approved 化で send_pending が実行する)。board が無い時だけ直接実行。\n"
            + "・詳細は /home/vps-harappa/garden/plots/shift_manager/SKILL.md の Mode 4 を Read。\n\n"
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
        + expense_block
        + invoice_block
        + field_block
        + sns_block
        + finance_block
        + client_block
        + scribe_block
        + shift_agg_block
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
    # S60: 直接 spawn から AgentRunner 抽象へ退避(測量士 2026-06-24 提案2)。
    # engine は GARDEN_GAKU_CO_ENGINE(既定 claude-code)。claude 固有フラグの組み立ては
    # ClaudeSubprocessRunner.build_cmd に隔離。Read/Edit/Write/Bash の OS 権限は
    # .claude/settings.json で path/entrypoint scoped(探索系・外部系は disallowed)。
    runner = resolve_runner()
    # S38: 経費の extract(Gemini OCR + 分類)が走ると 1 turn が長くなるため 300s に拡大。
    # 通常会話はすぐ返るので実害なし。gateway は asyncio.to_thread 経由なので他メッセージは生きる。
    res = runner.run(
        prompt,
        system=_persona_cache.get(),
        model="sonnet",
        disallowed_tools=["Glob", "Grep", "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite", "Task"],
        strict_mcp=True,
        cwd=HERE,
        timeout=300,
        extra_args=extra_args,
    )
    if res.error == "timeout":
        return "(考えるのに時間がかかりすぎました。もう一度送ってください)"
    if not res.ok:
        return f"(内部エラー: claude rc={res.returncode})"
    return res.text or "(返答が空でした)"


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
