---
name: client_steward
description: クライアント(toB)の知識(打合せ・メール・見積・実績・請求・担当・財務)を soil/clients に正本として継続蓄積・更新し、横断把握と先回りを可能にする世話役区画。Gmail(ドメイン)と Plaud(名前)の差分を取り込み、横展開(bootstrap)と動的進化(sweep)を同じ道具で回す。
plot: client_steward
status: draft
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

### 手順
1. **Gmail を domain で sweep** → 差出人署名から担当者、スレッド群を取得。
2. **スレッドを案件にクラスタリング**(件名・時期・金額で「どのメールがどの案件か」推定)→ 案件台帳ドラフトを複数生成。
3. **Plaud を名前で検索**(あれば)→ 打合せを案件に突合。**無くてもメールだけで案件の骨格(誰と・何を・いくら・いつ・入金)は立つ** = 横展開の起点は常にドメイン、Plaud は上乗せレーン。
4. **ガクチョが剪定**:案件の切り分け・確度・金額を確認/補正(混線クライアントはここで締める)→ soil 反映。

### 生成物
- `soil/clients/{slug}/README.md`(企業正本:`primary_domain` / 担当者 / 案件index / 受注因果)
- `soil/clients/{slug}/projects/{案件}/`(台帳 + meetings/ + emails/)
- `soil/people/clients/{氏名}.md`(担当者、署名由来=確実)

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

- **MVP** = Mode S の週次 sweep 種1本(当面 active = MTI のみ)+ Mode B の bootstrap ツール(`sweep_client`)。
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
