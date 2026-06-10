# App Definition: Freee Auditor

## 1. アプリ概要

**Freee Auditor** は、freeeに登録された取引データを監査し、部門（セクション）が未設定の明細を発見・一括修正するアプリケーションです。

会計データの精度維持を目的とした「経理品質管理」ツールとして機能し、AIによる部門推論とHuman-in-the-Loopの確認フローを組み合わせています。

---

## 2. 業務フロー (Workflow)

```
[scan]                   [human / AI]              [apply]
freee取引取得 → CSV出力 → 部門推論・確認・修正 → freee PUT更新 → アーカイブ
```

1. **Input (Freee):** freee API から指定期間の全取引を取得（ページネーション対応）
2. **Process:** 部門IDが未設定の明細を抽出し、中間CSVを出力
3. **AI推論:** エージェントが勘定科目・摘要・金額をもとに部門を推論し `suggested_section` に記入
4. **Human確認:** ユーザーが `section_name` 列を確認・修正して承認
5. **Output (Freee):** `PUT /api/1/deals/{id}` で取引の部門IDを更新

---

## 3. 実装要件

### 3.1 ディレクトリ構造

```text
apps/freee_auditor/
 └── auditor.py           # メイン処理 (scan / apply)

data/freee_auditor/       # Git管理外
 ├── scan/                # スキャン結果CSV（未適用）
 └── applied/             # 適用済みCSVアーカイブ

.agent/skills/freee_auditor/
 └── SKILL.md             # Agentスキル定義（日本語）
```

### 3.2 コマンド仕様

#### `scan`

| パラメータ | デフォルト | 説明 |
|---|---|---|
| `--start` | 3ヶ月前の月初 | 開始日 (YYYY-MM-DD) |
| `--end` | 本日 | 終了日 (YYYY-MM-DD) |

**処理フロー:**
1. `GET /api/1/sections` で部門一覧を取得
2. `GET /api/1/account_items` で勘定科目一覧を取得（ID→名称変換用）
3. `get_all_deals()` でページネーション付きで全取引を取得（100件/ページ）
4. `details[].section_id` が null / 未設定の明細を抽出
5. CSV出力: `data/freee_auditor/scan/audit_YYYYMMDD_HHMMSS.csv`

**CSV列定義:**

| 列名 | 型 | 内容 |
|---|---|---|
| deal_id | int | freee 取引ID |
| detail_id | int | freee 明細行ID |
| date | string | 取引日 (YYYY-MM-DD) |
| type | string | income / expense |
| partner | string | 取引先名 |
| account_item | string | 勘定科目名 |
| amount | int | 金額（円） |
| description | string | 摘要 |
| suggested_section | string | AI推論提案値（空欄、Agentが記入） |
| section_name | string | 適用する部門名（ユーザーが確認・記入） |

#### `apply`

| パラメータ | 必須 | 説明 |
|---|---|---|
| `csv_file` | ✓ | 適用するCSVファイルパス |
| `--dry-run` | - | テスト実行（freeeは更新しない） |

**処理フロー:**
1. `GET /api/1/sections` で部門名→IDマップを構築
2. CSVを読み込み、`section_name` が記入済みの行のみ処理
3. `update_deal_section(deal_id, detail_id, section_id)` を行単位で実行
4. 処理済みCSVを `data/freee_auditor/applied/applied_YYYYMMDD_HHMMSS.csv` にコピー

### 3.3 freee API 利用エンドポイント

| メソッド | エンドポイント | 用途 |
|---|---|---|
| GET | `/api/1/sections` | 部門一覧取得 |
| GET | `/api/1/account_items` | 勘定科目一覧取得 |
| GET | `/api/1/deals` | 取引一覧取得（ページネーション） |
| GET | `/api/1/deals/{id}` | 取引詳細取得（apply時） |
| PUT | `/api/1/deals/{id}` | 取引の部門更新 |

### 3.4 部門更新ロジック

`PUT /api/1/deals/{id}` は全フィールドを送信する必要があるため、更新フローは以下の通り：

```python
# 1. 対象取引を取得
deal = GET /api/1/deals/{id}

# 2. 対象 detail の section_id のみ変更
for detail in deal.details:
    if detail.id == target_detail_id:
        detail.section_id = new_section_id

# 3. 全フィールドで PUT
PUT /api/1/deals/{id} with full payload
```

---

## 4. 技術スタック

- **言語:** Python 3
- **会計:** Freee Accounting API - `modules.freee_client`（PUT/PATCHメソッド追加済み）
- **依存ライブラリ:** `requests`, `python-dotenv`（標準ライブラリのみ使用）

---

## 5. 制限事項・注意点

- **部門更新の非可逆性:** 部門変更は会計データを直接変更するため、Dry Runによる事前確認を推奨。
- **全フィールド送信:** freee の `PUT /deals/{id}` は部分更新非対応。取引の全明細を含めた完全なペイロードが必要。
- **ページネーション:** 取引件数が多い場合、`get_all_deals()` の実行に時間がかかる。デフォルトを3ヶ月に設定しているのはこのため。
- **部門名の完全一致:** `section_name` はfreeeの部門名と完全一致が必要。部分一致・曖昧検索は未対応。
