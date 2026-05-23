# staff/ — HARAPPA スタッフ

HARAPPA(株)に関わるスタッフのエンティティページ群。**正社員はいない**。

スタッフは「契約関係(contract)」と「役割(role)」の2軸で整理する(2026-05-22 スキーマ改訂):

- **contract**: 1軸・排他。経営 / 業務委託 / 外部スタッフ / アルバイト
- **role**: 複数可・リスト。運営 / フィールドスタッフ / 写真 / 調理 (etc.)

雇用形態(契約)と業務内の役割を分離することで、「業務委託だけど運営も担う」「アルバイトでフィールドスタッフと写真の両方をやる」といった実態を表現する。

## frontmatter スキーマ

```yaml
---
type: staff
status: active                  # active | inactive | alumni
dynamism: dynamic               # 主に dynamic(週〜月で動く)
contract: 経営                   # 経営 | 業務委託 | 外部スタッフ | アルバイト  (1軸排他)
role:                           # 運営 | フィールドスタッフ | 写真 | 調理  (複数可)
  - 運営
kana: つかこしあきら              # ふりがな(ひらがな)
area: 全社                      # 拠点(全社 | 逗子 | 千葉 | 大阪 | etc.)
freee_id: 26224600              # Freee の Partner ID または Employee ID
freee_type: partner             # partner | employee | manual
email:
  - tukapontas@gmail.com
nicknames:
  - ガクチョー
joined: 2014                    # 関与開始(年 or YYYY-MM)
linked_services: []             # business/ 配下サービス
linked_clients: []              # clients/ 配下クライアント
linked_projects: []             # projects/ 配下プロジェクト
sources:
  - "Freee Partner DB (id: 26224600)"
  - "Drive: スタッフ登録フォーム(回答)"
private_details: "Drive: スタッフ登録フォーム(回答) sheet id 1oiCLf34zwhsDqLvGq5WrPCF5dNJi_7SyUS-gc6_VqBo"
last_updated: 2026-05-22
last_updated_by: claude
---
```

## 機微情報の扱い

スタッフ登録フォーム(Drive Sheet)には生年月日・住所・電話・口座・アレルギー・契約書PDFリンク等の **機微情報** が含まれる。これらは **Wiki に書かない**。

- マスター(各スタッフページ)に書くフィールド: `name, kana, area, email, contract, role, freee_id, nicknames` のみ
- 機微情報の参照先は frontmatter の `private_details` に **Sheet ID のみ** を記録
- 必要時(invoice 処理で住所が要る等)は MCP 経由で Sheet を都度照会

理由: Wiki は git 履歴に残るため、機微情報を書き込むと事実上削除できない。private repo でも漏洩リスクは下げたい。

## ページ本文の構造

各スタッフページは下記セクションを持つ(空でも OK):

```markdown
# {{氏名}}({{nicknames[0]}})

## プロフィール
役割、関与開始、得意領域

## 担当領域
- 担当しているサービス([[link]])
- 担当しているクライアント([[link]])
- 関わったプロジェクト履歴

## メモ
業務上の特記事項、契約関係、得意/苦手、コミュニケーションの取り方等

## 履歴
重要な出来事、契約変更、役割変更
```

## 同期方針

- **Freee 同期**: shift_manager の `sync_staff_master.py` 相当の処理を将来 HMG 用に移植
- **Drive のスタッフ一覧との同期**: 塚越さんがシェアした Sheet を Claude が読み込んで反映
- **キー**: Email(複数持つ場合は最初の 1 件をプライマリ)、補助キーとして Freee ID

## 一覧

合計 29名 active(28名 @2026-05-22 + 飯田淳毅 @2026-05-23 追加)。alumni 候補 48名は塚越さん判定で個別ページ化保留。

### 経営(1名)

| slug | 名前 | contract | role |
|---|---|---|---|
| [[akira-tsukakoshi]] | 塚越 暁(ガクチョー) | 経営 | 運営 |

### 業務委託(13名)

