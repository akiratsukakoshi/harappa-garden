# HMG の由来

## HMC からの派生

HMG (HARAPPA Management Garden) は **HMC (HARAPPA Management Cockpit)** をフォーク元として 2026-05-22 に開発開始した。

- フォーク元: [`/home/tukapontas/harappa-cockpit/`](file:///home/tukapontas/harappa-cockpit/) (`akiratsukakoshi/harappa-cockpit`)
- フォーク方針: **履歴を切る** (HMCの`git log`は継承しない)。コンセプトに断絶があるため、HMGは新規履歴で出発。

## なぜフォークしたか

HMCは「人間(塚越さん)が中央の操縦席に座り、ツール/Copilotと協働する」モデルで設計されていた。これを「**エージェントが起点となり、塚越さんが判断・監督する**」モデルに進化させるには、設計思想そのものを書き直す必要があると判断したため。

- HMCを直接書き換えると、実業務(現在進行中)を止めるリスクがある
- 新旧の設計が混在すると、意思決定の参照点が曖昧になる
- 名前・語彙・構造を一新することで「HMG時代」の出発点を明確にする

## HMCから持ち込んだもの

- `.agent/` — SKILL定義・workflow定義(段階的にGarden化予定)
- `apps/` — 各SKILL実装コード
- `modules/` — Freee/utils等の共通モジュール
- `scripts/` — 補助スクリプト
- `deploy/`, `development/` — 運用ツール
- `rules.md` — ディレクトリ構成等のルール
- `requirements.txt` — Pythonパッケージ依存
- `main_menu.py`, `clean.py` — 補助ツール
- `docs_legacy/` — HMC時代のドキュメント(参考用に残置)

## HMCから持ち込まなかったもの

- **`.git/`** — 新規履歴で出発
- **`data/`** — 実業務データ。HMC側で稼働継続のため移さない
- **`tasks/`** — hmc_pilot のタスクデータ。Garden版のタスク管理は別途設計
- **`.env`, `credentials.json`, `token.json`, `oauth_credentials.json`, `modules/freee_tokens.json`** — 秘匿情報。塚越さんが必要時に個別設定
- **`.venv/`** — ローカル環境ごとに再構築
- **`gogcli_analysis/`** — 研究分析資料(HMG設計と独立)
- **`debug_*.py`, `test_drive_*.py`, `patch.py`, `list_models.py`** — 一過性スクリプト
- **`calendar_output.txt`, `run_log.txt`** — 実行ログ
- **`.claude/`** — HMCローカル設定(HMG側で新規生成)
- **`README.md`, `project_harappa-cockpit.md`** — HMC固有。HMG用に書き直し

## 並行運用の方針

当面は HMC が実業務(請求書処理・経費・SNS等)を稼働させ続け、HMGは **設計・開発のサンドボックス** として動く。

- HMCで継続: 既に動いている SKILL の日々の実行
- HMGで開発: Garden化設計、新SKILL、自律トリガー化、コンテキスト統合(土壌)
- 移行: ある区画(SKILL)が HMG で十分育ったら、HMCから実業務をHMGに移植する

## メタデータ

- ネーミング決定: 2026-05-22 (詳細: [docs/decisions/2026-05-22-naming.md](decisions/2026-05-22-naming.md))
- 最初の壁打ち議論: [docs/discussions/2026-05-22-concept.md](discussions/2026-05-22-concept.md)
- GitHub: `akiratsukakoshi/harappa-garden` (private)
