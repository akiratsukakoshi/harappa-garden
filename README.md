# HARAPPA Management Garden (HMG)

HARAPPA Management Garden (HMG) は、小規模な事業運営を **AI エージェント中心** で進めるための実験的な経営運用プラットフォームです。

前身の HARAPPA Management Cockpit (HMC) は「人間が操縦席に座り、AI や業務ツールを呼び出す」モデルでした。HMG はそこから一段進めて、**エージェントが時間・イベント・状態変化を起点に動き、人間は判断・承認・方向修正に集中する** 構造を目指しています。

このリポジトリは公開されているため、この README では個別のクライアント、個人、取引先、会議名、実 URL、secret の値には触れず、プロジェクトの構造と設計思想を説明します。

## コンセプト

HMG の中心にある比喩は「庭」です。

- **人間の役割**: すべてを手で動かす操縦者ではなく、全体を見て剪定する庭師
- **AI エージェントの役割**: 区画ごとの業務を継続的に育て、必要なときに収穫や相談を出す存在
- **システムの役割**: 業務知識、実行トリガー、承認境界、通知、ログを一つの庭として結び直すこと

設計上の大きな方針は以下です。

- **Markdown first**: 業務知識、種、判断記録、ログをできるだけ読みやすいテキストとして持つ
- **Agent first**: 人間が都度起動するのではなく、cron・イベント・状態変化からエージェントが起動する
- **Human in the loop**: 外部送信、会計登録、重要な確定操作などは承認境界を明示する
- **Vendor neutral**: 特定 LLM だけに固定せず、runner / engine / capability を分けて差し替え可能にする
- **Operational memory**: 業務の判断材料を soil / memory / session / ADR に蓄積し、次の実行に引き継ぐ

詳しい思想は [docs/concept.md](docs/concept.md)、語彙は [docs/garden-vocabulary.md](docs/garden-vocabulary.md) を参照してください。

## Garden 語彙

HMG では設計議論のために Garden 語彙を使います。これは装飾ではなく、「何をどこに置くか」を揃えるための設計言語です。

| 語彙 | 意味 |
|---|---|
| 庭 / Field | HMG 全体 |
| 庭師 / Gardener | 最終判断・承認・方向修正を行う人間 |
| 区画 / Plot | 業務ドメイン。財務、SNS、会議調整、日次運用など |
| 種 / Seed | cron、イベント、状態変化などの起動条件 |
| 土壌 / Soil | スタッフ、案件、イベント、業務フローなどのコンテキスト基盤 |
| 番人 / Watcher | 異常や未処理を監視して知らせるエージェント |
| 菌糸 / Mycelium | 情報を分解・整理・索引化する裏方エージェント |
| 剪定 / Pruning | 人間による承認、却下、修正、方向づけ |
| 収穫 / Harvest | レポート、投稿案、会計登録、会議設定などの業務成果 |
| 通行手形 / Capability | scope ごとの権限境界。誰がどの操作を実行できるか |
| 測量士 / Land Surveyor | 実装から離れて全体を俯瞰する外部視点 |

コード上の `tool` / `service` / `provider` は実装層の用語です。庭師が設計するのは主に **区画・種・通行手形** で、具体的なサービス実装は水面下の実装層に置きます。

## 現在実装されている主な機能

HMG はすでに複数の区画が実運用またはテスト運用されています。以下は公開 README 向けに抽象化した一覧です。

| 区画 | 状態 | 役割 |
|---|---|---|
| `daily-pilot` | active | 日次タスクの生成、朝のブリーフィング、夜のレビュー、承認待ちの再提示 |
| `shift_manager` | active | 月次のシフト募集、稼働集計、確認依頼の起草と承認フロー |
| `expense_processor` | active | 経費候補の抽出、レビューシート化、承認後の会計登録 |
| `invoice_processor` | test | 請求書候補の抽出、レビュー、承認後の会計登録 |
| `finance` | test | 月次レビュー、見積・請求書生成、財務分析の補助 |
| `sns_manager` | active / test | 投稿候補の生成、画像取得、予約投稿、失敗検知 |
| `client_steward` | active | メールや履歴から案件フォロー候補を抽出し、soil へつなぐ |
| `scribe` | test | 会議録を取り込み、関係する soil へ要約・索引を接続する |
| `field_assistant` | test | 現場準備やイベント前後の確認を扱う |
| `meeting_coordinator` | test | 会議候補抽出、参加可否記録、確定後のカレンダー・オンライン会議設定 |
| `plot_gardener` | active | 新しい業務を Garden 化するためのメタ区画 |

