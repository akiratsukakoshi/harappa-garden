"""sweep_client — クライアント soil の差分世話役(client_steward MVP / Mode S)。

active クライアントの `primary_domain` で Gmail を `last_synced` 以降だけ引き、
「変化と要フォロー」を digest にする。本文は Gmail に残し、soil 正本は要点 +
thread_id 参照(SKILL の機密作法)。

承認境界(SKILL):
  - 生取り込み(新メールの要点)= 自動でよい
  - 解釈(確度変更・新規案件・freee反映の断定)= board → ガクチョ剪定
  本 MVP は **digest を出すだけ**(soil への自動書き込みはしない)。append/board は次段。

認証: invoice_processor の user OAuth token を流用(新規 secret 不要)。
  - 既定 token = garden/services/invoice-processor/secrets/user_token.json
  - CLIENT_STEWARD_TOKEN / INVOICE_USER_TOKEN で上書き可

Plaud(打合せ)側の差分は MCP 越しのため本 cron サービスには含めない(homework)。
当面 Plaud はエージェントが対話時に MCP で引く(S48 と同方式)。
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# サービス相対の .env を明示ロード(cwd 非依存。launcher/cron から起動されるため)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# soil/clients の実体:ローカル(repo)は service 相対で届く。VPS は services 直下の soil が
# 空で、実体は garden-mirror 配下のため SOIL_CLIENTS_DIR で明示する(invoice の SOIL_STAFF_DIR と同型)。
DEFAULT_CLIENTS_DIR = os.path.join(REPO, "garden", "soil", "clients")
CLIENTS_DIR = os.environ.get("SOIL_CLIENTS_DIR", DEFAULT_CLIENTS_DIR)
DEFAULT_TOKEN = os.path.join(
    REPO, "garden", "services", "invoice-processor", "secrets", "user_token.json"
)
TOKEN_PATH = (
    os.environ.get("CLIENT_STEWARD_TOKEN")
    or os.environ.get("INVOICE_USER_TOKEN")
    or DEFAULT_TOKEN
)
STATE_DIR = os.path.join(os.path.dirname(__file__), "state")

# read 用途。invoice token は gmail.modify を持つので読み取り可。
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

OUR_DOMAIN = "harappa-daigaku.jp"
FINANCE_KEYWORDS = ["請求", "見積", "入金", "振込", "お支払", "支払処理", "ご請求"]
SCHEDULE_KEYWORDS = ["日程", "打ち合わせ", "打合せ", "下見", "MTG", "ミーティング", "開催", "当日"]


# ---------- frontmatter 読み(PyYAML 非依存の軽量パーサ) ----------

def read_frontmatter(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    body = text[3:end]
    out = {}
    for line in body.splitlines():
        m = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            val = re.sub(r"\s+#.*$", "", val).strip().strip('"')
            out[key] = val
    return out


def list_active_clients():
    """soil/clients/{slug}/README.md を持つ slug を列挙(primary_domain ありのみ)。"""
    found = []
    if not os.path.isdir(CLIENTS_DIR):
        return found
    for slug in sorted(os.listdir(CLIENTS_DIR)):
        readme = os.path.join(CLIENTS_DIR, slug, "README.md")
        fm = read_frontmatter(readme)
        if fm.get("primary_domain"):
            found.append((slug, fm))
    return found


# ---------- Gmail ----------

def gmail_service():
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"user token が見つかりません: {TOKEN_PATH}\n"
            "→ invoice_processor の token を流用します。secrets/user_token.json を配置してください。"
        )
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            try:
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            except OSError:
                pass
        else:
            raise RuntimeError("user token 失効。invoice_processor の issue_token.py で再発行を。")
    return build("gmail", "v1", credentials=creds)


def _headers(msg):
    out = {"Subject": "", "From": "", "Date": "", "To": ""}
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name") in out:
            out[h["name"]] = h.get("value", "")
    return out


def _parse_date(date_str):
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(date_str)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d
    except Exception:
        return None


def list_thread_ids(svc, q, page_size=100, max_pages=20):
    """threads().list を nextPageToken で辿り全 thread id を集める(S49 測量士 P2)。

    旧実装は maxResults=40 の1回きりで、41件目以降を取りこぼしたまま watermark を進めて
    いた。max_pages に達してもまだ続きがある場合は truncated=True を返し、呼び出し側で
    watermark を進めないようにする(静かな取りこぼし防止)。
    """
    ids = []
    token = None
    truncated = False
    for _ in range(max_pages):
        resp = svc.users().threads().list(
            userId="me", q=q, maxResults=page_size, pageToken=token
        ).execute()
        ids.extend(t["id"] for t in resp.get("threads", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    else:
        truncated = bool(token)
    return ids, truncated


def sweep_domain(svc, domain, since_dt, page_size=100, max_pages=20):
    """domain に関係する thread を since 以降で集め、要点と要フォロー signal を返す。

    戻り値: (threads, contacts, truncated)。truncated=True は取得上限到達=取りこぼしの可能性。
    """
    after = since_dt.strftime("%Y/%m/%d")
    q = f"(from:{domain} OR to:{domain}) after:{after}"
    thread_ids, truncated = list_thread_ids(svc, q, page_size, max_pages)

    threads = []
    contacts = {}
    for tid in thread_ids:
        tr = svc.users().threads().get(userId="me", id=tid, format="metadata",
                                       metadataHeaders=["Subject", "From", "To", "Date"]).execute()
        msgs = tr.get("messages", [])
        if not msgs:
            continue
        first_h = _headers(msgs[0])
        last = msgs[-1]
        last_h = _headers(last)
        last_dt = _parse_date(last_h["Date"])
        if last_dt and last_dt < since_dt:
            continue  # since 以降に動きがない

        # contacts(差出人の domain 一致分)
        for m in msgs:
            frm = _headers(m)["From"]
            mm = re.search(r"<([^>]+)>", frm) or re.search(r"([\w.\-+]+@[\w.\-]+)", frm)
            if mm and domain in mm.group(1).lower():
                addr = mm.group(1).lower()
                name = frm.split("<")[0].strip().strip('"') if "<" in frm else ""
                contacts.setdefault(addr, name)

        # signal: 最後の発話が先方か(=こちらが返す番)
        last_from = last_h["From"].lower()
        awaiting_us = (OUR_DOMAIN not in last_from)
        days_since = (dt.datetime.now(dt.timezone.utc) - last_dt).days if last_dt else None

        # finance/schedule シグナルは件名だけでなく本文(snippet)も見る(S49 測量士 P2)。
        # 「請求書添付しました」「7/23 でお願いします」「支払処理します」は本文側に出やすく、
        # 件名だけだと大事な変化を見落とす。snippet は metadata 取得でも各メッセージに付くので
        # 追加 API コール不要。
        subj = first_h["Subject"]
        blob = subj + " " + " ".join(m.get("snippet", "") for m in msgs)
        finance = any(k in blob for k in FINANCE_KEYWORDS)
        schedule = any(k in blob for k in SCHEDULE_KEYWORDS)

        threads.append({
            "thread_id": tid,
            "subject": subj,
            "msgs": len(msgs),
            "last_date": last_h["Date"][:22],
            "last_dt": last_dt,
            "awaiting_us": awaiting_us,
            "days_since": days_since,
            "finance": finance,
            "schedule": schedule,
        })
    threads.sort(key=lambda t: t["last_dt"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                 reverse=True)
    return threads, contacts, truncated


# ---------- digest ----------

def build_digest(slug, fm, threads, contacts, since_dt):
    lines = []
    company = fm.get("company", slug)
    lines.append(f"## {company}({fm.get('primary_domain')}) — {since_dt.date()} 以降")
    if not threads:
        lines.append("  (新しい動きなし)")
        return "\n".join(lines)

    # 要フォロー(こちらが返す番 / 一定日数放置)
    awaiting = [t for t in threads if t["awaiting_us"]]
    if awaiting:
        lines.append("\n**🔴 要フォロー(こちらが返す番)**")
        for t in awaiting:
            d = f"{t['days_since']}日" if t["days_since"] is not None else "?"
            lines.append(f"  - [{t['last_date']}] {t['subject'][:50]}({d}前・{t['msgs']}通)")

    fin = [t for t in threads if t["finance"]]
    if fin:
        lines.append("\n**💰 finance シグナル(見積/請求/入金)**")
        for t in fin:
            lines.append(f"  - [{t['last_date']}] {t['subject'][:50]} → freee 突合要")

    lines.append("\n**📨 動いたスレッド**")
    for t in threads:
        flags = []
        if t["awaiting_us"]:
            flags.append("要返信")
        if t["finance"]:
            flags.append("💰")
        if t["schedule"]:
            flags.append("📅")
        fl = (" [" + "/".join(flags) + "]") if flags else ""
        lines.append(f"  - [{t['last_date']}] {t['subject'][:50]}({t['msgs']}通){fl}")

    if contacts:
        lines.append("\n**👤 登場した担当者(署名/アドレス)**")
        for addr, name in contacts.items():
            lines.append(f"  - {name or '(名前なし)'} <{addr}>")
    return "\n".join(lines)


# ---------- 生取り込みレーン(_inbox.md への append-only) ----------
#
# 承認境界(SKILL)で「生取り込み = 自動でよい」とされたレーンの実装。emails/ は案件単位
# (projects/{案件}/emails/)で、スレッドを正しい案件に振り分ける = クラスタリング判断が要る
# (= 機械に渡せないと ADR 2026-06-18 で線引き)。そこで機械は **client 直下の整理前バッファ**
# `clients/{slug}/_inbox.md` に新着スレッドの要点だけ append し、案件への filing は人が行う。
#   - append-only(履歴を汚さない。S57 で痛感した上書き事故と無縁)
#   - thread_id で dedup(state["inbox_thread_ids"])= 一度載せた行は人が消しても再 append しない
#   - 本文は載せない(要点 + thread_id のみ。SKILL の機密作法)

INBOX_FILE = "_inbox.md"


def _inbox_header(slug, fm):
    company = fm.get("company", slug)
    return (
        "---\n"
        "type: client_inbox\n"
        f"client: {slug}\n"
        "note: machine-written(sweep が新着スレッドの要点だけ自動 append する整理前バッファ)。\n"
        "  各行を該当 projects/{案件}/emails/ に filing したら、この行は削除してよい\n"
        "  (state で dedup 済 = 再 append されない)。案件への振り分け(クラスタリング)は人。\n"
        "---\n\n"
        f"# {company} — 受信トレイ(整理前 / 自動生成)\n\n"
        "> sweep_client が `--write-inbox` で新着スレッドの要点を append。"
        "案件 README / emails/ への filing は人(クラスタリング判断のため)。\n"
    )


def append_inbox(slug, fm, threads, run_date):
    """新着スレッド(state 未記録)の要点を clients/{slug}/_inbox.md に append。

    戻り値: append した件数。soil 足場(clients/{slug}/)が無ければ 0(bootstrap 等)。
    """
    client_dir = os.path.join(CLIENTS_DIR, slug)
    if not os.path.isdir(client_dir):
        return 0  # soil 足場なし(--domain bootstrap 等)= 書かない

    state = _read_state(slug)
    seen = set(state.get("inbox_thread_ids", []))
    fresh = [t for t in threads if t["thread_id"] not in seen]
    if not fresh:
        return 0

    path = os.path.join(client_dir, INBOX_FILE)
    new_file = not os.path.exists(path)
    block = [f"\n## {run_date} sweep 着信(要 filing)\n"]
    for t in fresh:
        flags = []
        if t["awaiting_us"]:
            flags.append("要返信")
        if t["finance"]:
            flags.append("💰")
        if t["schedule"]:
            flags.append("📅")
        fl = (" [" + "/".join(flags) + "]") if flags else ""
        block.append(
            f"- [{t['last_date']}] {t['subject'][:60]}({t['msgs']}通){fl} "
            f"<!-- thread:{t['thread_id']} -->"
        )
    with open(path, "a", encoding="utf-8") as f:
        if new_file:
            f.write(_inbox_header(slug, fm))
        f.write("\n".join(block) + "\n")

    state["inbox_thread_ids"] = sorted(seen | {t["thread_id"] for t in fresh})
    _write_state(slug, state)
    return len(fresh)


# ---------- state(watermark + inbox dedup) ----------

def _state_path(slug):
    return os.path.join(STATE_DIR, f"{slug}.json")


def _read_state(slug):
    """slug の state を dict で返す(last_synced / inbox_thread_ids 等を相乗り保持)。"""
    path = _state_path(slug)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _write_state(slug, state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_state_path(slug), "w") as f:
        json.dump(state, f, ensure_ascii=False)


def load_watermark(slug, default_days):
    s = _read_state(slug)
    if s.get("last_synced"):
        try:
            return dt.datetime.fromisoformat(s["last_synced"])
        except Exception:
            pass
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=default_days)


def save_watermark(slug, when=None):
    """last_synced だけ更新(inbox_thread_ids 等の他キーは保持)。"""
    s = _read_state(slug)
    s["last_synced"] = (when or dt.datetime.now(dt.timezone.utc)).isoformat()
    _write_state(slug, s)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="client_steward Sweep(Gmail 差分 digest)")
    ap.add_argument("--client", help="slug(例 mti)。未指定なら全 active client")
    ap.add_argument("--domain", help="soil 足場なしで任意ドメインを直接 digest(bootstrap の素材ダンプ)。"
                                     "例 panasonic-homes.com / @panasonic-homes.com。"
                                     "横展開はこの digest を Claude が読み、手で soil 台帳を起こす(SKILL Mode B)。")
    ap.add_argument("--since", help="YYYY-MM-DD。未指定なら watermark or 既定日数前")
    ap.add_argument("--days", type=int, default=14, help="watermark 不在時の遡及日数(既定14)")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="digest を出すだけ(soil の解釈書込はしない)")
    ap.add_argument("--write-inbox", action="store_true",
                    help="新着スレッドの要点を clients/{slug}/_inbox.md に append(生取り込みレーン・"
                         "append-only・thread_id dedup)。解釈(確度/案件確定/freee)は書かない。"
                         "--domain(bootstrap)では無効。")
    ap.add_argument("--commit-watermark", action="store_true",
                    help="今回時刻を watermark に保存(次回はここから差分)")
    args = ap.parse_args()

    # 対象の決定:--domain(soil 不要の bootstrap 素材ダンプ)> --client(soil 既存)> 全 active client
    if args.domain:
        dom = args.domain.lstrip("@").strip().lower()
        targets = [(dom, {"company": f"(bootstrap) {dom}", "primary_domain": dom})]
    elif args.client:
        targets = [(args.client, read_frontmatter(
            os.path.join(CLIENTS_DIR, args.client, "README.md")))]
    else:
        targets = list_active_clients()
    if not targets or (args.client and not targets[0][1].get("primary_domain")):
        print(f"対象 client なし(primary_domain を持つ soil/clients/ が必要): {args.client}")
        return 1

    svc = gmail_service()
    print(f"# client_steward Sweep  ({dt.datetime.now().strftime('%Y-%m-%d %H:%M')})\n")
    for slug, fm in targets:
        domain = fm.get("primary_domain")
        since_dt = (dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc)
                    if args.since else load_watermark(slug, args.days))
        threads, contacts, truncated = sweep_domain(svc, domain, since_dt)
        print(build_digest(slug, fm, threads, contacts, since_dt))
        if truncated:
            print("  ⚠️ 取得上限に達した可能性 → watermark を進めません(次回も同区間を再取得)。")
        # 生取り込みレーン:新着スレッドの要点を _inbox.md に append(--domain は対象外)
        if args.write_inbox and not args.domain:
            today = args.since and dt.datetime.fromisoformat(args.since).date()
            n = append_inbox(slug, fm, threads, str(today or dt.date.today()))
            if n:
                print(f"  📥 _inbox.md に {n} 件 append(要 filing → 案件 emails/)")
        print()
        if args.commit_watermark:
            if args.domain:
                print("  (--domain は bootstrap 用 = watermark 保存なし)\n")
            elif truncated:
                print(f"  (watermark 据え置き: {slug} — truncated)\n")
            else:
                # now() で先送りせず、実際に処理した最新スレッド時刻まで進める(同日後着の
                # 取りこぼし防止)。threads は last_dt 降順ソート済 = [0] が最新。新着ゼロなら
                # 現区間に動きが無かったので now() まで進めてよい。
                newest = threads[0]["last_dt"] if threads else None
                save_watermark(slug, newest)
                shown = newest.date() if newest else "now(新着なし)"
                print(f"  (watermark 更新: {slug} → {shown})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
