# soil/projects — 進行中プロジェクト(toB案件など)

原っぱ大学の**進行中プロジェクト**を置く土壌。中心は **toB 案件**(企業研修・コンサル・共創)。各案件は金額・計上月・確度・freee反映状況を持ち、**財務の着地予測([soil/finance/](../finance/))と直結**する。

## なぜ soil か

toB案件は「全体に紐づく」経営情報:売上着地・CF・クライアント([soil/clients/](../clients/))・担当([soil/people/clients/](../people/clients/))を横断する。finance の議論ログ([soil/finance/discussions/](../finance/discussions/))に埋もれていた案件群を、ここに**正本として昇格**させ、相互リンクする。

## 🚧 宿題(S47 / ガクチョ「必ずやりたい」)→ S48 で型確立

**S48: [soil/clients/](../clients/) の2層構造(企業→案件、a〜f+finance)を確立 + MTI を型の参照実装(第1号)として縦通し完了。** 残りの昇格作業:

1. [x] 案件を**個別プロジェクトファイル**に展開する型を確立(MTI 3案件で実施。`README.md` frontmatter に金額/計上月/確度/freee反映 + a〜f スロット)
2. [~] クライアント企業を [soil/clients/](../clients/) に正本化 — **MTI 完了**。残り(パナHM / ゴンチャ / boundlesslife / 白井松 / 三井 / 京急)は MTI を参照に横展開
3. [ ] finance の月次議論([soil/finance/discussions/](../finance/discussions/))から案件を参照する形に整える(着地予測の根拠が辿れる)
4. [ ] 案件のステータス更新を月次サイクル(finance Mode A の 10日)に組み込む
5. [ ] **次段(d/f 生成)**: 見積/請求を [templates](../finance/templates/) から自動生成 → PDF/Excel レンダリング capability(将来 plot 化の候補 = client_steward)
6. [ ] **次段(a/b 取り込み)**: Plaud プロジェクト側 MCP の OAuth(ガクチョ)→ 打合せ自動取り込みの動線

> 構造仕様 = [soil/clients/README.md](../clients/README.md)。この宿題は [garden/MAP.md](../../MAP.md) + memory にも記録。
