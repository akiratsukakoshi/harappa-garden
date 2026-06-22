"""board_dashboard.py — 承認待ち board の閲覧専用 HTML ダッシュボード(案1, S56)。

Discord / VPS 直見 以外から「いま何が承認待ちか」を URL で確認するための画面。
承認操作はしない(操作は Discord のまま=操作チャンネル一本化)。
データ窓口は send_pending.iter_pending_boards / classify_board に一本化(status=pending のみ)。

本文 markdown はブラウザ側(marked.js)でレンダリングして表示する(スマホで読みやすく)。
各 board は <details> で折りたためる。サーバ依存追加なし(CDN の marked.js を読むだけ)。
"""
import html
from datetime import datetime, timezone, timedelta

import send_pending as sp

JST = timezone(timedelta(hours=9))


def _esc(s: str) -> str:
    return html.escape(s or "")


_HEAD = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>承認待ち board — HARAPPA Garden</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
         margin: 0; padding: 14px; background:#f6f6f4; color:#222; line-height:1.7;
         max-width: 760px; margin-inline:auto; }}
  header {{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:6px; }}
  h1 {{ font-size:18px; margin:0 0 2px; }}
  .sub {{ color:#888; font-size:12px; }}
  .empty {{ padding:40px 8px; color:#3a7; font-size:16px; text-align:center; }}
  details.card {{ background:#fff; border:1px solid #e3e3df; border-radius:12px; padding:4px 16px;
          margin:14px 0; box-shadow:0 1px 3px rgba(0,0,0,.05); }}
  details.card[open] {{ padding-bottom:14px; }}
  summary {{ cursor:pointer; list-style:none; padding:12px 0; }}
  summary::-webkit-details-marker {{ display:none; }}
  .kind {{ display:inline-block; font-size:12px; background:#eef3ff; color:#3457a6;
          border-radius:999px; padding:2px 10px; }}
  summary h2 {{ font-size:16px; margin:6px 0 4px; display:inline-block; }}
  .meta {{ color:#999; font-size:11.5px; }}
  /* レンダリング後の markdown */
  .md {{ font-size:15px; border-top:1px solid #eee; padding-top:10px; margin-top:4px;
        word-break:break-word; overflow-wrap:anywhere; }}
  .md h1 {{ font-size:18px; margin:14px 0 8px; }}
  .md h2 {{ font-size:16px; margin:16px 0 6px; padding-top:6px; border-top:1px dashed #e3e3df; }}
  .md h3 {{ font-size:14.5px; margin:12px 0 4px; color:#555; }}
  .md p {{ margin:8px 0; }}
  .md ul, .md ol {{ padding-inline-start:1.3em; margin:8px 0; }}
  .md li {{ margin:3px 0; }}
  .md code {{ background:#f0f0ec; padding:1px 5px; border-radius:4px; font-size:13px; }}
  .md pre {{ background:#fafaf8; border:1px solid #eee; border-radius:8px; padding:10px;
            overflow:auto; }}
  .md pre code {{ background:none; padding:0; }}
  .md blockquote {{ margin:8px 0; padding:6px 12px; border-left:3px solid #cdd6ea;
            background:#f7f9ff; color:#555; border-radius:0 6px 6px 0; }}
  .md hr {{ border:none; border-top:1px solid #eee; margin:14px 0; }}
  .md table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  .md th, .md td {{ border:1px solid #e3e3df; padding:4px 8px; text-align:left; }}
  @media (prefers-color-scheme: dark) {{
    body{{background:#1a1a1a;color:#ddd}} details.card{{background:#242424;border-color:#333}}
    .md{{border-color:#333}} .md code,.md pre{{background:#1e1e1e;border-color:#333}}
    .md blockquote{{background:#1f2533;border-color:#3a4a6a;color:#bbb}} .md code,.md pre code{{background:#333}}
    .kind{{background:#26344f;color:#9db8ef}} .sub,.meta{{color:#999}}
    .md h2{{border-color:#333}} .md th,.md td{{border-color:#333}}
  }}
</style></head><body>
<header><div><h1>📋 承認待ち board</h1><div class="sub">承認は Discord でガクコに。この画面は閲覧専用です。</div></div>
<div class="sub">{now} 時点 / {n} 件</div></header>
"""

_TAIL = """
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
  (function () {
    function render() {
      document.querySelectorAll('.md').forEach(function (el) {
        if (el.dataset.done) return;
        el.innerHTML = marked.parse(el.textContent.trim(), { breaks: true });
        el.dataset.done = '1';
      });
    }
    if (window.marked) { render(); }
    else { document.addEventListener('DOMContentLoaded', render); window.addEventListener('load', render); }
  })();
</script>
</body></html>"""


def _lint_banner() -> str:
    """board 規約違反(ERROR)があれば警告バナーを返す(無ければ空)。"""
    try:
        import board_lint
        errors = [m for sev, m in board_lint.collect_violations() if sev == "ERROR"]
    except Exception:
        return ""
    if not errors:
        return ""
    items = "".join(f"<li>{_esc(m)}</li>" for m in errors)
    return (
        '<div style="background:#fff3f0;border:1px solid #f0b8aa;border-radius:10px;'
        'padding:10px 14px;margin:10px 0;color:#a33;">'
        f"⚠️ <b>board 規約違反 {len(errors)} 件</b>(board_registry 未登録など)"
        f'<ul style="margin:6px 0 0;padding-inline-start:1.2em;">{items}</ul></div>'
    )


def render_dashboard_html() -> str:
    rows = list(sp.iter_pending_boards())
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    parts = [_HEAD.format(now=_esc(now), n=len(rows))]
    parts.append(_lint_banner())
    if not rows:
        parts.append('<p class="empty">✅ いま承認待ちの board はありません。</p>')
    else:
        for path, fm, body in rows:
            seed = (fm.get("from_seed") or "?").strip()
            kind, title = sp.classify_board(seed, fm, body)
            created = (fm.get("created") or "").strip()[:16]
            sched = (fm.get("scheduled_send") or "").strip()
            blocked = (fm.get("blocked") or "").strip().lower() == "true"
            meta = []
            if created:
                meta.append(f"作成 {created}")
            if sched:
                meta.append(f"⏰ {sched}")
            if blocked:
                meta.append("⛔ 前段待ち")
            meta.append(f"種 {seed} / {path.name}")
            parts.append(
                '<details class="card" open>'
                "<summary>"
                f'<span class="kind">{_esc(kind)}</span>'
                f"<h2>{_esc(title)}</h2>"
                f'<div class="meta">{_esc(" / ".join(meta))}</div>'
                "</summary>"
                # 本文は html-escape して入れる → JS が textContent を marked で描画(安全)
                f'<div class="md">{_esc(body.strip())}</div>'
                "</details>"
            )
    parts.append(_TAIL)
    return "\n".join(parts)