横断機能として、以下も動いています。

- **launcher**: seed を読み、runner / engine を解決してエージェントを起動する実行基盤
- **garden-gaku-co**: Discord / LINE などの会話面から Garden の tool を呼び出す対話レイヤー
- **board**: 人間の承認が必要なものを集める剪定キュー
- **watcher**: cron、ログ、投稿失敗、沈黙などを監視する番人
- **mycelium**: soil / memory の索引更新、取り込み、整理を行う裏方
- **soil-sync / memory-sync**: repo と VPS の正本関係を保つ同期スクリプト
- **runtime Vendor Switch Kit**: LLM runner の差し替えを進めるための監査、設定、smoke test

## ローカルと VPS の関係

HMG はローカル環境と VPS を分担して使います。

| 場所 | 主な役割 |
|---|---|
| ローカル | 実装、設計、レビュー、テスト、repo 上の構造ファイル編集 |
| VPS | 24 時間稼働の cron、bot、通知、board、log、実運用データとの接続 |
| Obsidian / vault | 人間が読むためのビュー。すべての実行正本ではない |
| GitHub | コード、設計文書、構造化された知識の共有・履歴管理 |

重要な正本関係は次の通りです。

- **repo**: plot、seed、service、workflow、ADR などの構造ファイルの正本
- **VPS**: cron 実行、board、log、bot、実運用 state の正本
- **soil**: repo と VPS の間で同期するコンテキスト基盤。編集内容に応じて pull / push する
- **memory**: wiki 的な運用記憶。raw は VPS 側、整理済み wiki は同期対象

VPS には secret や本番 token が配置されますが、値は repo に置きません。secret を扱う作業では [docs/security/README.md](docs/security/README.md) のルールに従います。

## コミュニケーションチャンネル

HMG では、人間との接点を用途ごとに分けています。

| チャンネル | 役割 |
|---|---|
| Discord | 個人運用面。朝夕のブリーフィング、承認依頼、失敗通知、開発・運用対話 |
| LINE | チームや関係者との通知・返信面。必要な tool だけを capability で開く |
| board | 承認・却下・修正が必要なものの実体。通知ではなく判断単位の置き場 |
| Obsidian / Markdown | タスク、知識、運用ログを人間が読むビュー |
| Google Workspace | カレンダー、Drive、Sheets などの業務データ接続 |
| 会計サービス | 経費、請求、売上、部門などの会計処理接続 |
| オンライン会議サービス | 会議確定時の URL 発行と招待 |

基本原則は、**通知チャンネルと判断の正本を分ける** ことです。Discord や LINE は知らせる場所、board は承認単位、session / ADR は履歴と決定の置き場です。

## Soil の役割

`garden/soil/` は HMG のコンテキスト基盤です。エージェントが自律的に判断するには、業務の前提が散らばらず、参照可能な形になっている必要があります。

soil には次のような情報を置きます。

- 人、役割、チーム、関係性
- 事業やサービスの構造
- イベントや会議の履歴
- 案件やプロジェクトの状態
- 財務処理の前提
- 業務フローの正本
- soil 自体の編集ログ

特に `garden/soil/workflows/` は、業務プロセスの **single source of truth** です。各 workflow では、目的と現状の方法を分けます。

- **Purpose**: 変えない目的
- **Current Method**: 現時点のやり方。改善対象
- **Improvement Hints**: すぐ実装しない改善案の置き場

これにより、エージェントは「今の手順を守る」だけでなく、「目的を満たすよりよい方法」を提案できます。

## ディレクトリ構造

