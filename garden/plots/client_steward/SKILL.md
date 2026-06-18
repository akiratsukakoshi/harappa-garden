---
name: client_steward
description: クライアント(toB)の知識(打合せ・メール・見積・実績・請求・担当・財務)を soil/clients に正本として継続蓄積・更新し、横断把握と先回りを可能にする世話役区画。Gmail(ドメイン)と Plaud(名前)の差分を取り込み、横展開(bootstrap)と動的進化(sweep)を同じ道具で回す。
plot: client_steward
status: test
scope: master
topics: [クライアント, client, toB, 案件, soil, Gmail, Plaud, 打合せ, メール, 見積, 請求, 担当者, sweep, bootstrap, 横展開, ブリーフィング, client_steward]
inherits_from:
  - garden/CHARTER.md
requires_soil:
  - garden/soil/clients/
  - garden/soil/people/clients/
  - garden/soil/projects/
  - garden/soil/finance/
created: 2026-06-17
created_by: claude (with ガクチョ, セッション48)
origin: S48 MTI 縦通し(打合せ Plaud + メール Gmail + 見積/請求 + finance を soil に統合)のプロトタイプを恒常化
---

# client_steward — クライアント台帳の世話役

> 共通の業務観・呼称・トーン・Output Style は [garden/CHARTER.md](../../CHARTER.md)。本 SKILL は「クライアント soil を育て続ける」作法に集中。

## この区画の目的(不変)

クライアントにまつわる知識を **soil/clients に正本として継続的に蓄積・更新**し、放置で陳腐化させない。これにより:
- 打合せ前ブリーフィング(前回要点 + 直近メール + 未決)
- 案件ステータスの自動鮮度維持(見積→発注→請求→入金がメールに出る → finance 突合)
- 請求/フォローの抜け漏れ検出
- 担当者の実名・役割を**メール署名から確実に**発見(Plaud 話者の不確かさを補完)
- 受注の因果(リピート/アップセル導線)の裏取り

構造の正本 = [soil/clients/README.md](../../soil/clients/README.md)(2層 = 企業→案件、a〜f + メール + finance を案件台帳に一望)。

## 中核思想:横展開と動的進化は「同じ道具の別トリガー」

道具は2つだけ:**ドメインで Gmail を引く** / **名前で Plaud を引く**。
- 一度に全部引く = **Bootstrap(横展開)**
- 前回同期以降の差分だけ引く = **Sweep(動的進化)**

→ 案件台帳 frontmatter の `last_synced`(thread_id / Plaud 日付)を watermark に、毎回フルでなく差分で回す。

---

## Mode B: Bootstrap(新規クライアントの横展開)

### Intake(ガクチョからの最小依頼)
```
「{企業名} をクライアント区画化して。
  ドメイン = {例 mti.co.jp}(or 担当メール)
  Plaudの呼び名 = {例 "MTI" / 無し}」
```

### 手順(Claude が手で起こす。Python は Gmail 素材ダンプだけ)

> **設計判断(S50)**:横展開は **10-15社の有限・判断主体**の作業。soil 台帳を機械生成すると、各社の個性(下記 型)を平準化して潰し、抽出ミス(漢字氏名・自動メールのノイズ・案件の表記ゆれ)が手戻りを生む(京急で実証)。**台帳は Claude が手で起こすのが正**。Python の役割は「Claude が Gmail を直接読めない」を埋める**素材ダンプだけ**に限定する。[ADR 2026-06-18](../../../docs/decisions/2026-06-18-client-bootstrap-manual-not-scaffold.md)。

**① Gmail 素材ダンプを出す**(Python の唯一の役割):
```
.venv/bin/python3 garden/services/client-steward/sweep_client.py \
  --domain {例 panasonic-homes.com} --since {例 2025-12-18}
```
→ 動いたスレッド一覧(件名・日付・通数)+ 要フォロー + finance/schedule シグナル + **登場担当者(署名/アドレス)** が出る。Claude はこれを読む(Discord でなくターミナル)。

