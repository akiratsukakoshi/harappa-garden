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

## [2026-05-31] index-bootstrap | Stage 1 初回 full scan で index.md を意味的に最新化
- by: claude (with ガクチョ, セッション23 / 菌糸 Stage 1 初回)
- type: index-bootstrap
- pages: index.md
- summary: staff 4名のみ反映の初期化状態から、staff 29名 (contract×role×area の3軸集計) + business 18 (toC harappa-university 学部別 / toC ai / toB 5 / communication 1) + workflows 4本 + concepts 1 + 空カテゴリの位置づけ整理 を反映。Karpathy LLM Wiki 哲学に従い全件列挙はせず「カテゴリ・件数・主要リンク」に絞った。これ以降は菌糸 Mode 3(seeds/mycelium/index-refresh.md、type=index)が日次差分更新を担う。

## [2026-05-25] ingest | workflows/daily-cycle.md を A 案テンプレで新規起草
- by: claude
- type: ingest
- pages: [[daily-cycle]], workflows/README.md (関連メモのみ)
- summary: セッション6 で「HMC のコア機能(朝ブリーフィング → タスク化 → 夜の振り返り)が workflows/ に未登録」が発覚。HMC `hmc_pilot` SKILL の Mode 1/2/3 を Garden 化方針(種起点)で書き直し、5 ステップ構成(recurring-spawn / morning-briefing / 日中編集 / night-review / inbox-process)で起草。各ステップに目的・現状の方法・改善余地表を A 案テンプレで配置。データモデル(backlog=マスタ、active=派生ビュー)も明記。
- source: 塚越さん 2026-05-25 セッション6、docs/decisions/2026-05-25-daily-workflow-and-task-master-architecture.md, HMC hmc_pilot SKILL

## [2026-05-31] index-refresh | 検知 62 件(mirror sync)
- by: mycelium (Stage 1)
- type: index
- pages: index.md(変更なし)
- summary: 全 62 ファイルが同日 20:38 mirror sync による一括タイムスタンプ更新。同日の index-bootstrap (セッション23) が全件カバー済みのため index.md 変更不要と判断。
- detected: staff 33, business 21, workflows 5, concepts 1, その他 2(全て 2026-05-31 mtime)

## [2026-06-02] ingest-raw | RAW ingest 2026-05-31〜2026-06-01
- by: mycelium (Mode 1 ingest-raw)
- type: ingest
- pages: [[daily_operation]], [[tech_infra]]
- summary: 2026-05-31 夜に確認した翌 6/1 期限の持ち越しタスク 5 件の状況記録。月末連絡(前島・永木・りた・晶子、5/30 から繰り返し)・パナソニックホームズ企画書(6/1 締切)・ミポオンライン(持ち越し)・戦略会議日程(持ち越し)・とうぶんかいサイト修正(5/27 から 5 日超過)。ガクチョは翌日持ち越し判断。2026-06-01 夜にシフトアンケートシェアを 6/2 タスクに追加決定。
- source: master/raw/2026-05-31.md, master/raw/2026-06-01.md

## [2026-06-08] ingest | 6月経費精算 Freee 登録完了
- by: mycelium (Mode 1 ingest-raw, 2026-06-09)
- type: ingest
- pages: —
- summary: 2026-06-07付けの経費2件をFreee登録完了。LAWSON プリント代¥60 + OK逗子店 菓子類・文房具など¥4,348(計¥4,408)。部門: こども学部 / 費目: 消耗品費 / 税区分: 課税仕入10%。

## [2026-06-10] ingest-raw | skip - no unprocessed raw
- by: mycelium (Mode 1 ingest-raw)
- type: ingest
- pages: —
- summary: 対象範囲(2026-05-27〜2026-06-09)の全 RAW ファイル 4 件(2026-05-31, 2026-06-01, 2026-06-02, 2026-06-08)が処理済み(last_ingested_at 設定済み)。未処理 RAW なし。