| slug | 名前 | contract | role | area |
|---|---|---|---|---|
| [[yuji-wada]] | 和田 祐司(ユージさん) | 業務委託 | 運営 | 逗子 |
| [[shotaro-shimura]] | 志村 正太郎(少佐) | 業務委託 | 運営 | 逗子 |
| [[kei-suzuki]] | 鈴木 慶(慶ちゃん) | 業務委託 | 運営 | 逗子 |
| [[junki-iida]] | 飯田 淳毅(じゅんき) | 業務委託(仮) | フィールドスタッフ | 逗子 |
| [[keiko-uchiyama]] | 内山 景子 | 業務委託 | 写真 | 逗子 |
| [[miho-oyoshi]] | 大吉 美穂 | 業務委託 | 写真 / フィールドスタッフ | 逗子 |
| [[naoko-shiroie]] | 城家 尚子 | 業務委託 | フィールドスタッフ | 大阪 |
| [[kasumi-tachibana]] | 立花 香澄 | 業務委託 | 写真 | 千葉 |
| [[sakiko-nakatsuji]] | 中辻 早希子 | 業務委託 | フィールドスタッフ | 千葉 |
| [[takayuki-maeda]] | 前田 隆行 | 業務委託 | フィールドスタッフ | 千葉 |
| [[misa-mine]] | 三根 美紗 | 業務委託 | 写真 | 逗子 |
| [[mie-morite]] | 守田 美枝 | 業務委託 | フィールドスタッフ | 大阪 |
| [[kosaku-yoshida]] | 吉田 耕作 | 業務委託 | 写真 | 千葉 |

### 外部スタッフ(11名)

| slug | 名前 | contract | role | area |
|---|---|---|---|---|
| [[chihiro-irie]] | 入江 千宙 | 外部スタッフ | フィールドスタッフ | 逗子 |
| [[keisuke-ono]] | 大野 佳祐 | 外部スタッフ | フィールドスタッフ | 逗子 |
| [[hiroki-ono]] | 大野 洋毅 | 外部スタッフ | フィールドスタッフ | 逗子 |
| [[taro-koyama]] | 小山 太朗 | 外部スタッフ | フィールドスタッフ |  |
| [[nazuki-shindo]] | 進藤 凪月 | 外部スタッフ | フィールドスタッフ |  |
| [[masaki-chonan]] | 長南 征樹 | 外部スタッフ | フィールドスタッフ |  |
| [[honoka-nagano]] | 永野 帆夏 | 外部スタッフ | フィールドスタッフ |  |
| [[yuto-fukaya]] | 深谷 結友 | 外部スタッフ | フィールドスタッフ |  |
| [[shion-fujimoto]] | 藤本 志音 | 外部スタッフ | フィールドスタッフ |  |
| [[kota-yamada]] | 山田 航太 | 外部スタッフ | フィールドスタッフ |  |
| [[kio-oyoshi]] | 大吉 希於 | 外部スタッフ | フィールドスタッフ |  |

### アルバイト(4名)

| slug | 名前 | contract | role | area |
|---|---|---|---|---|
| [[shunsuke-akagi]] | 赤木 俊介 | アルバイト | フィールドスタッフ | 逗子 |
| [[tomoyo-kitao]] | 北尾 朋世 | アルバイト | フィールドスタッフ | 逗子 |
| [[etsuko-shimada]] | 嶋田 英津子 | アルバイト | フィールドスタッフ | 逗子 |
| [[eriko-fujita]] | 藤田 恵梨子 | アルバイト | フィールドスタッフ | 逗子 |

### role 集計

| role | 人数 | 内訳 |
|---|---:|---|
| 運営 | 4 | 塚越・ユージ・少佐・慶 |
| フィールドスタッフ | 21 | アルバイト4 + 外部スタッフ11 + 業務委託6(城家・中辻・前田・守田・大吉美穂・飯田) |
| 写真 | 5 | 内山・大吉美穂・立花・三根・吉田(大吉美穂のみ写真+フィールド兼任) |
| 調理 | 0 | 未割り当て |

注: 飯田淳毅は role=フィールドスタッフ だが、企画会議には運営4名と並んで参加する立ち位置(workflows 参照)。

## テンプレート

新規スタッフは [_template.md](_template.md) をコピーして作成。
