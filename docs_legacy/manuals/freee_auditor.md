# Freee Auditor - ユーザーマニュアル

**Freee Auditor** は、freeeに登録された取引データを監査し、**部門（セクション）が設定されていない取引を発見・一括修正**するアプリケーションです。

会計データの精度を維持するための「経理品質チェック」として機能します。
AIエージェントが各取引の勘定科目・摘要から適切な部門を推論し、人間が確認・承認してからfreeeを更新します。

---

## 主な機能

- **スキャン (Scan):** 指定期間内の取引を取得し、部門が未設定の明細をCSVに一覧出力します。
- **AI部門提案:** スキャン結果をもとにAIエージェントが勘定科目・摘要・金額から適切な部門を推論し、提案します。
- **Human-in-the-Loop:** 提案内容を人間が確認・修正してから承認する安全なフローです。
- **一括適用 (Apply):** 承認済みのCSVをfreeeに一括反映します。Dry Runで事前確認も可能です。

---

## 利用方法（AIエージェント / Skill）

AIエージェントに以下のように指示するだけで利用できます。

> 「部門の振り分け漏れを確認して」
> 「今年度の部門未設定を整理したい」
> 「3月〜3月の部門チェックをして」

エージェントが以下のフローを自動で進行します。

1. **スキャン実行** → 部門未設定の取引一覧をCSV出力
2. **部門提案** → AIが各取引に適切な部門を推論して提示
3. **確認** → 内容を確認し、修正があれば伝える
4. **承認後に反映** → 「適用して」と伝えると freeeを更新

---

## 利用方法（手動実行）

### ステップ1：スキャン

```bash
# 直近3ヶ月（デフォルト）
python3 apps/freee_auditor/auditor.py scan

# 期間指定
python3 apps/freee_auditor/auditor.py scan --start 2025-10-01 --end 2026-03-31
```

`data/freee_auditor/scan/audit_YYYYMMDD_HHMMSS.csv` が出力されます。

### ステップ2：CSVを編集

出力されたCSVを開き、`section_name` 列に部門名を入力します。

- `suggested_section` 列：AIが入力した提案値（参考）
- `section_name` 列：実際に適用する部門名（ここを編集）

部門名はスキャン実行時に表示される「利用可能な部門一覧」と完全一致させてください。

### ステップ3：Dry Run（テスト確認）

```bash
python3 apps/freee_auditor/auditor.py apply data/freee_auditor/scan/audit_xxx.csv --dry-run
```

更新予定の内容が表示されますが、freeeは変更されません。

### ステップ4：本番適用

```bash
python3 apps/freee_auditor/auditor.py apply data/freee_auditor/scan/audit_xxx.csv
```

成功した行はログに `✓` が表示されます。処理済みCSVは `data/freee_auditor/applied/` に自動アーカイブされます。

---

## ディレクトリ構成

| パス | 内容 |
|---|---|
| `data/freee_auditor/scan/` | スキャン結果CSV（未適用） |
| `data/freee_auditor/applied/` | 適用済みCSVのアーカイブ |

---

## 注意事項

- **部門変更は会計データを直接変更します。** 必ずDry Runで内容を確認してから本番実行してください。
- **部門名は完全一致が必要です。** 「逗子_共通」と「逗子共通」は別扱いになります。スキャン時に表示される部門一覧をコピーして使用することを推奨します。
- **`section_name` が空の行はスキップされます。** 判断がつかない行は空白のままにしておけば、その行はfreeeに反映されません。
- 適用後、freeeの帳票（部門別PL等）への反映はリアルタイムです。

## 連携スキル

- **finance_analyzer:** 部門修正後に `check` コマンドで品質確認を行うことを推奨します。