## [2026-06-10] edit | スタッフマスター修正 3 件(S41 invoice_processor 稼働突合で発覚)
- by: claude (with ガクチョ, セッション41)
- type: edit
- pages: [[shiiro-kawamura]], [[aya-higashida]], [[misa-mine]], staff/README
- summary: (1) 河村思依蕗の個人ページ新設(2026-04 加入、契約区分はガクチョ確認待ち、Freee 未登録)(2) 東田彩の個人ページ新設(業務委託・写真、屋号 A and Life、Freee 57561931)(3) 三根さんの正字は「美紗」とガクチョ確定 → Freee 取引先名(API)+ DB_Master_Nicknames を修正、soil の freee_name_variant を撤去。ほか嶋田英津子の 2026-05 稼働シート区分を 業務委託→給与 に修正(Nicknames マスターは既に給与)。29名 → 31名 active。

## [2026-06-10] edit | 河村思依蕗の契約区分を外部スタッフに確定
- by: claude (with ガクチョ, セッション41)
- type: edit
- pages: [[shiiro-kawamura]], staff/README
- summary: ガクチョ確定「請求ナシの外部スタッフ」。soil contract=外部スタッフ、DB_Master_Nicknames PaymentType=追加、2026-05 稼働シートの区分 業務委託→追加 を修正(5月の「追加」払い CSV に正しく載るように)。外部スタッフ 11→12名。

## [2026-06-11] index-refresh | 検知 6 件
- by: mycelium (Stage 1)
- type: index
- pages: index.md
- summary: 東田彩(業務委託・写真)新設 + 河村思依蕗(外部スタッフ)確定 + 三根美紗表記確定(S41) / monthly-cycle 日程確定(S40: 締切7日・集計8日)を index.md に反映。staff 29名→31名・写真5→6・フィールド21→22・外部スタッフ11→12・業務委託13→14・未指定area 6→8。
- detected: staff 3(aya-higashida 新設 / shiiro-kawamura 確定 / misa-mine 表記修正), staff/README 1, workflows 2(monthly-cycle S40確定 / README mtime変化)

## [2026-06-11] ingest-raw | 7月シフトアンケート集計完了
- by: mycelium (Stage A.5)
- type: ingest
- pages: memory/master/raw/2026-06-10.md
- summary: 7月シフトアンケート集計完了(2026-06-10)。有効回答数 14 名(6/8 時点は 11 名 → 3 名が追加回答)、NG マトリクスを Shift_Work_2026-07 シートに書き出し済み。

## [2026-06-11] edit | 運営5名に line_display_name 欄を追加(S42)
- by: claude (with ガクチョ, セッション42)
- type: edit
- pages: people/staff/{akira-tsukakoshi,yuji-wada,shotaro-shimura,kei-suzuki,junki-iida}.md
- summary: field_assistant のメンション紐づけ用に `line_display_name:`(LINE アカウント名)を frontmatter に追加(値は未記入)。LINE 仕様 = メンションは userId 必須・group/room 宛のみ。グループ投入後に webhook が userId+表示名を収集 → `processor.py sync-line-users` が本欄と照合して line_users.json(全 nicknames → userId)を自動更新する設計。

## [2026-06-12] index-refresh | 検知 5 件
- by: mycelium (Stage 1)
- type: index
- pages: index.md(変更なし)
- summary: S42 で運営5名に line_display_name フィールドを追加(値は未記入)。集計値・ロール変更なし → index.md は Pattern A で変更不要と判断。
- detected: staff 5(akira-tsukakoshi / yuji-wada / shotaro-shimura / kei-suzuki / junki-iida)

## 2026-06-12 (セッション43)

