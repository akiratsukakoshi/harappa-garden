# Finance Analyzer - ユーザーマニュアル

**Finance Analyzer** は、freeeの財務データ（PL・BS・CF）をリアルタイムで取得し、**チャット上で財務状況を即時確認・将来予測・戦略議論**するためのアプリケーションです。

従来の kpi_monitor（Sheetsへの書き出し型）を発展させた後継スキルです。「数字を見ながらAIと議論する」ことを中心に設計されています。

---

## 主な機能

- **データ品質チェック (check):** 月別の部門未設定件数・未決済件数を集計し、分析前の帳票精度を確認します。
- **PL表示 (pl):** 月次損益計算書をチャット上にテーブル表示します。目標比・累計も自動算出。CSVにも保存されます。
- **CF分析 (cf):** 口座残高の現況と、月次営業利益ベースのキャッシュフロー推移・年度末予測を表示します。
- **財務サマリー (summary):** PL・CF・口座残高・目標達成率を一括集計し、戦略議論用のサマリーを生成します。
- **目標管理 (targets):** 年間の売上・利益目標を設定・保存します。以降のコマンドで自動参照されます。

---

## 利用方法（AIエージェント / Skill）

AIエージェントに以下のように指示するだけで利用できます。

> 「今月のPLを見せて」
> 「今の財務状況を確認したい」
> 「キャッシュフロー、大丈夫か確認して」
> 「年度末の着地予測を出して」
> 「目標達成のために何が必要か議論したい」

---

## 利用方法（手動実行）

### 初回セットアップ：目標値の設定

```bash
python3 apps/finance_analyzer/analyzer.py targets \
  --fiscal-year 2025 \
  --fiscal-start-month 10 \
  --set-revenue 15000000 \
  --set-operating-profit 2500000 \
  --notes "昨対比120%目標"
```

設定は `data/finance_analyzer/targets.json` に保存され、以降のコマンドで自動参照されます。

---

### データ品質チェック

分析前にデータの状態を確認します。部門未設定が多い場合は先に `freee_auditor` で整理することを推奨します。

```bash
python3 apps/finance_analyzer/analyzer.py check
python3 apps/finance_analyzer/analyzer.py check --fiscal-year 2025
```

---

### PL（損益計算書）の確認

```bash
# 会計年度全体（全12ヶ月）
python3 apps/finance_analyzer/analyzer.py pl --fiscal-year 2025

# 上半期のみ（財務月1〜6 = 10月〜3月）
python3 apps/finance_analyzer/analyzer.py pl --fiscal-year 2025 --start-month 1 --end-month 6
```

売上高 / 売上原価 / 売上総利益 / 販売管理費 / 営業利益が月次テーブル形式で表示されます。
`data/finance_analyzer/reports/pl_fy2025_YYYYMMDD.csv` にも自動保存されます。

---

### キャッシュフロー分析

```bash
python3 apps/finance_analyzer/analyzer.py cf
python3 apps/finance_analyzer/analyzer.py cf --months 6
```

口座・カード別の残高と月次CF推移が表示されます。年度末時点の推計残高と、資金ショートが懸念される月も自動で検出します。

---

### 財務サマリー（戦略議論用）

最も総合的なコマンドです。全データを集約し、AIとの戦略議論の起点となるサマリーを生成します。

```bash
python3 apps/finance_analyzer/analyzer.py summary
```

**出力内容：**
- 現金・預金残高（口座別）
- PL実績累計と目標比
- 現ペース継続時の年度末着地予測
- 目標達成に必要な月次売上の試算
- 詳細JSONファイル（`data/finance_analyzer/reports/summary_fy2025_YYYYMMDD.json`）

このサマリーをもとに以下の議論をAIと行えます：
- 「このままだと年度末はどう着地するか」
- 「目標達成のために何が必要か」
- 「資金ショートの危険はどの月か」
- 「どの事業・部門に注力すべきか」

---

## 推奨ワークフロー

```
① targets で目標値を設定（初回のみ）
        ↓
② check でデータ品質確認
        ↓ （部門漏れがあれば freee_auditor で修正）
③ pl / cf で現状把握
        ↓
④ summary でサマリー生成 → AIと戦略議論
        ↓
⑤ 必要に応じてCSV/Sheetsにエクスポート
```

---

## ディレクトリ構成

| パス | 内容 |
|---|---|
| `data/finance_analyzer/targets.json` | 目標値設定ファイル |
| `data/finance_analyzer/reports/` | PL・CF・サマリーのCSV/JSONレポート |

---

## 注意事項

- **`check` コマンドは全取引をAPIで取得するため、1年分だと数十秒かかる場合があります。**
- **年度末予測は「現在の月次平均が継続した場合」の機械的試算です。** 季節変動・予定大型案件等は別途考慮が必要です。
- **CF分析の営業利益はキャッシュフローの近似値です。** 設備投資・借入返済など資本的支出は含まれません。正確なCFが必要な場合はfreee上のCFレポートを参照してください。
- 目標値が未設定（0円）の場合、目標比の表示はスキップされます。

## 連携スキル・ツール

- **freee_auditor:** データ品質に問題がある場合はこちらで部門修正を行う
- **kpi_monitor:** 過去のSheetsダッシュボードが必要な場合は引き続き利用可能（非推奨）
