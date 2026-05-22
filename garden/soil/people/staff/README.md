# staff/ — HARAPPA スタッフ

HARAPPA(株)に関わるスタッフのエンティティページ群。**正社員はいない**(代表/運営/業務委託/アルバイトの4分類)。

## frontmatter スキーマ

```yaml
---
type: staff
status: active                  # active | inactive | alumni
dynamism: dynamic               # 主に dynamic(週〜月で動く)
role: 代表                       # 代表 | 運営 | 業務委託 | アルバイト
kana: つかこしあきら              # ふりがな(ひらがな)
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

- マスター(各スタッフページ)に書くフィールド: `name, kana, email, role, freee_id, nicknames` のみ
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

| slug | 名前 | role |
|---|---|---|
| [[akira-tsukakoshi]] | 塚越 暁(ガクチョー) | 代表 |
| [[yuji-wada]] | 和田 祐司(ユージさん) | 運営 |
| [[shotaro-shimura]] | 志村 正太郎(少佐) | 運営 |
| [[kei-suzuki]] | 鈴木 慶(慶ちゃん) | 運営 |

## テンプレート

新規スタッフは [_template.md](_template.md) をコピーして作成。
