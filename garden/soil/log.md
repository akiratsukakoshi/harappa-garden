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

## [2026-05-22] edit | スタッフスキーマ contract / role 2軸に改訂
- by: gardener + claude
- type: edit
- pages: people/staff/README.md, _template.md, akira-tsukakoshi.md, yuji-wada.md, shotaro-shimura.md, kei-suzuki.md
- summary: 塚越さん判定により旧 `role: 代表|運営|業務委託|アルバイト` を 2軸に分離。**contract**(経営/業務委託/外部スタッフ/アルバイト、1軸排他) と **role**(運営/フィールドスタッフ/写真/調理、リスト複数可)。 area フィールドも追加。既存4名(塚越=経営/[運営]、ユージ・少佐・慶=業務委託/[運営])を移行。
- source: 塚越さん 2026-05-22 セッション2 判定

## [2026-05-22] ingest | _review 80名分の個別ページを一括生成(24名)
- by: claude
- type: ingest
- pages: shunsuke-akagi, tomoyo-kitao, etsuko-shimada, eriko-fujita (アルバイト 4), chihiro-irie, keisuke-ono, hiroki-ono, taro-koyama, nazuki-shindo, masaki-chonan, honoka-nagano, yuto-fukaya, shion-fujimoto, kota-yamada, kio-oyoshi (外部スタッフ 11), keiko-uchiyama, miho-oyoshi, naoko-shiroie, kasumi-tachibana, sakiko-nakatsuji, takayuki-maeda, misa-mine, mie-morite, kosaku-yoshida (業務委託 9)
- summary: _review-2026-05-22-master-data-candidates.md の塚越さんレビュー結果(☐ 26名のうち既存2名=塚越・少佐 を除く 24名)を個別ページ化。各ページは frontmatter のみ充実(contract/email/kana/freee_id/area)、本文は塚越さん埋め待ち。role は全員 `[]` (空リスト)で生成、塚越さんが運営/フィールドスタッフ/写真/調理 から選んで埋める。
- source: _review-2026-05-22-master-data-candidates.md, _data/sheet-extract-2026-05-22.json

## [2026-05-22] edit | 24名スタッフの role を確定
- by: gardener
- type: edit
- pages: 24 staff pages (shunsuke-akagi ... kosaku-yoshida)
- summary: 塚越さん指示で 24名分の role を一括設定。1-15(アルバイト4+外部スタッフ11)はフィールドスタッフのみ。業務委託9名は内山・立花・三根・吉田=写真のみ、大吉美穂=写真+フィールド、城家・中辻・前田・守田=フィールドのみ。役割「調理」は今回未割り当て。
- source: 塚越さん 2026-05-22 セッション2 指示

## [2026-05-22] edit | 三根美紗の Freee ID 同定(漢字違いの表記ゆれ)
- by: gardener + claude
- type: edit
- pages: [[misa-mine]]
- summary: Freee に「三根美沙」(沙)で登録あり、Freee ID 37003282。Sheet 表記「三根 美紗」(紗)と字違いだが、塚越さん判定で同一人物。`freee_name_variant: 三根美沙` フィールドを新設して両表記を記録。
- source: HMC master_data.csv, 塚越さん 2026-05-22 確認

## [2026-05-22] edit | _review ファイルの記号運用を訂正
- by: claude
- type: edit
- pages: _review-2026-05-22-master-data-candidates.md
- summary: 塚越さん運用と Claude の説明文に乖離があった(塚越方式: ☐=個別ページ作る / ■=alumni / ×=不要)。説明文を実態に合わせて修正。alumni 集約(■ 48名)は塚越さん「無視でOK」判定で本セッションでは保留。

