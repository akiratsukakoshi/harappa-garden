# finance service — 財務区画の実装(売上記帳 / 財務分析 / データ整合性)

HMC 3スキル(finance_importer / finance_analyzer / freee_auditor)を 1 区画 `finance` に
束ねた transplant 移植(S47)。区画 SKILL = [garden/plots/finance/SKILL.md](../../plots/finance/SKILL.md)。

## 3 つの実行体(HMC の 3 app に対応)

| script | モード | 役割 | Freee |
|---|---|---|---|
| `importer.py` | I 記帳 | 売上CSV(STORES/Square)→ 振替伝票 | **書込**(manual_journal) |
| `auditor.py`  | D 監査 | 部門漏れ + 未登録明細の検出 → 部門を修正 | **書込**(PUT deals) |
| `analyzer.py` | A 分析 | PL/CF/着地予測(read-only) | 読取のみ |

月次サイクル: **5日** ガクチョが Drive に売上CSVアップ → **6日** importer → **9日** auditor(地ならし)→ **10日** analyzer が Discord に対話の投げかけ。

## コマンド

```bash
PY=.venv/bin/python
# 記帳(I)
$PY importer.py fetch                      # Drive 売上CSV → input/
$PY importer.py generate                   # input/ → 振替伝票候補 review CSV(部門ルール推定)
$PY importer.py to-sheet <csv> --tab YYYYMM
$PY importer.py from-sheet <tab>
$PY importer.py register <csv> --dry-run   # 内容確認
$PY importer.py register <csv>             # manual_journal 本登録 + Drive 原本を processed へ
# 監査(D)
$PY auditor.py scan --month YYYY-MM        # 部門漏れ + 未登録明細(PL未反映)を検出
$PY auditor.py to-sheet <csv> --tab YYYYMM
$PY auditor.py from-sheet <tab>
$PY auditor.py apply <csv> --dry-run       # PUT 内容を確認(破壊的なので必須)
$PY auditor.py apply <csv>                 # 部門を Freee に反映
# 分析(A, read-only)
$PY analyzer.py check                      # データ品質(部門未設定・未決済の月別件数)
$PY analyzer.py pl / cf / summary
$PY analyzer.py targets --set-revenue 30000000 --set-operating-profit 5000000
```

## secret(VPS のみ、600)

すべて既存資産の流用。**新しい Freee 連携・新トークンは作らない**(重複回避):

| secret | 中身 | 流用元 |
|---|---|---|
| `.env` `FREEE_CLIENT_ID/SECRET/TARGET_COMPANY_ID` | Freee OAuth | 他 finance 系区画と同一(company 723485) |
| `.env` `FREEE_TOKEN_FILE` | Freee トークン共有ファイル | expense/shift/invoice と物理共有(429 ローテ対策) |
| `secrets/credentials.json` | service account(Drive read + Sheets) | expense の `harappa-drive-bot@…` 流用 |
| `.env` `FINANCE_SALES_DRIVE_FOLDER_ID` | 売上CSVアップ用 Drive フォルダ | ⭐ガクチョが作成 → SA に共有 |
| `.env` `FINANCE_REVIEW_SHEET_ID` | レビュー用ワークブック | ⭐ガクチョが作成 → SA に Editor 共有 |

`config/targets.json` は repo に雛形(目標0)。VPS は実数値で diverge するので、
**デプロイ rsync は `--exclude config/targets.json`**(実数値を repo に戻さない)。

## freee_client(正本 + コピー同期)

`lib/freee_client.py` は `garden/lib/freee_client.py`(正本)の機械コピー。S47 で
読み取りメソッド(`get_trial_pl` / `get_all_deals` / `get_walletables` / `get_deal` /
`update_deal_section` / `get_wallet_txns`)を正本に追記済み。編集は正本で行い
`garden/lib/sync-freee-client.sh` で配布。

## ⚠️ 初回実データで確定する TODO

`auditor.py scan` の **未登録明細**(`get_wallet_txns`)は、freee の明細 `status` の
どの値が「未登録(取引化されていない)」かを初回実データで確定する。

**S47 実データ(2026-05)**: status 内訳 `{1: 16, 2: 23}`。サンプルの status=1 は
「かながわ信金の振込入金(Square/STORES 売上)・手数料・コドモン等」= **取引化されていない
口座のお金の動き**そのもの。→ **status=1 が「未登録」の候補**。ガクチョ確認のうえ
`_scan_unregistered` に `status == 1` の filter を入れて headline 件数を絞る(現状は全件報告)。
詳細は SKILL Mode D。
