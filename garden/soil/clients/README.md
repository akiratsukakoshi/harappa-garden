# soil/clients — クライアント企業の正本(toB ナレッジの軸)

原っぱ大学の **toB クライアント企業**を、案件・打合せ・資料・見積・実績・請求・財務が **横断して辿れる正本**として置く土壌。ここが育つと「人の頭の中にしかない横断把握」が**問い合わせ可能な資産**になる(打合せ前ブリーフィング / 提案の再利用 / 値付けの一貫性 / 着地予測の根拠化 / 請求漏れ検出 / 経営の打ち手)。

## 2層モデル — 企業(client)と 案件(project)

```
soil/clients/{企業slug}/
  ├─ README.md                    ← ① 企業正本(プロフィール・担当者・関係史・案件インデックス)
  └─ projects/{案件}/
       ├─ README.md               ← ② 案件台帳(single pane)= a〜f + メール + finance を一望
       ├─ meetings/               ← a 打合せ(客) / b 打合せ(社内)。Plaud 由来の MD
       ├─ emails/                 ← メール(Gmail 由来。要点 + thread_id、本文は Gmail 残す)
       ├─ materials/              ← c 資料(MD 正本 +(将来)PPT/Word export)
       ├─ estimate.md             ← d 見積(庭が生成 → freee 着地に接続)
       ├─ deliverable.md          ← e 納品物・実績(レポート MD)
       └─ invoice.md              ← f 請求(庭が生成 → freee 記帳に接続)
```

- **企業が家、案件はその中**。1社が複数案件を持つ(例: MTI = 新人研修 / 経営研修 / 経営者研修)。関係そのもの=企業が一番長持ちする資産。
- **案件台帳 README が「一枚の管」**。打合せも見積も請求も freee 反映状況も、そこを見れば全部辿れる。[soil/projects/toB-pipeline.md](../projects/toB-pipeline.md) の1行が、この台帳に「展開」される。

## a〜f の2種類 — 知識(正本)と 成果物(収穫物)

案件は必ずこのライフサイクルを通る:

```
打合せ(a/b) → 資料 c → 見積 d →〔受注〕→ 納品/実績 e → 請求 f →〔入金=freee〕
└─ 知識(正本)─┘   └────── 成果物(収穫物)──────────┘   └─ 財務 ─┘
```

| 項目 | 中身 | 性質 | 由来 |
|---|---|---|---|
| **a 打合せ(客) / b 打合せ(社内)** | 何を話したか・決めたか | **知識(soil 正本)** | Plaud(MCP 取り込み) |
| **c 資料** | 提案書・企画書 | 成果物 | a/b + 過去資産から生成(将来 cowork 移植) |
| **d 見積** | 御見積書 | 成果物 | a/b + 値付けパターンから生成 |
| **e 実績** | 納品レポート | 成果物 | 開催後に生成 |
| **f 請求** | 御請求書 | 成果物 | d + 実績から生成 → freee 記帳 |

## メールの動線(Gmail)

- 企業に `primary_domain`(例 `mti.co.jp`)、担当者に `email` を持たせ、**ドメイン/アドレスで Gmail を引いて**案件に紐付ける。Garden は既に **invoice_processor の user OAuth token**(`gmail.modify`=読取可)を持つので流用できる。
- **soil 正本**は打合せと同じ粒度:**スレッドの要点 + 参加者 + `gmail_thread_id` 参照**。本文は Gmail に残す。
- メールが効く所:① 打合せ前ブリーフィング(打合せ+直近メール)② 案件ステータスの自動鮮度維持(見積送付/発注/請求/入金がメールに出る → finance 突合)③ 抜け漏れ検出(未返信・入金期限)④ **担当者の実名・役割を署名から確実に発見**(Plaud 話者の不確かさを補完)⑤ 受注の因果の裏取り(リピート導線)。

## Plaud 取り込みの動線(a/b)

