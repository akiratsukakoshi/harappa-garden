---
type: service
status: draft(2026-06-10 S41 移植。VPS デプロイ + 初回実走待ち)
last_updated: 2026-06-10
purpose: Gmail の請求書を月次で取得・解析し、スタッフ照合・稼働突合つきの Freee 登録候補を作る
---

# invoice-processor — 請求書処理 service

HMC `apps/invoice_processor/` の hybrid 移植(S41)。区画は [garden/plots/invoice_processor/](../../plots/invoice_processor/SKILL.md)、種は [garden/seeds/invoice_processor/](../../seeds/invoice_processor/)。

## フロー

```
fetch    : Gmail(件名キーワード or Invoice_Pending ラベル)→ 添付を Drive Inbox へ
extract  : Drive Inbox → Gemini 解析 + ルール推論 + ★soil スタッフ照合 → review CSV
check    : ★稼働時間シート({前月}_稼働時間 の 区分=業務委託)と突合 → 請求漏れ検出
to-sheet : review CSV → レビュー用 Sheets タブ(ガクチョが直接編集)
from-sheet: 編集後タブ → CSV 書き戻し
register : CSV → Freee 支出取引登録 + Gmail 処理済ラベル + Drive Processed/Error 移動
```

★ = S41 の新機能(HMC に無い)。スタッフ照合は `garden/soil/people/staff/` の
frontmatter(contract / freee_id)が正本。リスト外(スタッフでない請求元)も
同じフローで Freee 登録まで進む(レビューで薄い青に色分けされるだけ)。

## 認証(3 系統)

| 系統 | 方式 | 備考 |
|---|---|---|
| Gmail / Drive / Sheets | **user OAuth token 1 本**(`secrets/user_token.json`) | SA だと Drive アップロードが quota で失敗するため(HMC も gog = user 認証)。発行は `issue_token.py`(ローカル 1 回)。scope: gmail.modify / drive / spreadsheets |
| Freee | 共有 token(`FREEE_TOKEN_FILE` = shift-manager と物理共有) | refresh ローテ対策。client は `garden/lib/freee_client.py` 正本のコピー |
| Gemini | `GEMINI_API_KEY` | モデルは env(既定 gemini-2.5-flash) |

## セットアップ(VPS)

1. rsync 一式 + `python3 -m venv .venv --without-pip` + get-pip + `pip install -r requirements.txt`
2. `.env`(`.env.example` 参照)+ `secrets/user_token.json`(ローカル発行 → scp)を配置、全部 chmod 600
3. dry-run: `processor.py check --month YYYY-MM` → `processor.py register --file <csv> --dry-run`

## 入出力

- working/: review CSV(`invoices_*.csv`、`*_reviewed_*.csv`)。git 除外
- temp/: 解析時の一時 DL。git 除外
- Drive: `DRIVE_INBOX_ID` → `DRIVE_PROCESSED_ID` / `DRIVE_ERROR_ID`(HMC のフォルダを継承)
- Sheets: `INVOICE_REVIEW_SHEET_ID` のタブ `{YYYYMM}`

## 関連

- 移植元: `harappa-cockpit/apps/invoice_processor/`(+ SKILL の月次支払フロー)
- 外部スタッフ(区分=追加)の稼働 CSV は HMC `export_external_staff.py` 相当が将来課題
  (現状の Garden 化スコープ外。必要なら HMC で生成した CSV を register に渡せる)
