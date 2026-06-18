# 2026-06-18 クライアント bootstrap は Claude 手動 + SKILL 型ライブラリ。Python はファイル生成しない

- 状態: 決定(セッション50)
- 関連: [client_steward SKILL](../../garden/plots/client_steward/SKILL.md) / [soil/clients/README.md](../../garden/soil/clients/README.md) / 測量士の手紙 [2026-06-17](../surveyor/letters/2026-06-17.md)

## 背景

S50 で「digest → soil 台帳ドラフト生成の自動化」(横展開の一発 bootstrap)に着手し、`sweep_client.py` に **scaffold モード**を実装した:ドメインを渡すと企業 README スケルトン + 機械可読 pack(JSON)+ 担当者 stub を自動でディスクに書き出し、Claude は判断パート(案件クラスタリング・散文)だけ埋める、という「機械80% / 判断20%」の分担。MTI/パナHM(手起こし2社)では綺麗に通った。

## 検証(京急 `keikyu-group.jp`)

3社目に「幅広く事業をする会社」=京急で scaffold を実走(66スレッド)→ 機械抽出の限界が3つ露呈:

1. **漢字氏名が取れない** — 社内メーラーの表示名がローマ字 local part(`asami.ikeda`)。people stub が `asami.ikeda.md` とブサイクになり、結局手直し=**手戻りを増やした**。
2. **最大クラスタがノイズ** — cluster_hint 最頻が「解凍パスワード通知メール」22件(ZIP 別送パスワードの自動メール/PPAP)。案件情報ゼロ。
3. **1案件が表記ゆれで割れ + 他社混在** — 実態は「みうらの森林共創プロジェクト」1案件が20以上の件名 hint に割れ、かつ他社(ゴンチャ/ヤマハ/三浦観光バス)が同一ドメインに混在。機械の cluster_hint は当てにならない。

一方、**bootstrap 自体は破綻しなかった**:Python が全66スレッドの生件名+thread_id を一覧化し、Claude が生件名を読めば正しく束ねられた。= 価値は「ファイル生成」でなく「Gmail を構造化して Claude に渡す素材ダンプ」にあった。

## 決定

横展開クライアントは **10-15社の有限・判断主体**の作業。台帳生成を機械化すると:
- 各社の個性(研修連鎖型/継続運営型/共創パートナー型…)を平準化して潰す
- 抽出ミス(漢字氏名・自動メールのノイズ・案件の表記ゆれ)が手戻りを生む

ので、**soil 台帳は Claude が手で起こす**。Python(`sweep_client.py`)の役割は **「Claude が Gmail を直接読めない」を埋める素材ダンプ(`--domain` digest)に限定**し、ファイル生成(README スケルトン / pack / 担当者 stub)は持たない。

- **力点は SKILL に置く**:手動 bootstrap 手順 + **各社の型ライブラリ**(横展開のたびに追記)。仕組みでなく**記述**が増える形。
- weekly **sweep**(既存 active の差分監視・cron で Claude 不在で回る)は別途有用なので残す。これは「監視」であって「生成」ではない。

## 残す / 捨てる

| 残す | 捨てる(S50 で撤去) |
|---|---|
| `--domain` digest(Gmail 素材ダンプ) | `--scaffold-soil` / `--company`(ファイル生成) |
| weekly sweep(差分監視) + watermark | scaffold 関数群 / bootstrap pack(JSON) |
| 案件 frontmatter の枠3つ(finance_links/roles/uncertainties)+ パナHM 実当て | scaffold の回帰テスト(`test_scaffold.py`) |
| 測量士 P2④⑤(watermark 全ページ化 / 本文 snippet)+ その回帰テスト | — |

枠3つ(測量士 #4#5#2)は scaffold と独立に有用(finance Mode A の機械突合)なので**残す**。

## 抽出 polish の宿題(任意・Python 側)

台帳生成は自動化しないが、素材ダンプの質は上げられる(やるかは費用対効果で判断):
- 自動メール(no-reply / PPAP 解凍パスワード)を digest から除くノイズフィルタ
- 署名本文からの漢字氏名抽出(metadata の表示名では取れない会社向け)

## 振り返り

測量士の申し送り「横展開より先に取りこぼさない仕組みを固めよ」を実践する過程で、**横展開そのものは仕組み化より記述充実が正**と分かった。ガクチョの直感(「さまざまなケースがきちんと記述されることの方が大事」)が、実データ(京急)で裏付けられた一件。
