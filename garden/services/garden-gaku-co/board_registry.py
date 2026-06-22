"""board_registry.py — board 運用ルールの単一レジストリ(S56, 一元管理の核)。

board(剪定依頼/連絡板)の「種ごとの振る舞い」をここ1か所に集約する。
種を足す = この REGISTRY に1行足すだけ(send_pending のロジック改修は不要)。
分類(種別/タイトル)・通知・ライフサイクル・配信ルーティング・lint が全部これを参照する。

正本(人間向けの仕様書): garden/board/README.md
ADR: docs/decisions/2026-06-22-board-central-management.md

承認モデル(approval):
  - AUTO          : status:approved を立てると send_pending が dispatcher で実行(配信/集計)
  - CONVERSATIONAL: 会話で承認 → bot / Claude セッションが実行(SNS の予約・経費/請求の登録)。
                    ※ status:approved は使わない(使っても send_pending は配信せず黙って archive)
  - FYI           : 承認不要の通知だけ。表示されたら役目終わり(録音 digest・財務投げかけ等)

dispatcher(AUTO のときだけ意味を持つ):
  - "line_send" : LINE 配信(/api/send → /api/approve)
  - "shell"     : execute_command を allowlist 実行(集計など)
  - None        : 自動実行なし(CONVERSATIONAL / FYI)
"""

AUTO = "auto"
CONVERSATIONAL = "conversational"
FYI = "fyi"

# 種 → 振る舞い。kind=種別ラベル / title=日本語タイトル(board の frontmatter title: が最優先)
# title 内の {target_month} {week} は board の frontmatter 値で置換。
REGISTRY = {
    "sns_manager/saturday-image-select": {
        "kind": "📸 SNS画像セレクト", "title": "来週の SNS 投稿画像セレクト(火・土)",
        "approval": CONVERSATIONAL, "dispatcher": None},
    "sns_manager/monday-caption-draft": {
        "kind": "✍️ SNS文案", "title": "SNS 投稿の文案ドラフト",
        "approval": CONVERSATIONAL, "dispatcher": None},
    "scribe/daily-recording-sweep": {
        "kind": "🎙️ 録音スイープ", "title": "会議録の取り込み・リネーム提案",
        "approval": FYI, "dispatcher": None},
    "expense_processor/monthly-expense-draft": {
        "kind": "💰 経費ドラフト", "title": "{target_month} の経費登録",
        "approval": CONVERSATIONAL, "dispatcher": None},
    "invoice_processor/monthly-invoice-draft": {
        "kind": "🧾 請求ドラフト", "title": "{target_month} の請求登録",
        "approval": CONVERSATIONAL, "dispatcher": None},
    "client_steward/weekly-client-sweep": {
        "kind": "👥 クライアント差分", "title": "クライアント Gmail 差分の要フォロー",
        "approval": FYI, "dispatcher": None},
    "shift_manager/monthly-shift-survey": {
        "kind": "📨 シフト募集配信", "title": "{target_month} のシフト募集",
        "approval": AUTO, "dispatcher": "line_send"},
    "shift_manager/monthly-working-hours-confirmation": {
        "kind": "📨 稼働確認配信", "title": "{target_month} の稼働時間確認",
        "approval": AUTO, "dispatcher": "line_send"},
    "shift_manager/month-end-working-hours-prep": {
        "kind": "⚙️ シフト集計実行", "title": "シフト集計の実行(承認で発火)",
        "approval": AUTO, "dispatcher": "shell"},
    "shift_manager/monthly-shift-finalize": {
        "kind": "⚙️ シフト集計実行", "title": "{target_month} のシフト回答集計(承認で発火)",
        "approval": AUTO, "dispatcher": "shell"},
    "finance/monthly-sales-import": {
        "kind": "💴 売上記帳ドラフト", "title": "{target_month} の売上記帳(STORES/Square→振替伝票)",
        "approval": CONVERSATIONAL, "dispatcher": None},
    "finance/monthly-data-audit": {
        "kind": "🔍 部門監査", "title": "{target_month} のデータ監査(部門漏れ・未登録明細)",
        "approval": CONVERSATIONAL, "dispatcher": None},
    "finance/monthly-finance-review": {
        "kind": "📊 財務レビュー", "title": "{target_month} の財務確認・投げかけ",
        "approval": FYI, "dispatcher": None},
    "daily-pilot/morning-briefing": {
        "kind": "🌅 朝ブリーフィング", "title": "朝のブリーフィング(Triage)",
        "approval": FYI, "dispatcher": None},
}