## [2026-05-22] ingest | business/ 事業構造の骨格を作成
- by: claude
- type: edit
- pages: business/README.md, toC/*, toB/*, communication/*
- summary: 21ファイルの骨格生成。HARAPPA(株)単一法人配下に toC事業(原っぱ大学・大阪・放課後サボール・俺のヨガ・各種イベント・AI関連)、toB事業(研修・組織開発・コミュニティマネジメント・単発イベントプロデュース・みうらの森林共創・その他出演等)、横断コミュニケーション(週1メルマガ)を配置。各サービスページは中身空欄(塚越さん埋め待ち)。
- source: 塚越さん 2026-05-22 提供の事業領域サマリ

## [2026-05-23] ingest | workflows/ toC原っぱ大学 3階層の業務フロー初期化
- by: claude (gardener 投入)
- type: ingest
- pages: workflows/README.md, workflows/annual-quarterly-planning.md, workflows/monthly-cycle.md, workflows/program-execution.md
- summary: 塚越さん投入のテキストをもとに toC 1-a/b/c(おやこ/こども/おとな)の業務フローを 3 階層に分解して言語化。(A) 年間→3ヶ月→月次の企画反映、(B) 当月のシフト中心ルーチン、(C) プログラム実施フローの 3 本立て。登場人物(企画担当者=運営4+飯田 / 現場責任者=運営4 / フォトグラファー=写真role月次決定)・外部接続(年間/月次カレンダー Sheet, STORES, Notion, Google Photo, LINE)・Phase 3 向けの種(自律トリガー)候補を frontmatter+本文に編み込み。
- source: 塚越さん 2026-05-23 セッション3 投入

## [2026-05-23] ingest | 飯田淳毅 staff ページ新設
- by: claude
- type: ingest
- pages: [[junki-iida]]
- summary: workflows 言語化中、企画会議メンバー(運営4名+飯田)として登場。Drive Sheet に存在(2025/08/15 登録、未退職、kana=いいだじゅんき、email=junki.iida@gmail.com)。contract / role / area / freee_id は塚越さん埋め待ち。linked_services=[parent-child, kids, adult], linked_workflows=[annual-quarterly-planning, program-execution]。
- source: Drive Sheet「スタッフ登録フォーム(回答)」+ 塚越さん 2026-05-23 セッション3

## [2026-05-23] edit | 3学部ページに linked_workflows を追記
- by: claude
- type: edit
- pages: [[parent-child]], [[kids]], [[adult]]
- summary: harappa-university 配下 3 学部の frontmatter に linked_workflows(annual-quarterly-planning / monthly-cycle / program-execution)と cadence(月3回 / 月1-2回 / 月2回)を追加。本文は引き続き塚越さん埋め待ち。
- source: 塚越さん 2026-05-23 セッション3

## [2026-05-23] edit | 飯田淳毅の Freee ID / role / area を確定
- by: gardener + claude
- type: edit
- pages: [[junki-iida]], people/staff/README.md
- summary: 塚越さん指示で role=フィールドスタッフ・area=逗子 を確定。HMC master_data.csv に Partner ID 102180692 で登録あり → freee_id 確定。contract は塚越さん未明示のため業務委託で仮置き(他業務委託メンバーに準拠、要確認)。README の業務委託テーブル(12→13名)と role 集計(フィールド20→21)を更新。
- source: 塚越さん 2026-05-23 セッション3 指示 + HMC master_data.csv

## [2026-05-23] ingest | Notion フィールドレポート DB のスキーマを取込み
- by: claude
- type: ingest
- pages: [[program-execution]], workflows/README.md
- summary: 塚越さん共有 URL からフィールドレポート DB(collection://ffb8cd73-f4e1-471c-bf2e-305532ead0de)を fetch。プロパティ 11 種(Name/開催日/コース/天気/気温/業務時間/参加組数/体験家族数/参加スタッフ/調理班へのランチオーダー/アルバム)を program-execution.md step 7 に表で反映。コース選択肢に「余の日/海DAY/千葉」があり toC 1-a/b/c 以外のプログラムも同テンプレ運用 = workflows 拡張時の手掛かりとして TODO 登録。
- source: Notion DB「フィールドレポート」 https://www.notion.so/5dab98a40ae443849e3804c0b431abe2

## [2026-05-23] edit | 飯田淳毅ページに「ガクコ core_team 未参加」セクション追加
- by: claude
- type: edit
- pages: [[junki-iida]]
- summary: セッション4 の決定「ガクコ core_team は当面いじらない(飯田は未参加)」を反映。「企画会議メンバー」と「ガクコ core_team」が別概念であることを staff ページに明記。HMG が core_team へ通知を投げ始めるタイミングで再判断する旨も記載。
- source: 塚越さん 2026-05-23 セッション4、docs/decisions/2026-05-23-seeds-design-direction.md

## [2026-05-24] edit | workflows/monthly-cycle.md を A 案テンプレで全面書き直し
- by: claude
- type: edit
- pages: [[monthly-cycle]], workflows/README.md
- summary: セッション5 で workflow が実運用とずれていた問題(月初1日に「前月稼働確認依頼→3ルート精算」「月末に稼働表作成」が抜け)を発見。塚越さん追記情報を元に4ステップ構成(月末/月初1日/月初10日/適宜)で書き直し。各ステップを「目的(Purpose)/現状の方法(Current Method)/改善余地(Improvement Hints)」の三層で記述する A 案テンプレを採用。改善余地表に ❓未検証 / 💡着手可能 / ✋検討済 / 🛠️実装中 のマーカー。workflows/README.md 冒頭にも原則とテンプレを追記。
- source: 塚越さん 2026-05-24 セッション5、docs/decisions/2026-05-24-workflows-as-truth-and-improvement-targets.md

## [2026-05-24] ingest | コドモン(放サボ勤怠管理アプリ)を concepts に登録
- by: claude
- type: ingest
- pages: [[kodomon]]
- summary: 月末稼働表作成フローに登場する外部システム。学童・保育園向け ICT。放サボの参加者管理とスタッフ勤怠に使用。API/MCP 提供有無は未調査(改善余地 ❓ で記録)。CSV エクスポート → 稼働表に手入力が現状。CSV パーサ実装(💡着手可能)を改善候補として明記。
- source: 塚越さん 2026-05-24 セッション5

## [2026-05-25] ingest | workflows/daily-cycle.md を A 案テンプレで新規起草
- by: claude
- type: ingest
- pages: [[daily-cycle]], workflows/README.md (関連メモのみ)
- summary: セッション6 で「HMC のコア機能(朝ブリーフィング → タスク化 → 夜の振り返り)が workflows/ に未登録」が発覚。HMC `hmc_pilot` SKILL の Mode 1/2/3 を Garden 化方針(種起点)で書き直し、5 ステップ構成(recurring-spawn / morning-briefing / 日中編集 / night-review / inbox-process)で起草。各ステップに目的・現状の方法・改善余地表を A 案テンプレで配置。データモデル(backlog=マスタ、active=派生ビュー)も明記。
- source: 塚越さん 2026-05-25 セッション6、docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md, HMC hmc_pilot SKILL