- Plaud は **プロジェクト側 MCP**(repo `.mcp.json`、[ADR 2026-06-17](../../../docs/decisions/2026-06-17-plaud-mcp-project-side.md))。ベンダー中立(どの LLM ランタイムからも使える)。
- 録音は `list_files`(名前・日付で検索)→ `get_note`(AI サマリ)/ `get_transcript`(全文)で引ける。
- **soil に固定する粒度**:打合せ MD の正本は **AI サマリ note + メタdata(日付・種別 a/b・参加者・`plaud_file_id`)**。**全文 transcript は soil に常駐させない**(クライアント機密 + 肥大化回避)。必要時に `plaud_file_id` で MCP から都度引く。

## データ分類(クライアント機密)

- 本 repo は private([PII 案A ADR](../../../docs/decisions/2026-06-10-pii-in-private-repo.md))。クライアントの経営戦略など機密度はスタッフ PII より高い。
- 打合せは **サマリ note を正本**とし、生の発言録(transcript)は Plaud 側に残す(file_id 参照)。要機密案件は案件台帳 frontmatter に `confidential: true` を立てる。
- **書き込み粒度(S53 確定)**:`get_note` の生出力を貼らず**要約し直して**書く(生 dump 禁止)。**具体数字(金額等)は含めてよい** — 可読性 + finance 突合のため。機密対策は「生 transcript を外す + private repo + `confidential`」で担保し、数字削除では担保しない。詳細は [scribe SKILL](../../plots/scribe/SKILL.md) Step 3 の3層モデル。

## 案件台帳の frontmatter schema(機械可読の枠)