# 未登録の種のフォールバック種別(plot 接頭辞から)。lint はこれに頼らず「未登録」を警告する。
PLOT_FALLBACK = {
    "sns_manager": "📸 SNS", "scribe": "🎙️ 録音", "expense_processor": "💰 経費",
    "invoice_processor": "🧾 請求", "client_steward": "👥 クライアント",
    "shift_manager": "🗓️ シフト", "finance": "📊 財務", "daily-pilot": "🌅 日次",
}

VALID_APPROVALS = {AUTO, CONVERSATIONAL, FYI}
VALID_DISPATCHERS = {None, "line_send", "shell"}


def entry(seed: str):
    return REGISTRY.get((seed or "").strip())


def is_registered(seed: str) -> bool:
    return (seed or "").strip() in REGISTRY


def kind_label(seed: str) -> str:
    e = entry(seed)
    if e:
        return e["kind"]
    plot = (seed or "").split("/", 1)[0]
    return f"{PLOT_FALLBACK.get(plot, '📋')} 承認依頼" if plot in PLOT_FALLBACK else "📋 承認依頼(剪定)"


def _fill(tmpl: str, fm: dict) -> str:
    out = tmpl
    for k in ("target_month", "week"):
        v = (fm.get(k) or "").strip()
        if v and "{" + k + "}" in out:
            out = out.replace("{" + k + "}", v)
    return out


def title_for(seed: str, fm: dict, body: str) -> str:
    import re
    t = (fm.get("title") or "").strip()
    if t:
        return t
    e = entry(seed)
    if e and e.get("title"):
        return _fill(e["title"], fm)
    m = re.search(r"^#\s+(.+)$", body or "", re.MULTILINE)
    return m.group(1).strip() if m else ((seed or "?").strip())


def classify(seed: str, fm: dict, body: str):
    """(種別ラベル, 日本語タイトル) を返す。"""
    return kind_label(seed), title_for(seed, fm, body)


def approval_model(seed: str):
    e = entry(seed)
    return e["approval"] if e else None


def dispatcher_of(seed: str):
    e = entry(seed)
    return e["dispatcher"] if e else None


def line_send_seeds() -> set:
    return {s for s, e in REGISTRY.items() if e["dispatcher"] == "line_send"}


def shell_seeds() -> set:
    return {s for s, e in REGISTRY.items() if e["dispatcher"] == "shell"}


def self_check() -> list:
    """レジストリ自身の妥当性(approval/dispatcher の値域・整合)を返す。lint が呼ぶ。"""
    problems = []
    for seed, e in REGISTRY.items():
        if e.get("approval") not in VALID_APPROVALS:
            problems.append(f"{seed}: approval 不正 ({e.get('approval')})")
        if e.get("dispatcher") not in VALID_DISPATCHERS:
            problems.append(f"{seed}: dispatcher 不正 ({e.get('dispatcher')})")
        if e.get("approval") == AUTO and e.get("dispatcher") is None:
            problems.append(f"{seed}: approval=AUTO なのに dispatcher が None")
        if e.get("approval") != AUTO and e.get("dispatcher") is not None:
            problems.append(f"{seed}: approval≠AUTO なのに dispatcher 指定あり")
        if not e.get("kind") or not e.get("title"):
            problems.append(f"{seed}: kind/title 欠落")
    return problems
