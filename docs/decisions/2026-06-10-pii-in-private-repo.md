# ADR: soil/people の個人情報を private repo に置くことの条件付き承認

日付: 2026-06-10
セッション: 39
ステータス: 採用(案A: 条件付き承認。案B は将来の宿題)

## 文脈

S39 のセキュリティレビューで、`garden/soil/people/`(staff 29 名 + clients / partners)に
スタッフの本名・メールアドレス・freee_id 等の個人情報が **34 ファイル、git 管理下**で存在し、
GitHub(`akiratsukakoshi/harappa-garden`)に push されていることが指摘された。

事実確認(2026-06-10 実施):

- リポジトリは **非公開**(未認証の GitHub API で 404 を確認)
- 現時点でアクセスできるのはガクチョのみ(コラボレータなし)
- soil は「repo = 構造ファイル正本 / VPS = 菌糸ログ正本 / vault = 読み取りビュー」の
  3 箇所同期アーキテクチャ([ADR 2026-06-02](2026-06-02-soil-source-of-truth.md))の中核であり、
  people/ だけを git から外すと正本・運搬経路の再設計が必要になる

## リスクの整理

現在のリスクは顕在化していない。顕在化するのは以下の 3 パターン:

1. リポジトリを誤って public に切り替えた場合
2. コラボレータを追加した場合(全員がスタッフ全データを閲覧可能になる)
3. GitHub アカウント自体が侵害された場合

## 決定(案A: 条件付き承認)

**個人情報を含む soil/people/ を private repo に置くことを、以下の条件付きで意識的に承認する:**

| # | 条件 |
|---|---|
| 1 | リポジトリの **非公開を維持**する。public 化は理由の如何を問わず行わない |
| 2 | **コラボレータを追加する前に、必ず people/ の扱いを再検討**する(本 ADR を更新するか、案B に移行してから追加する) |
| 3 | GitHub アカウントは 2FA を維持する |
| 4 | soil に書く個人情報は業務上必要な範囲に留める(住所・銀行口座等の高機密情報は soil に書かない。それらは Freee 側を正とする) |

## 将来の選択肢(案B: チーム公開時に再設計)

チームメンバーに repo アクセスを開くタイミングが来たら、people/ を VPS 正本に引っ越す
(memory raw と同じ「VPS 専属 + .gitignore 除外」パターン)。
これは soil-sync / mirror-daemon / LiveSync の経路再設計を伴うため、独立セッションで行う。
permanent 記憶の Stage D(マスター透視権・スコープ分離)と同時に検討するのが自然。

## 関連

- [ADR 2026-06-02 soil-source-of-truth](2026-06-02-soil-source-of-truth.md)
- [ADR 2026-05-31 memory-three-layer-and-soil-routing](2026-05-31-memory-three-layer-and-soil-routing.md)(raw の VPS 専属パターン)
- [docs/security/README.md](../security/README.md)
