# 土壌の編集ログ

> 追記専用。フォーマットは [README.md](README.md#ログのルール) 参照。

## [2026-05-22] init | 土壌の初期化
- by: claude
- type: edit
- pages: README.md, index.md, log.md
- summary: garden/soil/ の骨格(README, index, log)とディレクトリ構造を作成。Karpathy LLM Wiki 方式で運用開始。

## [2026-05-22] ingest | 既知4名のスタッフページを初期生成
- by: claude
- type: ingest
- pages: [[akira-tsukakoshi]], [[yuji-wada]], [[shotaro-shimura]], [[kei-suzuki]]
- summary: HMC の invoice_processor master_data.csv から Freee ID を取得し、CLAUDE.md と塚越さんの口頭情報をもとに 4 名の初期ページを生成。Email・nicknames・linked_* は塚越さん埋め待ち。
- source: harappa-cockpit/data/invoice_processor/master_data.csv, CLAUDE.md

## [2026-05-22] ingest | Partner マスター候補リストを抽出
- by: claude
- type: ingest
- pages: _review-2026-05-22-master-data-candidates.md
- summary: HMC invoice_processor master_data.csv 160 件を抽出し、Claude が「個人110/法人23/判定不能27」に暫定分類。塚越さんレビュー待ち。確定後にスタッフページを順次生成。
- source: harappa-cockpit/data/invoice_processor/master_data.csv

## [2026-05-22] edit | CLAUDE.md 主要固有名詞を更新
- by: claude
- type: edit
- pages: CLAUDE.md
- summary: 和田・少佐の本名と慶ちゃんを追加。「パートナー」→「運営」に表記変更(塚越さん口頭情報に合わせる)。

## [2026-05-22] ingest | Drive スタッフ登録フォーム(回答)を読み込み
- by: claude
- type: ingest
- pages: [[akira-tsukakoshi]], [[yuji-wada]], [[shotaro-shimura]], [[kei-suzuki]], _alumni.md, _review-2026-05-22-master-data-candidates.md
- summary: Service Account (harappa-drive-bot@harappa-cockpit.iam.gserviceaccount.com) で Drive Sheet (id: 1oiCLf34zwhsDqLvGq5WrPCF5dNJi_7SyUS-gc6_VqBo) を読み込み、88名のスタッフ情報を抽出。既知4名のメアド・ふりがな確定、_alumni.md に退任7名(志村圭子含む)集約、_review ファイルを Sheet データで強化。
- source: Drive Sheet「スタッフ登録フォーム(回答)」

## [2026-05-22] edit | スキーマ確定(機微情報方針)
- by: claude
- type: edit
- pages: people/staff/README.md, _template.md
- summary: 塚越さん判定により最終スキーマ確定。Wiki に書くのは name, kana, email, role, freee_id, nicknames のみ。生年月日・住所・口座等の機微情報は Wiki に書かず Drive Sheet 参照のまま。role は「代表 | 運営 | 業務委託 | アルバイト」の1軸(雇用区分とは別軸)。

## [2026-05-22] edit | セッション運用の仕組み導入
- by: claude
- type: edit
- pages: garden/MAP.md, docs/sessions/2026-05-22-session1.md, CLAUDE.md
- summary: 塚越さん要望で「全体設計図 + 進捗管理 + セッション切れ目フロー」を導入。garden/MAP.md(常に最新の俯瞰)、docs/sessions/(時系列サマリ)を新設、CLAUDE.md にセッション運用ルールを追記。次回以降セッション開始時に MAP.md と最新 session を読む規律。

## [2026-05-22] edit | 4名スタッフの担当領域を双方向リンク
- by: gardener + claude
- type: edit
- pages: [[akira-tsukakoshi]], [[yuji-wada]], [[shotaro-shimura]], [[kei-suzuki]], [[parent-child]], [[kids]], [[saboru-zushi]], [[ore-no-yoga]], [[events]], [[training]]
- summary: 塚越さんレビュー(2026-05-22)で4名の担当領域・追加メアド・nicknames を直接編集。Claude が linked_services / linked_staff の双方向リンクを補完。塚越さん追記の主要事項: 塚越→tuka@harappa-daigaku.jpメアド追加・ガクチョ ニックネーム、和田→おやこ/運営全般/企業研修、少佐→おやこ/ナーフ学園(events)/サボール、慶ちゃん→俺のヨガ/こども、慶ちゃんは退社済みでいまは業務委託(role=運営は維持)。
- source: 塚越さんレビュー直接編集

## [2026-05-22] ingest | business/ 事業構造の骨格を作成
- by: claude
- type: edit
- pages: business/README.md, toC/*, toB/*, communication/*
- summary: 21ファイルの骨格生成。HARAPPA(株)単一法人配下に toC事業(原っぱ大学・大阪・放課後サボール・俺のヨガ・各種イベント・AI関連)、toB事業(研修・組織開発・コミュニティマネジメント・単発イベントプロデュース・みうらの森林共創・その他出演等)、横断コミュニケーション(週1メルマガ)を配置。各サービスページは中身空欄(塚越さん埋め待ち)。
- source: 塚越さん 2026-05-22 提供の事業領域サマリ