案件 `projects/{案件}/README.md` の frontmatter は、人が読む散文とは別に **finance/briefing が機械で拾える枠**を持つ(測量士 2026-06-17 #4#5#2 採用、S50)。空欄でもよい(sweep / 本文確認で順次埋める)。

```yaml
type: soil_project
client: {slug}          # 原っぱの契約相手(=入金元・請求先)の slug
end_client:             # ★実施先 ≠ 契約相手 のとき記入(代理店/紹介商流型)。同一なら省略可
project: {案件名}
status:                 # 進行中 / 受注 / 完了 など
# --- finance linkage(#4: finance Mode A が機械突合)---
amount:                 # 税抜・案件総額(粗い見込み)
計上月:                 # 例 2026-07(複数なら "2026-06 / 2026-09")
確度:                   # 見込み / 確定
estimate_amount:        # 見積額(税抜)
invoice_amount:         # 請求額(税抜)
freee_deal_id:          # freee 取引ID(記帳後)
payment_status:         # 未請求 / 請求済 / 入金済
department:             # freee 部門
freee反映: false        # bool(記帳済か)
# --- 担当者の役割(#5: 案件単位の relationship)---
roles:                  # "氏名 : sponsor/coordinator/finance_contact/decision_maker/day_of_contact"
  - ""
# --- 未確定情報(#2: sweep/briefing が回収)---
uncertainties:
  - ""
confidential: true
plaud_query:            # Plaud 検索キーワード(無ければ空)
last_synced:            # sweep watermark(thread の最新時刻)
last_updated:
```

- **finance linkage**:見積 d → 請求 f → freee 記帳(finance 区画 Mode I)→ 入金、の鎖が台帳で辿れる。finance Mode A が client soil を読み「請求済だが入金未確認」「見込みと Freee 実績の差」を出せる。[soil/projects/toB-pipeline.md](../projects/toB-pipeline.md) と [soil/finance/](../finance/) の着地予測に直結。
- **roles**:同じ人でも案件ごとに役割が違う(決裁者/実務窓口/finance 窓口/当日担当)。人ページ([people/clients/](../people/clients/))は名簿、案件 README の `roles` が「この案件での役割」。
- **uncertainties**:「7/2 or 7/3」「freee 未反映かも」のような曖昧を捨てず first-class に。client_steward が次回 sweep / briefing で回収。

## 横展開(型の使い方)

最初に **MTI** で a〜f + finance を縦に1本通して型を確定した([mti/](mti/))。新規クライアントは MTI を参照実装としてコピーする。見積/請求の様式は [soil/finance/templates/](../finance/templates/)、HARAPPA 固定情報は [soil/finance/harappa-billing.md](../finance/harappa-billing.md)。

### 型ライブラリ(2026-06-18 時点・7社で5型)

bootstrap は **Claude 手起こし + SKILL 型ライブラリ**([ADR 2026-06-18](../../../docs/decisions/2026-06-18-client-bootstrap-manual-not-scaffold.md))。診るときは下表の型を参照実装に。

| 型 | 構造 | お金の向き | 代表クライアント |
|---|---|---|---|
| **研修連鎖型** | 1社で研修案件が連鎖(新人→経営→AI 等) | 原っぱ→クライアントに請求(請求先) | [MTI](mti/)・[フージャース](hoosiers/)・[スキルインフォ](skill-informations/)・ゴンチャAI研修 |
| **継続運営型** | コミュニティ/場の月次運営(チラシ→開催→レポート) | 月額で請求 or 前受取り崩し | [パナHM](panasonic-homes/)・[三井CACR1](mitsui-residential/)・京急桐畑 |
| **共創パートナー型** | 原っぱが場の主管に参画、派生案件が生まれる | ★**支払先**(原っぱ→主管に外注費=商流が逆) | [京急 みうらの森林](keikyu/) |
| **人事起点・多案件型** | 1社の人事部窓口から人と組織の案件が多数派生 | 案件ごとに性格が違う(請求/利益なし混在) | [ゴンチャ](gongcha/) |
| **代理店/紹介商流型** | ★**契約相手(入金元)と実施先が別企業**。委託元が複数エンドクライアントを束ねる | 原っぱ→**委託元に委託費を請求**(実施先には請求しない) | [エイチ・ティー](ht/)(→白井松/一丸) |

> **`end_client` フィールド**: 代理店/紹介商流型では `client`(契約相手=入金元)と実施先が別。案件 frontmatter に `end_client` を立て、企業 README の案件インデックスにも end_client 列を持たせる。

> **schema 凍結の判断**(2026-06-18・7社到達): 5型が出揃い、枠は **`end_client` 1つの追加**で全社収まった。残るは boundlesslife(Gmail 死角・FB Messenger 専用)等の特殊例。型は安定とみてよい段階。

## 資料アーカイブ(Windows/Dropbox・WSL から参照可)

ガクチョの PC（Dropbox）に過去の実体ファイルがある。WSL からは `/mnt/c/...` で読める(2026-06-18 アクセス確認済)。c 資料・d 見積・f 請求の **実物 PDF/Excel/docx** の所在。

| 種別 | パス(WSL) | 中身 |
|---|---|---|
| **受託資料**(c 資料・提案・企画) | `/mnt/c/Users/tukap/Dropbox/PC間やり取り/5_受託/` | クライアント別フォルダ(15_MTI / 17_三井 / 18_京急 / 5_フージャーズ / 白井松新薬 / ゴンチャ / パナソニックホームズ / boundlesss life 等)。提案書・オーダーシート・MTG メモ |
| **請求書**(f 請求・会計) | `/mnt/c/Users/tukap/Dropbox/PC間やり取り/1_経理_HARAPPA/` | 年度別決算フォルダ(201509〜202509決算)。過去の請求書一式。finance 突合の一次資料 |

> 案件台帳の d/f が「⏳ 要再取得」のとき、まずここを当たる。**Dropbox は正本ではなく一次資料置き場**(soil 側に要点を写し、実物は Dropbox 参照)。

## 関連
- [soil/people/clients/](../people/clients/) — クライアント担当者(個人)
- [soil/projects/](../projects/) — 案件パイプライン(財務横断ビュー)
- [soil/finance/](../finance/) — 着地予測・目標・billing 様式