**② Claude が digest を読んで soil 台帳を手で起こす**(MTI/パナHM を参照実装にコピー):
- digest の**生件名**を読んで **スレッドを案件にクラスタリング**(表記ゆれ・他社混在を判断で束ねる。京急=「みうらの森林共創PJ」が20以上の件名に割れ + ゴンチャ/ヤマハ別件混在 のような会社は丁寧に分ける)。
- `clients/{slug}/README.md`(企業正本:プロフィール・**担当者表**・案件インデックス・受注因果)を書く。
- `projects/{案件}/README.md` を書く([案件 frontmatter schema](../../soil/clients/README.md) = finance_links / roles / uncertainties の**枠込み**)。
- `projects/{案件}/emails/{範囲}_{名}.md` に**読みやすいメールレーン**(運営/請求/打合せ等にまとめる。本文は Gmail に残す)。
- `people/clients/{氏名}.md`(担当者)。**漢字氏名は digest の表示名で取れない会社がある**(京急=ローマ字 local part)→ **署名/本文で漢字を確認**してから作る。ローマ字のまま作らない。
- **Plaud を名前で検索**(あれば)→ 打合せを `meetings/` に。**無くてもメールだけで骨格(誰と・何を・いくら・いつ・入金)は立つ** = 起点は常にドメイン、Plaud は上乗せ。

**③ ガクチョが剪定**:案件の切り分け・確度・金額・freee反映・担当者の roles を確認/補正 → 確定。

### 各社の型ライブラリ(横展開のたびに追記 = この区画の資産)

bootstrap は「テンプレに流す」でなく「一社ずつ診る」。診た型をここに足していくと次が速くなる(仕組みでなく**記述**が増える)。