主要なディレクトリは以下です。

```text
.
├── AGENTS.md                  # Codex / Codex CLI 向け入口
├── CLAUDE.md                  # 実装エージェント向け入口
├── README.md                  # 公開向けの全体説明
├── docs/
│   ├── concept.md             # HMG の設計思想
│   ├── garden-vocabulary.md   # Garden 語彙の正本
│   ├── decisions/             # ADR 的な設計判断ログ
│   ├── sessions/              # セッションごとの作業記録
│   ├── security/              # secret / security 運用
│   └── surveyor/              # 測量士の手紙と応答
├── garden/
│   ├── MAP.md                 # 現在地、区画ステータス、ロードマップ
│   ├── OPERATIONS.md          # 日々の運用盤
│   ├── CHARTER.md             # 全 plot 共通の振る舞い規範
│   ├── plots/                 # 業務区画ごとの SKILL
│   ├── seeds/                 # cron / event / state 起動の定義
│   ├── services/              # 実装スクリプト、bot、同期、watcher
│   ├── soil/                  # コンテキスト基盤
│   ├── memory/                # 運用記憶
│   ├── mycelium/              # soil / memory 維持エージェント
│   ├── runtime/               # runner、engine、権限、smoke test
│   ├── board/                 # ローカル側の構造。実運用 board は VPS 側
│   └── inbox/                 # CSV などの受け皿
├── deploy/                    # デプロイ元として使う補助ファイル
└── vps/                       # VPS 側サービスの管理・デプロイ補助
```

## 実行基盤

HMG の seed は `garden/services/launcher/` から起動されます。seed は frontmatter と本文で、いつ・何を・どの engine で・どの権限で動かすかを定義します。

現在の runtime は以下を分離する方向で整備されています。

- **seed**: 起動条件と業務目的
- **runner**: LLM CLI や実行方式の差し替え層
- **engine**: Claude / Codex などの具体的なエンジン指定
- **capability**: scope ごとの実行権限
- **service**: API 連携や決定的処理を担う Python / Node 実装
- **board**: 人間承認が必要な操作の待機場所

この分離により、LLM ベンダーの差し替え、権限の監査、低リスク seed での smoke test ができるようになっています。

## ドキュメントの読み方

目的別には次を見るのが近道です。

| 知りたいこと | 読む場所 |
|---|---|
| 全体思想 | [docs/concept.md](docs/concept.md) |
| Garden 語彙 | [docs/garden-vocabulary.md](docs/garden-vocabulary.md) |
| 現在地 | [garden/MAP.md](garden/MAP.md) |
| 日々の運用 | [garden/OPERATIONS.md](garden/OPERATIONS.md) |
| 業務区画の手順 | `garden/plots/{plot}/SKILL.md` |
| 起動トリガー | `garden/seeds/` |
| 実装 | `garden/services/` |
| 設計判断 | [docs/decisions/](docs/decisions/) |
| 作業履歴 | [docs/sessions/](docs/sessions/) |
| 外部視点レビュー | [docs/surveyor/](docs/surveyor/) |
| secret / security | [docs/security/README.md](docs/security/README.md) |

## 開発時の注意

- この repo は実運用に近い構造を含みます。公開 README や issue では個別のクライアント、個人、組織、URL、token、内部 ID を出さないでください。
- secret は repo に置きません。値の確認も `set/unset` や length 比較に留めます。
- soil や memory に関係する作業では、必要に応じて VPS から pull してから編集し、終了時に push します。
- 新しい業務を追加する場合は `plot_gardener` を通し、区画・種・通行手形を先に設計します。
- 重要な正本関係、命名、権限、運用境界を変える場合は ADR を残します。

## ステータス

開発開始は 2026-05-22。現在は、日次運用、シフト、経費、SNS、会議調整、会議録、案件フォロー、財務補助などの区画を段階的に Garden 化しています。

HMG は完成品ではなく、実運用しながら育てるシステムです。`garden/MAP.md` が現在地、`docs/sessions/` が時系列の作業履歴、`docs/decisions/` が判断の根拠です。
