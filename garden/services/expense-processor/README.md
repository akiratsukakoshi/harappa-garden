# expense-processor service

個人経費(クレカ明細 CSV + レシート画像)を抽出 → Freee 登録候補にする Python サービス。
HMC `apps/expense_processor/processor.py` を **移植型(transplant)** で Garden 化したもの。
業務知識(パーサ・Gemini 分類・Freee 登録)は全部継承し、変えたのは「起動」と「承認」だけ。

- 区画(plot): [garden/plots/expense_processor/SKILL.md](../../plots/expense_processor/SKILL.md)
- 種(seeds): [garden/seeds/expense_processor/](../../seeds/expense_processor/)(month-end-reminder / monthly-expense-draft)
- 起源: HMC `apps/expense_processor/processor.py` + `modules/freee_client/client.py` + `apps/invoice_processor/drive_client.py`

## 構成

```
expense-processor/
├── processor.py          extract / upload / taxes 本体
├── lib/
│   ├── freee_client.py   Freee API(HMC フル版移植: post_deal / get_account_items / get_sections / get_taxes)
│   ├── drive_client.py   Google Drive 同期・アーカイブ(HMC invoice_processor 移植)
│   └── utils.py          logger / ensure_directory
├── requirements.txt
├── .env.example          → .env として VPS に配置(600)
├── secrets/              ← VPS のみ(git 除外)。credentials.json(Drive SA)。Freee token は shift-manager と共有(FREEE_TOKEN_FILE)
├── input/                ← VPS のみ(git 除外)。未処理の明細・レシート
├── working/              ← VPS のみ(git 除外)。抽出した中間 CSV
└── proceeded/            ← VPS のみ(git 除外)。登録済みのアーカイブ(YYYYMMDD/)
```

## コマンド

```bash
cd /home/vps-harappa/garden/services/expense-processor
.venv/bin/python processor.py taxes                 # Freee の tax_code 一覧(EXPENSE_TAX_CODE 確定用)
.venv/bin/python processor.py extract               # Drive input → 中間 CSV(working/）
.venv/bin/python processor.py upload <csv> --dry-run # 登録内容を確認(必ず先に)
.venv/bin/python processor.py upload <csv>           # Freee 本登録 + input/CSV をアーカイブ
```

## Phase 2 デプロイ手順(S37 で 1〜7 完了。⭐ = ガクチョのコンソール操作)

1. ✅ **VPS に配置**: repo → VPS rsync(本 service に `.sh` は無い)。
2. ✅ **venv 構築**: VPS に `python3-venv` パッケージが無いため `python3 -m venv` は ensurepip で失敗する。
   `--without-pip` + get-pip でブートストラップする:
   ```bash
   cd /home/vps-harappa/garden/services/expense-processor
   python3 -m venv .venv --without-pip
   curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && .venv/bin/python /tmp/get-pip.py
   .venv/bin/pip install -r requirements.txt
   ```
3. ✅ ⭐ **secret 配置**(すべて 600 perm、`secrets/` と `.env` は git 除外):
   - `.env` … `.env.example` をコピーして Freee/Gemini/Drive の値を記入
   - **Freee token は shift-manager と共有**: `.env` の `FREEE_TOKEN_FILE` を
     `/home/vps-harappa/garden/services/shift-manager/secrets/freee_tokens.json` に向ける。
     (同一 Freee OAuth client を別ファイルで持つと refresh token ローテで互いを無効化するため、物理ファイルを1本に)
   - `secrets/credentials.json` … Drive は **service account**(`harappa-drive-bot@...`)。
     SA は対話認証不要・`token.json` 不要。HMC root の `credentials.json` を流用。
   ```bash
   chmod 700 secrets && chmod 600 secrets/* .env
   ```
4. ✅ ⭐ **tax_code 確定(会計の正しさに直結)**: `processor.py taxes` →
   **`136` = 課対仕入10%** を `.env` の `EXPENSE_TAX_CODE` に設定済。
5. ✅ **dry-run 検証**: 合成 PayPay CSV で extract → 分類(JR→旅費交通費 / スタバ→会議費)→
   `upload --dry-run` で `Tax=136`・全件勘定科目マッチ・skip 0 を確認(Freee 非書込み)。テストデータ掃除済。
   - この過程で **HMC 由来のバグを発見・修正**: `gemini-2.0-flash` 提供終了(404)で全件 `消耗品費` に
     黙ってフォールバックしていた → `gemini-2.5-flash`(env `GEMINI_MODEL` で可変)に更新。
6. ✅ **cron 登録**: 種 2 本(月末リマインド 28-31日19:00 / 抽出 2日08:00)を VPS crontab に。
7. **初回本登録(残)**: ガクチョが実明細を Drive `input/` に置く →(手動「経費まわして」or 2日 cron)→
   board → Discord 承認 → `upload`(dry-run なし)で初回登録 → **Freee 画面で税区分が「課税仕入」か目視**。
8. **昇格(残)**: 初回実走が通ったら plot を draft → active。

## 注意

- **input/working/proceededと secret は VPS のみ**。機微情報(明細・レシート・トークン)を含むため git に載せない。
- **費目 5 分類は Freee 側に同名の勘定科目がある前提**(完全一致しないと upload 時スキップ)。
- **必ず dry-run を先に**。本登録は取り消しが面倒なので、件数・合計・税区分を確認してから。