- by: claude (with ガクチョ)
- type: edit
- pages: hiroto-ando.md(新設)/ mie-morite.md / yuji-wada.md / shotaro-shimura.md / kei-suzuki.md / akira-tsukakoshi.md
- summary: ①運営5名(塚越/和田/志村/鈴木/飯田除く4名+塚越)の line_display_name 記入 + 和田にひらがなニックネーム(ゆーじさん/ゆーじ)追加(LINE メンション有効化) ②安藤寛人ページ新設(大阪・業務委託・freee_id 47229597。31→32名)③大阪2名(mie-morite / hiroto-ando)に invoice_monthly: true 新設(稼働シート外だが毎月請求が来る → invoice check が突合対象に含めるフラグ、ガクチョ指定)

## [2026-06-13] index-refresh | 検知 6 件
- by: mycelium (Stage 1)
- type: index
- pages: index.md
- summary: 安藤寛人(大阪・業務委託・フィールドスタッフ)新設に伴い、staff 31名→32名・業務委託14→15・フィールドスタッフ22→23・大阪エリア2→3 を index.md に反映。
- detected: staff 6(hiroto-ando 新設 / akira-tsukakoshi / mie-morite / shotaro-shimura / kei-suzuki / yuji-wada は mirror mtime のみ、実質変更は hiroto-ando のみ)

## 2026-06-14 (セッション44)

- by: claude (with ガクチョ)
- type: edit
- pages: [[maho-kumazawa]](新設)/ [[shiiro-kawamura]] / staff/README.md / index.md
- summary: ガクチョが請求処理向けに2名を Freee 取引先登録した報告を soil に反映。①熊澤満穂ページ新設(外部スタッフ・フィールド・2026-04 加入・2026-05 稼働シート区分=追加で確認。Freee 取引先コード Z102 / 数値ID 118889424)②河村思依蕗の freee_id を 118889450(取引先コード Z103)で確定・freee_type を manual→partner(これまで「Freee 未登録」だった外部スタッフ追加払いの partner 解決用)。③README 業務委託表に安藤寛人(S43新設・index.md には反映済だが README 表だけ漏れていた)を追記し active 31→33・業務委託14→15・外部12→13 に整合。④index.md を 32→33・外部13 に更新。
- note: ⚠️ ガクチョのメッセージは「河村 Z102 / 熊澤 Z103」だったが Freee 実データは逆(熊澤=Z102 / 河村=Z103)。Freee を正本として記録。安藤寛人は大阪フィールドスタッフ(page の role に元から記載あり)として role 集計に計上 → フィールドスタッフ 23→24(ガクチョ確認 2026-06-14)。
- source: Freee Partner DB(get_partners: 熊澤満穂=118889424/Z102, 河村思依蕗=118889450/Z103), 2026-05_稼働時間シート(区分=追加)

## [2026-06-15] index-refresh | 検知 3 件
- by: mycelium (Stage 1)
- type: index
- pages: index.md
- summary: 2026-06-14(S44)で更新された3ファイルを検知。counts は index に反映済みのため変更なし。河村思依蕗 Freee Z103 / 熊澤満穂 Z102 の登録を集計外メモに追記。
- detected: staff 2(shiiro-kawamura Freee Z103 確定 / maho-kumazawa 新設 Freee Z102), staff/README 1

## [2026-06-15] ingest-raw | 2026-06-14 RAW
- by: mycelium (Mode 1 ingest-raw)
- type: ingest
- source_date: 2026-06-14
- pages: [[daily_operation]]
- summary: 5月分請求書 Freee登録完了(67件・¥799,516・エラー0)を daily_operation wiki に追記。外部スタッフ2名(河村思依蕗・熊澤満穂)の Freee 登録情報は S44 で soil 既記録のため staff メモ追記 skip。グレー廃棄 4 turn。

## [2026-06-18] index-refresh | 検知 23 件
- by: mycelium (Stage 1)
- type: index
- pages: —(大規模変更のため index.md は更新せず)
- summary: manual full scan needed — clients/(MTI 研修プロジェクト群) 11件・finance/ 8件・people/clients/ 2件・projects/ 2件 を検知。>20件超過ルール適用。index.md の自動更新は skip。庭師による手動 full scan を推奨。
- detected: clients 11, finance 8, people/clients 2, projects 2 (合計 23件)
