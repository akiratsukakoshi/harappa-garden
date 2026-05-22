# CLAUDE.md — HARAPPA Management Garden (HMG)

## このプロジェクトについて

**HARAPPA Management Garden (HMG)** は、原っぱ大学(株式会社HARAPPA)の経営業務を **AIエージェント中心** で運用していく統合プラットフォーム。

前身の **HARAPPA Management Cockpit (HMC)** は「塚越さん(人間)が操縦席に座り、ツール/コパイロットと協働して事業を進める」モデル。HMGはここから一段進化させ、**「エージェントが起点となり、塚越さんが判断・監督する」** 構造を目指す。塚越さんは庭師(Gardener)、エージェント群は自律的に育つ生態系という比喩を、設計言語として採用する。

詳細は [docs/concept.md](docs/concept.md) を参照。

## 実行環境
- WSL (Ubuntu) 上で動作。Bashコマンドは直接実行可。
- ファイルパスは `/home/tukapontas/harappa-garden/` を基準としたLinuxパスを使用。
- Pythonは `.venv/bin/python3` を使用。

## 作業スタイル
- ファイルの読み込み・書き込み・コマンド実行は **逐一確認せず、自律的に進める**。
- 確認が必要なのは **破壊的操作(削除・force push等)** と **ユーザーの判断が必要な分岐点** のみ。
- `git push` はユーザーから指示があれば確認なしで実行してよい。
- 不明点・あいまいな点は判断せず、塚越さんとの議論で進める(原文「HMC→HMG移行は壁打ちしながら育てる」)。

## ベンダー中立の方針
- 当プロジェクトはClaudeを主に利用するが、Gemini/GPT等の他LLMからも参照可能な形で設計する。
- CLAUDE.md・memory・docsはすべてプロジェクト内に配置(プラットフォーム固有形式を避ける)。
- データストアはmarkdown + sqlite + MCP serverを基本とする。

## Garden語彙(設計言語)

HMG関連の設計議論ではこの語彙を共通言語として使う。詳細表は [docs/garden-vocabulary.md](docs/garden-vocabulary.md)。

| 語彙 | 対応 |
|---|---|
| 庭師 (Gardener) | 塚越さん — 戦略決定・最終承認・剪定 |
| 庭 / Field | HMG全体 |
| 区画 (Plot) | 業務ドメイン(財務区画・SNS区画など) |
| 種 (Seed) | トリガー(cron/event/状態変化) |
| 土壌 (Soil) | コンテキスト基盤(スタッフ・取引先・イベント等のマスター) |
| 番人 (Watcher) | 監視エージェント |
| 剪定 (Pruning) | 人間の介入(承認・却下・修正) |
| 収穫 (Harvest) | 業務成果物 |
| 寄合 (Yoriai) | エージェント間議論 |
| 天気 (Weather) | 外部状態(カレンダー・メール・市況・気象) |
| 季節 (Season) | 業務サイクル(日次・週次・月次・年次) |
| 苗床 (Nursery) | 試行中の業務・新SKILL |
| 蔵 (Kura) | 長期アーカイブ |

## 主要連携サービス (HMCから継承)
- **Freee** — 会計(売上記帳・経費・請求書)
- **Google Workspace** — Drive, Sheets, Calendar
- **Gemini AI** — PDF解析、経費分類

## SKILL一覧 (HMCから継承、段階的にGarden化予定)

各SKILLは `.agent/skills/{name}/SKILL.md` に定義。実行前に該当SKILLファイルを必ず読む。

| SKILL | 用途 |
|---|---|
| `hmc_pilot` | 朝ブリーフィング・タスク管理・週次レビュー |
| `finance_importer` | STORES/Square売上CSV → Freee振替伝票 |
| `expense_processor` | クレカ明細・レシート → Freee経費登録 |
| `invoice_processor` | Gmailの請求書PDF → Freee取引登録 |
| `freee_auditor` | 部門振り分け漏れの発見・一括修正 |
| `finance_analyzer` | PL/CF確認・財務予測・戦略議論 |
| `minute_maker` | 会議文字起こし → 議事録 |
| `sns_pilot` | Instagram/Facebook投稿の企画・下書き |
| `email_organizer` | メール整理 |
| `letter_opener` | 手紙仕分け |
| `shift_manager` | シフト管理 |

これらは現時点で「庭師(塚越さん)が起動する」構造。HMGでは段階的に「種(自律トリガー)から動く」構造に進化させる。

## 主要な固有名詞
- **原っぱ大学 / HARAPPA** — 運営する事業。自然体験×教育のフィールド事業
- **塚越(ガクチョー / 塚越暁)** — 代表・庭師
- **和田(ユージさん / 和田祐司)** — 運営
- **少佐(正太郎さん / 志村正太郎)** — 運営
- **慶ちゃん(鈴木慶)** — 運営
- **STORES / Square** — 決済サービス(売上CSVの入力元)
- **Freee** — クラウド会計ソフト(記帳先)

## 連携プロジェクト
- **HMC (harappa-cockpit)** — 前身。`/home/tukapontas/harappa-cockpit/`。当面実業務はHMC側で並行運用。
- **gaku-co5.0** — LINE Botフレームワーク(VPS側): `/home/tukapontas/gaku-co5.0/`
  - 連携API仕様: `/home/tukapontas/gaku-co5.0/INTERFACE.md`

## 設計議論の蓄積場所
- `garden/MAP.md` — **庭の見取り図(常に最新)**。現在地・区画ステータス・ロードマップ・宿題
- `docs/sessions/` — **セッションごとのサマリ**(時系列の記録)
- `docs/concept.md` — HMG全体のコンセプト(育てる文書)
- `docs/garden-vocabulary.md` — Garden語彙の定義表
- `docs/decisions/` — 設計判断の記録(ADR的)
- `docs/discussions/` — 議論ログ(壁打ち全文、任意)
- `docs/origin.md` — HMCからの派生経緯
- `garden/soil/log.md` — 土壌の編集ログ(細粒度)

設計議論の重要決定は必ず `docs/decisions/` に YYYY-MM-DD-題名.md で残す。

## セッション運用

**開始時**: `garden/MAP.md` と `docs/sessions/` の最新ファイルを読む。前回どこまで進んだか、宿題は何かを把握してから着手する。

**終了時**: 塚越さんから合図(「進捗書いて」「ここで止める」「セッション閉じる」「いったん区切る」等)があれば、Claude が以下を実行:

1. `garden/MAP.md` を最新化(現在地・区画ステータス・宿題・直近セッション欄)
2. `docs/sessions/YYYY-MM-DD-N.md` を作成(セッションサマリ、N は当日通し番号)
3. 内容を塚越さんに提示
4. 塚越さん OK で完了(git commit は別途指示)

進捗管理の粒度(粗→細):
- `garden/MAP.md` — 俯瞰(常に最新、1ページ)
- `docs/sessions/` — セッションサマリ(時系列)
- `docs/decisions/` — ADR(重要決定の理由つき)
- `docs/discussions/` — 壁打ち議論の全文(任意)
- `garden/soil/log.md` — 土壌の編集ログ(ingest/edit 都度)