| 型 | 代表 | 特徴・診るときの注意 |
|---|---|---|
| **研修連鎖型** | [MTI](../../soil/clients/mti/) | 複数の独立案件(新人研修/経営研修/経営者研修)。前案件の成果が次オーダーを生む=受注因果が濃い。Plaud 会議録あり。担当者は署名で確定 |
| **継続運営型** | [パナHM](../../soil/clients/panasonic-homes/) | 1つの継続案件(住民イベント運営)を月次で回す。四半期請求。Plaud 無し=メールだけで骨格。担当者表示名は漢字で取れた |
| **共創パートナー型** | [京急](../../soil/clients/keikyu/)(S50・最難物で実証) | 1つの大型継続案件(みうらの森林共創PJ)が件名表記ゆれで大量に割れる + **他社が混在**(ゴンチャ/ヤマハ/三浦観光バス)+ そこから**派生案件**が複数(桐畑/三浦海岸/品川)。**①PPAP 自動メールがノイズ最多**=数で釣られない。**②表示名がローマ字 local part**=漢字は署名確認必須([本文末尾を取る inline ダンプ](#)で苗字10名確定できた)。**③商流が逆になる案件**=京急は「請求先」でなく「支払先」(パートナー企業→原っぱ入金、原っぱ→京急 外注費)。frontmatter に `freee_partner_role: 支払先` を立てて finance に伝える |

> **診るときの普遍ルール**(京急で確立):①案件の主軸を1つ見極める→件名表記ゆれを束ねる ②他社混在は「連携先(案件内)/別クライアント候補/別NPO等で除外」に三分 ③**お金の向きを必ず確認**(請求先か支払先か。共創・パートナー事業は逆流しうる)④漢字が取れなければ署名本文ダンプ→苗字確定、役割は要確認で保持。
>
> 抽出 polish の宿題(Python 側・任意):自動メール(no-reply/PPAP)を digest から除くノイズフィルタ / 署名本文からの漢字氏名抽出を `sweep_client` に正式化。**ただし台帳生成の自動化はしない**([ADR 2026-06-18](../../../docs/decisions/2026-06-18-client-bootstrap-manual-not-scaffold.md))。京急では inline ダンプで足りた=繰り返し必要になったら正式化。

---

## Mode S: Sweep(既存クライアントの動的進化)

### trigger
定期(MVP=週次)。active クライアントごとに回す。

### 手順
1. 各 active client の `primary_domain` で Gmail を `last_synced` 以降だけ検索 → 新着スレッド/メールの要点を `emails/` に append。
2. Plaud を名前で `last_synced` 以降検索 → 新録音の note を `meetings/` に append。
3. **living 台帳(README)を更新** + watermark 更新。
4. **変化と要フォローを digest 通知**(Discord master):新日程確定 / 見積→発注 / 請求→入金 / 未返信◯日 / 入金期限接近 / 新規案件の芽。
5. **解釈は board 提案**(下記 承認境界)。

---

## Mode R: Brief(打合せ前ブリーフィング)※次段

カレンダーに client 打合せ → 前夜/当朝に「前回要点 + 直近メール + 未決事項」を通知(field_assistant の daily-brief を toB 化)。read-only 通知、承認なし。

---

## 承認境界(知識の質を守る)

| 動作 | 扱い |
|---|---|
| 生取り込み(新メール/録音の**要点を emails//meetings/ に append**) | **自動でよい**(履歴は append-only) |
| 解釈(**確度の変更・案件の統合/新規確定・freee反映の断定**) | **board → ガクチョ剪定 → soil 反映** |
| 担当者の実名確定 | メール署名は自動採用可。Plaud 話者は採用しない(不確か) |

> append-only レーン(meetings//emails/)+ living 台帳(README が「今の真実」)。履歴と現在地を両立。

---

## データ・機密の作法

- **本文は外部に残す**:soil 正本は要点 + 参照ID(`gmail_thread_id` / `plaud_file_id`)。全文は Gmail/Plaud から都度取得。
- private repo だが、クライアント経営情報は機密度が高い → 案件 frontmatter に `confidential: true`。
- token / MCP:**新規 secret 不要**。Gmail = invoice_processor の user OAuth(`gmail.modify`=読取可)流用 / Plaud = プロジェクト側 MCP([.mcp.json](../../../.mcp.json)、[ADR](../../../docs/decisions/2026-06-17-plaud-mcp-project-side.md))/ Calendar・Freee = 既存 service。

## scope(通行手形)

| scope | 使えること | 禁止 |
|---|---|---|
| **master** | 台帳の閲覧・sweep 起動・bootstrap・board 承認・digest 受信 | — |
| core_team | (出さない) | soil/clients 全般(クライアント機密・経営情報) |
| staff | (出さない) | 全部 |

LINE/core_team には開かない(master = Discord 一本、[memory: line-1to1-is-core-staff-pilot])。

## finance との連携

- 案件台帳の `amount` / `計上月` / `確度` / `freee反映` を sweep が更新 → [toB-pipeline](../../soil/projects/toB-pipeline.md) と [finance](../finance/) の着地予測に直結。
- finance 月次(Mode A・10日)が client_steward の最新台帳を読む。

## MVP(draft → test → active)

- **MVP** = Mode S の週次 sweep 種1本(active = MTI + パナHM)+ Mode B(`sweep_client --domain` の Gmail 素材ダンプ → Claude 手起こし)。
- Brief(Mode R)・finance 自動更新・複数クライアント横展開は次段。
- 昇格:dry-run(MTI で sweep 差分が出る)→ 初回 cron 通過 + OPERATIONS カード → active。

## 禁止事項

- 解釈(確度・新規案件・freee反映)を board なしで soil に断定書き込みしない。
- Plaud 話者ラベルから担当実名を機械採用しない(メール署名のみ)。
- core_team / staff / LINE にクライアント機密を出さない。
- 全文 transcript / メール本文を soil に常駐させない(要点 + 参照ID)。

## 関連
- 構造正本: [soil/clients/README.md](../../soil/clients/README.md)
- プロトタイプ: [soil/clients/mti/](../../soil/clients/mti/)(S48 縦通し)
- メタ区画: [plot_gardener](../plot_gardener/SKILL.md)
