# soil/finance — 財務・経営戦略の土壌

原っぱ大学の**経営・財務の文脈(知識)**を置く土壌ドメイン。`soil/people`・`soil/business` と並ぶ。

ここは「どう動かすか(実装)」ではなく、**Garden 全体が参照する経営コンテキスト**:目標・売上見込み・着地予測・案件パイプライン・戦略議論。finance 区画([garden/plots/finance/](../../plots/finance/SKILL.md))の Mode A(財務分析)が**継続性のため**ここを読む。

## 構成

| パス | 中身 |
|---|---|
| [discussions/](discussions/) | 経営・財務の議論ログ(議事録)。日付ごと。**毎月の壁打ちはここに追記** → 議論を地続きに蓄積 |
| [targets.md](targets.md) | 年間目標と根拠の**人間可読 正本**。`garden/services/finance/config/targets.json`(機械読み)はこのミラー |

## 正本ルール

- **soil/finance が経営知識の正本**。service の `targets.json` は analyzer が目標比計算で機械読みする cache(soil = 真実、json = 派生)。両者がずれたら soil を正とする。
- 議論ログは HMC `finance_analyzer/discussions/` から継承(2026-04-18 / 2026-05-19)。S47 で Garden soil に移設。

## 横断リンク(育てる先)

財務の着地予測は **toB 案件(soil/projects/)・クライアント(soil/clients/)・各事業(soil/business/)** と紐づく。discussions に出てくる案件・取引先を soil の正本に昇格させ、相互リンクしていく。
- → [garden/soil/projects/](../projects/)(toB案件。**昇格は宿題**、README 参照)
