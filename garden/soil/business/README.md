---
type: collection
status: active
dynamism: static
last_updated: 2026-05-22
last_updated_by: claude
---

# HARAPPA(株) 事業構造

## 法人構造

**HARAPPA 株式会社**(単一法人)。原っぱ大学・放課後サボール・俺のヨガ等はすべて **法人配下のサービス名**(別法人ではない)。

## サービス階層

```
HARAPPA(株)
├─ toC事業
│  ├─ 原っぱ大学
│  │  ├─ おとな学部
│  │  ├─ こども学部
│  │  └─ おやこ学部
│  ├─ 原っぱ大学 大阪
│  ├─ 放課後サボール(逗子)
│  ├─ 俺のヨガ(逗子)
│  ├─ 各種イベント
│  └─ AI関連
│     ├─ AIBOU GYM(AIパーソナルトレーナー)
│     └─ デジタル原っぱ大学(学びの場)
├─ toB事業
│  ├─ 研修・組織開発
│  ├─ コミュニティマネジメント
│  ├─ 単発イベントプロデュース
│  ├─ みうらの森林共創プロジェクト(京急電鉄との共同事業)
│  └─ その他イベント出演等
└─ 横断 / コミュニケーション
   └─ メルマガ(週1)
```

## ディレクトリと slug

| 配下 | slug |
|---|---|
| [toC/](toC/) | toC事業 |
| [toC/harappa-university/](toC/harappa-university/) | [[harappa-university]] |
| [toC/harappa-university/adult.md](toC/harappa-university/adult.md) | [[adult]] おとな学部 |
| [toC/harappa-university/kids.md](toC/harappa-university/kids.md) | [[kids]] こども学部 |
| [toC/harappa-university/parent-child.md](toC/harappa-university/parent-child.md) | [[parent-child]] おやこ学部 |
| [toC/harappa-osaka.md](toC/harappa-osaka.md) | [[harappa-osaka]] 原っぱ大学大阪 |
| [toC/saboru-zushi.md](toC/saboru-zushi.md) | [[saboru-zushi]] 放課後サボール |
| [toC/ore-no-yoga.md](toC/ore-no-yoga.md) | [[ore-no-yoga]] 俺のヨガ |
| [toC/events.md](toC/events.md) | [[events]] 各種イベント |
| [toC/ai/aibou-gym.md](toC/ai/aibou-gym.md) | [[aibou-gym]] |
| [toC/ai/digital-harappa.md](toC/ai/digital-harappa.md) | [[digital-harappa]] |
| [toB/training.md](toB/training.md) | [[training]] 研修・組織開発 |
| [toB/community-management.md](toB/community-management.md) | [[community-management]] |
| [toB/event-production.md](toB/event-production.md) | [[event-production]] 単発イベントプロデュース |
| [toB/miura-forest.md](toB/miura-forest.md) | [[miura-forest]] みうらの森林共創 |
| [toB/other-appearances.md](toB/other-appearances.md) | [[other-appearances]] その他出演等 |
| [communication/newsletter.md](communication/newsletter.md) | [[newsletter]] 週1メルマガ |

## frontmatter スキーマ(service)

```yaml
---
type: service
service_type: toC | toB | communication
status: active | inactive | archived
dynamism: static
parent:                       # 親サービス(あれば)
linked_staff: []              # 担当 staff の [[slug]]
linked_clients: []            # 関連 client の [[slug]]
linked_projects: []
sources: []
last_updated: 2026-05-22
last_updated_by: claude
---
```
