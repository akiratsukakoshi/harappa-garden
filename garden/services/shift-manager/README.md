# garden/services/shift-manager — シフトと稼働の Python サービス

shift_manager 区画([garden/plots/shift_manager/SKILL.md](../../plots/shift_manager/SKILL.md))から呼ばれる Python スクリプトの本体。HMC `apps/shift_manager/logic/` の必要部分(6/1 ミニマムスコープ)を Garden 化したもの。

## 配置(VPS)

```
/home/vps-harappa/garden/services/shift-manager/
├── generate_shift_form.py
├── generate_working_hours.py
├── lib/
│   ├── utils.py
│   └── freee_client.py
├── config/
│   ├── config_ids.json
│   └── section_mapping.json
├── secrets/            ← 600 perm, git 除外
│   ├── credentials.json    (Google OAuth client)
│   ├── token.json          (Google OAuth user token)
│   └── freee_tokens.json   (Freee OAuth tokens)
├── .env                ← 600 perm, git 除外
│   FREEE_CLIENT_ID=...
│   FREEE_CLIENT_SECRET=...
│   FREEE_TARGET_COMPANY_ID=...
├── .venv/              (Python 3.12)
├── requirements.txt
└── README.md
```

## セットアップ(VPS 初回)

```bash
cd /home/vps-harappa/garden/services/shift-manager
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# secrets/ と .env は手動配置(scp で HMC から持ち込む)
mkdir -p secrets && chmod 700 secrets
# 配置後:
chmod 600 secrets/* .env
```

## 実行(月次)

### シフト募集フォーム生成(翌々月)
```bash
.venv/bin/python generate_shift_form.py --month 2026-07
```

### 稼働時間集計シート生成(対象月)
```bash
.venv/bin/python generate_working_hours.py --month 2026-05
```

## 起動経路

- 月初1日 08:00 cron → `garden/seeds/shift_manager/monthly-shift-survey.md` → `generate_shift_form.py --month {翌々月}`
- 月末最終日 22:00 cron → `garden/seeds/shift_manager/month-end-working-hours-prep.md` → 庭師承認後に `generate_working_hours.py --month {当月}`

## HMC との関係

- HMC `apps/shift_manager/logic/` の **2 本** を Garden 化(generate_shift_form / generate_working_hours)
- 他の 12 本(monthly_to_db / aggregate_responses / register_payroll / 等) は **HMC 残置**(必要になったら段階的に Garden 化判断)
- HMC との同時稼働は **避ける**(Google Sheets の同一タブを両方が触るため)。Garden 化後は Garden 側のみを使う

## ロジックの変更点(HMC → Garden)

| 変更 | HMC | Garden |
|---|---|---|
| パス | cwd 相対 (`credentials.json` 等) | `__file__` ベース絶対 |
| credentials 配置 | プロジェクトルート | `secrets/` 配下 |
| config 配置 | `apps/shift_manager/` | `config/` 配下 |
| logger import | `from modules.utils` | `from lib.utils` |
| freee_client import | `from modules.freee_client` | `from lib.freee_client` |
| freee_client | 393行(post_deal / get_account_items / get_trial_pl 等含む) | 160行(`get_partners` のみ、generate_working_hours が使う最小スコープ) |
| 「ガクチョー」 | そのまま | 「ガクチョ」(memory rule) |

ロジック本体(集計式・シート書式・OAuth フロー)は HMC と完全同一。

## 関連

- 区画 SKILL: [garden/plots/shift_manager/SKILL.md](../../plots/shift_manager/SKILL.md)
- 業務 workflow: [garden/soil/workflows/monthly-cycle.md](../../soil/workflows/monthly-cycle.md)
- 種: [garden/seeds/shift_manager/](../../seeds/shift_manager/)
- HMC 起源: `/home/tukapontas/harappa-cockpit/apps/shift_manager/logic/`
