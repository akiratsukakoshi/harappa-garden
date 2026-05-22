---
name: finance_analyzer
description: freeeの財務データ（PL/BS/CF）を取得・分析し、現状把握・将来予測・戦略議論をサポートするスキル。kpi_monitorの後継。
---

# Finance Analyzer スキル

freeeから財務データをリアルタイムで取得し、**チャット上で財務状況を即時確認・議論**するためのスキルです。
kpi_monitorの「Sheetsに出力して終わり」ではなく、**フェーズ1（データ品質確認）→ フェーズ2（分析・戦略議論）**の2段階で機能します。

## 発動タイミング

- 「今月のPLを見せて」
- 「今の財務状況を確認したい」
- 「キャッシュフロー、大丈夫か確認して」
- 「年度末の着地予測を出して」
- 「目標達成のために何が必要か議論したい」
- 「今期の数字を整理して戦略を考えたい」

## ディレクトリ構成

- スクリプト: `apps/finance_analyzer/analyzer.py`
- レポート出力: `data/finance_analyzer/reports/`
- 目標設定ファイル: `data/finance_analyzer/targets.json`
- 議事録: `data/finance_analyzer/discussions/`（git除外済み）

---

## コマンド一覧

### `check` — データ品質チェック

部門未設定・未決済の取引を月別に集計し、データに問題がないか確認する。
**フェーズ1の起点として最初に実行することを推奨。**

```bash
python3 apps/finance_analyzer/analyzer.py check
python3 apps/finance_analyzer/analyzer.py check --fiscal-year 2025
```

出力例：
```
月         総件数   部門未設定   未決済
2025-10      45        3 ⚠       8
2025-11      52        0         5
```

部門未設定が多い場合は、先に `freee_auditor` スキルで修正することを推奨する。

---

### `pl` — 損益計算書の表示

月次PLをマークダウンテーブルで表示 + CSVファイルに保存する。

```bash
# 会計年度全体
python3 apps/finance_analyzer/analyzer.py pl --fiscal-year 2025

# 財務月指定（例：第1〜第6月 = 10月〜3月）
python3 apps/finance_analyzer/analyzer.py pl --fiscal-year 2025 --start-month 1 --end-month 6
```

表示項目: 売上高 / 売上原価 / 売上総利益 / 販売管理費 / 営業利益（月次 + 累計 + 目標比）

---

### `cf` — キャッシュフロー分析

口座残高の現状と、月次営業利益をベースにしたCF予測を表示する。

```bash
python3 apps/finance_analyzer/analyzer.py cf
python3 apps/finance_analyzer/analyzer.py cf --months 6
```

表示内容：
- 口座・カード別残高（合計）
- 直近N ヶ月の売上・営業利益推移
- 現ペース継続時の年度末残高予測
- 資金ショートの危険月（ある場合）

---

### `summary` — 財務サマリー（予測・戦略議論用）

**フェーズ2の起点。** 全財務データを一括取得してサマリーを生成する。
JSONファイル + テキストサマリーが出力され、これをもとにAIと戦略議論を行う。

```bash
python3 apps/finance_analyzer/analyzer.py summary
python3 apps/finance_analyzer/analyzer.py summary --fiscal-year 2025
```

出力内容：
- 現金・預金残高
- PL実績累計（目標比）
- 年度末着地予測（現ペース）
- 目標達成に必要な月次売上の試算
- 詳細JSONファイルパス

---

### `targets` — 目標値の確認・設定

年間の売上・利益目標を設定・確認する。

```bash
# 現在の目標を表示
python3 apps/finance_analyzer/analyzer.py targets

# 目標を設定する
python3 apps/finance_analyzer/analyzer.py targets \
  --fiscal-year 2025 \
  --fiscal-start-month 10 \
  --set-revenue 15000000 \
  --set-operating-profit 2500000 \
  --notes "昨対比120%を目標"
```

設定は `data/finance_analyzer/targets.json` に保存され、以降のコマンドで自動参照される。

---

## 推奨ワークフロー

### 初回セットアップ

```bash
# 1. 目標値を設定
python3 apps/finance_analyzer/analyzer.py targets \
  --fiscal-year 2025 --fiscal-start-month 10 \
  --set-revenue XXXX --set-operating-profit XXXX

# 2. データ品質確認
python3 apps/finance_analyzer/analyzer.py check
```

### 定期確認（月次）

```bash
# データ品質チェック → 問題あれば freee_auditor で修正
python3 apps/finance_analyzer/analyzer.py check

# 最新PL確認
python3 apps/finance_analyzer/analyzer.py pl --fiscal-year 2025

# キャッシュ確認
python3 apps/finance_analyzer/analyzer.py cf
```

### 戦略議論（四半期・半期）

```bash
# サマリー生成
python3 apps/finance_analyzer/analyzer.py summary

# → 出力を読んでAIと議論：
#   「このペースで年度末はどうなる？」
#   「目標達成に何が足りない？」
#   「どの部門・事業に注力すべきか？」
```

---

## フェーズ2 議論ガイド（AIへの指示）

`summary` コマンドの出力を受け取ったら、以下の観点でユーザーと議論する：

1. **現状診断**: 実績が目標より上か下か、どの項目が乖離しているか
2. **CF安全性**: 資金ショートリスクの有無。危険月の特定
3. **着地シナリオ**: 「現ペース継続」「月次X円上積み」「コスト削減」の3シナリオを試算
4. **アクション提案**: 目標達成のために何をすべきか（売上施策 / コスト管理 / 資金調達）
5. **部門別分解**: 全社PLだけでなく部門別の貢献度を確認（必要に応じて `pl --section-id` で深掘り）

---

## 注意事項

- `check` コマンドは全取引をAPIで取得するため、1年分の場合は数十秒かかることがある。
- `summary` の年度末予測は「現在の月次平均が継続した場合」の機械的試算。季節変動や計画は別途考慮が必要。
- 目標値（`targets.json`）が未設定（0円）の場合、目標比の表示はスキップされる。最初に `targets` コマンドで設定することを推奨。
- PLの「営業利益」はキャッシュフローの近似値として使用している。設備投資・借入返済等の資本的支出は含まれない。

## 議事録の保存

戦略議論・目標設定・月次レビューなど重要なやり取りの後は、議事録をMarkdownで保存する。

- 保存先: `data/finance_analyzer/discussions/YYYYMMDD_タイトル.md`
- git除外済みのため、会社の機密情報を含んでよい
- ユーザーから「議事録を保存して」と言われたとき、または重要な意思決定が行われたセッションの終わりに保存する
- 記載内容: 日時・議論の背景・判断の根拠・確定した数値・今後のアクション

---

## 連携スキル

- **freee_auditor**: データ品質に問題がある場合はこちらで修正する
- **kpi_monitor**: 年次のSheetsダッシュボードが必要な場合は引き続き利用可能（非推奨）
