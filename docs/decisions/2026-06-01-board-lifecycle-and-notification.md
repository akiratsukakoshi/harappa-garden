# board のライフサイクル拡張と承認依頼通知の経路

- **日付**: 2026-06-01
- **記録**: セッション24
- **決定者**: ガクチョ(庭師) / Claude
- **ステータス**: 合意・実装完了(S24 で settings.json / send_pending.py / morning-briefing 種 / daily-pilot SKILL を改変)
- **前提**: [board の構造設計(2026-05-27)](2026-05-27-garden-board-structure.md)、[shift_manager Garden 化 + post_approval(2026-05-30)](2026-05-30-shift-manager-garden-and-post-approval.md)

## 背景

2026-06-01 19:00 の dummy 配信が走らなかったことが発覚した。原因は単発のバグではなく、 **board の運用設計に 3 つの構造的な穴** があったため:

### 穴 1: 種が python スクリプトを実行できない(claude -p の Bash 未許可)

S13 で `~/.claude/settings.json` を path-scoped allow で固めた際、 **`Bash` が allow に含まれていなかった**。S21 で導入された `shift_manager/monthly-shift-survey` 種は `generate_shift_form.py` を呼び出す前提だが、ヘッドレス claude -p のサンドボックスがブロック → board が `form_url: ERROR` のまま起草される失敗状態に。S21 から 6/1 までの 2 日間、月初配信は実質「手動補完」前提で潜在していた。

### 穴 2: 承認依頼通知がモック化されたまま放置

S21 で `==NOTIFY==` ブロック(ログに書き出すだけ)を「当面モック化」として導入したが、 **Discord master への実通知経路が実装されないまま** 6/1 を迎えた。`board/pending/` に起草された board の存在をガクチョが知る術がなかった(send_pending.py の dispatch 通知は `approved` 検知時のみ)。

### 穴 3: 連鎖 board の自動連結なし

`shift_manager/month-end-working-hours-prep` が approved されると `run_month_end_collect.sh` で稼働表が生成され、後段の `monthly-working-hours-confirmation` board の `blocked: true` を外す必要があるが、 **その連結が実装されていなかった**。結果、confirmation board は `blocked: true` のまま誰も触れず、5 月分の稼働確認配信が止まる構造だった。

### 既存 ADR との関係

[2026-05-27 garden-board-structure](2026-05-27-garden-board-structure.md) は **配置・命名・テンプレ・ライフサイクル・操作経路** を決めたが、上記 3 つは射程外だった。本 ADR は同 ADR を **追補・上書きする部分は明示** しつつ、運用フェーズで顕在化した穴をふさぐ。

## 決定

### 決定 1: `board/failed/` ディレクトリの新設(4 系統体制へ)

```
garden/board/
├── pending/      ← 剪定待ち
├── processed/    ← 完了(配信済み・却下済み)
├── triage/       ← Triage 系(質疑応答ベース)
└── failed/       ← (NEW)種実行失敗・形式不正・手動退避対象
```

**`failed/` の目的**:

- 種実行が `on_failure` ルートを通って起草された board(form URL 未取得など)を **「実行はしたが配信不能」** な状態として隔離
- べき等性ガードのグロブ(`pending/processed` 直下)から外して、 **次回の種発火が新規 board を起草できる状態に戻す**
- 失敗の記録として残す(削除しない)。命名: `{元のファイル名}.FAILED.md` で原型を保持

**ライフサイクル**:

```
[種が on_failure 経路で起草 / 庭師が手動で退避]
   ↓
[board/failed/{date}-{seed}.FAILED.md]   (常設、削除しない)
   ↓ 種再キック / 修正後の運用で次の board を pending に新規起草
   ↓
[元のフロー(pending → approved → processed)再開]
```

**前 ADR(2026-05-27 決定 2)からの差分**: 3 ディレクトリ → 4 ディレクトリ。`failed/` は新設、他 3 つの定義は不変。

### 決定 2: `status` 値の運用整理 + 補助 frontmatter フィールド

前 ADR(決定 4)で `status: awaiting_pruning | approved | rejected | sent | send_failed` と定義したが、実装は **`status: pending`** が事実上の `awaiting_pruning` として使われている。本 ADR で正式に **`pending` をデフォルト初期状態** として認める(`awaiting_pruning` は予約)。

加えて、運用上必要な補助フィールドを 2 つ正式採用する:

| field | 値 | 意味 |
|---|---|---|
| `status` | `pending` / `test` / `approved` / `rejected` | 庭師の判断状態。`test` は personal LINE テスト配信(配信後 `pending` に自動復帰) |
| `blocked` | `true` / `false`(or 未設定) | **(NEW)** 前段未完了などで庭師判断不能。`true` の間は通知されず、approve しても発火しない |
| `notified_at` | ISO8601 | **(NEW)** send_pending.py が初回承認依頼通知を投げた時刻。冪等化キー |
| `scheduled_send` | ISO8601 | 配信予定時刻(approved 後も時刻まで待機) |
| `blocked_reason` | string | `blocked: true` の理由(自由記述) |

**`blocked` を導入した理由**: 連鎖型 board(前段 approved → 後段 unblock)を扱うには、後段が「まだ判断できない」状態を明示する型が必要。`status: pending` のままだと「承認依頼が届く」UX に巻き込まれて庭師の認知負荷が増える。

### 決定 3: 承認依頼通知は `send_pending.py` の責務に追加(4 経路)

`send_pending.py`(cron `* * * * *` 起動)の責務を 3 つから 4 つに拡張:

| 検知パターン | 動作 | 冪等化 |
|---|---|---|
| **(既存)** `status: approved` + 配信時刻到達 | dispatch_line_send / dispatch_dummy / dispatch_shell → 成功で `processed/` 移動 | ファイル移動 |
| **(既存)** `status: test` | dispatch_line_send(personal LINE)→ `status: pending` に戻す | reset_test_status |
| **(NEW)** `status: pending` + `blocked: false` + `notified_at` 未設定 | Discord master に「📋 承認依頼が届いています」通知 → frontmatter に `notified_at` 追記 | `notified_at` の存在 |
| **(NEW)** dispatch_shell 成功時、from_seed が `month-end-working-hours-prep` | 同 `target_month` の `monthly-working-hours-confirmation` board の `blocked: true` を外し、`scheduled_send` を当日 19:00(過去なら 2 分後)に設定 | `blocked: false` の存在 |

**「(NEW)」 2 つは前 ADR の射程外**。前 ADR では「通知方法」を `pruning.channel: line / board_with_notify / board` と分類していたが、 **実装では「Discord master 一括通知 → 庭師が Obsidian で開く」が現実解** になった。LINE 通知は garden-gaku-co 統合後の再検討。

### 決定 4: 朝のブリーフィングに「承認待ち board」セクション統合

[2026-05-27 ADR](2026-05-27-garden-board-structure.md) で「ガクコ側の責任(LINE 返信 → board 書き戻し)」が触れられているが、 **「庭師がそもそも board の存在を見落とすケース」** はカバーされていなかった。Discord master の単発通知は埋もれやすい。

朝の Triage board の末尾に **「📋 承認待ち board(剪定依頼)」セクション** を追加する経路を正式採用:

1. `morning-briefing.md` 種の `computed_inputs.board_pending_block` で launcher が `pending/` を事前列挙
2. 種 prompt → SKILL Mode 1 **Step 1.5** に従って Triage board 末尾に整形
3. `blocked: true` は「⏳ 前段待ち(本日対応不要)」として分離
4. 口火(`morning_greet.py`)が active_tasks の Triage セクション要約で Discord master に短く触れる

**運用効果**:
- 初回通知を見落としても、翌朝の Triage で再提示される
- `blocked: true` は「庭師の認知から外して保留」できる(通知も再リマインドも飛ばない)
- 通知 → リマインド → 朝 Triage の 3 段で「気づかれずに残り続ける board」を構造的に防止

### 決定 5: 配信本文セクション抽出は **見出し部分一致 + `## 配信本文` 必須化**

S24 検証中、`monthly-shift-survey` board が `## 📋 配信本文（編集可）` のような **装飾付き見出し** を使っていて、`extract_send_body` の完全一致正規表現 `^##\s*配信本文\s*$` にマッチしなかった事故が発生。

**前 ADR(2026-05-27 決定 8)** で「値は **見出し文字列**(`## 配信本文` 等)」と定めていたが、実装と種テンプレが乖離していた。今回 2 つを揃える:

1. **`extract_send_body` を部分一致に緩和**: `^##\s.*配信本文.*$`(装飾絵文字・補足カッコを許容)
2. **すべての配信系種テンプレで `## 配信本文` セクションを必須化**:
   - `monthly-shift-survey`: 装飾付き見出しも OK だが、内部に `## 配信本文` を含む文字列が必須
   - `monthly-working-hours-confirmation`: blocked 時の警告は別セクション `## ⚠️ 配信保留中(前段未完了)` で並置 → `## 配信本文` セクションは **常に存在** させる(S24 で発覚した S21 設計バグの修正)
3. **`scheduled_send` 時刻が過去でも `extract_send_body` 失敗で `pending` 残置 → 庭師判断**(現状の挙動を維持、本 ADR では変更なし)

### 決定 6: 庭師アクションセクションの **統一テンプレ強制**(`status:` 変更案内)

S24 で「チェックボックスを `[x]` にすると発火」という誤誘導文言が `month-end-working-hours-prep` board に残っていた(S21 設計時の混乱)。 **`status: pending` → `approved` 書き換え以外では何も発火しない** ことを庭師に明示するため、配信系 3 種すべてに **統一テンプレの「庭師アクション」セクション** を強制:

```markdown
## 🌱 庭師アクション(承認 = 配信/集計の発火)

**frontmatter の `status:` フィールドを書き換えて保存** してください:

- `status: pending` → `status: test` に変更 → 保存
  → 約1分以内に ガクチョ個人 LINE にテスト配信(本配信前の確認用、何度でも可)
- `status: pending` → `status: approved` に変更 → 保存
  → scheduled_send の時刻に staff グループに本配信(dummy モード時は Discord master へ)
- `status: rejected` に変更 → 保存 → 配信せず却下

⚠️ チェックボックスは備忘録。発火条件は frontmatter の `status:` のみ。
```

- **チェックボックスの責務を明確化**: チェックリストは「庭師が自分の確認進捗を記録するための備忘録」。発火には一切寄与しない
- **`status: test` を明文化**: テスト配信機構は存在したが、board 文言で案内されておらず使われていなかった

### 決定 7: コドモン CSV 運搬路 = WSL cron rsync(α)を暫定採用、γ(Discord アップロード)を将来構想

S24 で `shift_manager/monthly-working-hours-confirmation` の dummy 配信を成立させた後、放サボ列が反映されていない問題が発覚。深掘りすると **複数の構造的問題が連鎖** していた:

**問題 1: generate_working_hours.py の「時間空 → スキップ」バグ**
- 放サボイベントは「カテゴリ = 放サボ / 稼働時間 = 空(CSV から取得予定)」で運用される設計
- しかし実装は `parse_hours("") → None → continue` で events から除外
- 結果、稼働表に放サボ列が一切生成されない = import_kodomon.py が書き込む対象セルがない

**問題 2: CSV 運搬路の設計欠落**
- import_kodomon.py は `VPS の garden-mirror/garden/inbox/kodomon/{月}.csv` を期待
- だがガクチョの手元(WSL/Dropbox)から VPS へ CSV を運ぶ経路が **未設計**
- vault に置いても LiveSync は MD のみ同期するので CSV は伝搬しない
- S21 で VPS 側にディレクトリを作っただけで「運搬路」を作っていなかった

**問題 3: ファイル名規約の固定化**
- import_kodomon.py が `{YYYY-MM}.csv` 完全一致を要求
- ガクチョが置いたのは `202605.csv`(ハイフンなし、コドモン由来の自然な命名)
- 形式違いで自動取り込みが空振り

**S24 の修正**:

| 修正 | 内容 |
|---|---|
| 放サボバグ修正 | `is_saboru` 判定を `parse_hours` 前に行い、放サボなら時間空でも events に追加(`hours_result = None / auto_hours = None`)。`generate_working_hours.py` 行 286-301 |
| ファイル名柔軟化 | `resolve_csv_path()` 関数追加: `{YYYY-MM}.csv` / `{YYYYMM}.csv` / `*{YM}*.csv` glob / フォルダ唯一の CSV の順で解決。`import_kodomon.py` |
| 運搬路 α 採用(暫定) | WSL crontab `*/5 * * * *` で `repo/garden/inbox/kodomon/*.csv` を VPS の `garden-mirror/garden/inbox/kodomon/` に rsync。`garden/services/kodomon-sync/sync_to_vps.sh` 新設 |

**運搬路の比較と選択**:

| 案 | ガクチョの作業 | 自動化度 | 実装コスト |
|---|---|---|---|
| α: WSL cron + rsync | repo/garden/inbox/kodomon/ に CSV 置く | 半自動(WSL 起動中のみ) | 低(本 ADR 採用) |
| β: Dropbox 経由 | Dropbox 専用フォルダに置く + WSL cron で rsync | α と同じ | α と同じ |
| γ: Discord アップロード | Discord に CSV をドラッグ&ドロップ | 完全自動 | 中(bot.py に新機能追加) |
| δ: コドモン API/MCP 直接 | 何もしない | 完全自動 | 高(API 鍵入手・実装) |

**α を選んだ理由**: 既存の repo 配置運用(ガクチョが既に CSV を置いた実績)に乗る最短経路。WSL 依存は許容範囲(月初・月末作業は PC 利用時間帯と一致)。γ への移行は MAP の宿題として保持。

**将来課題**:
- γ への移行(WSL 依存の脱却)
- δ への移行(完全無人化、コドモン側 API 確認次第)

### 決定 8: 種側の `on_failure` を「`failed/` 退避 + pending 新規起草を許す」運用に統一

前 ADR(決定 4 status 遷移表)では `send_failed` ステータスを定義していたが、実運用では:

- 配信前の失敗(フォーム生成失敗・前段未完了など)→ board が「壊れた pending」状態のまま `pending/` に残置 → べき等性ガードで再発火不能
- 配信後の失敗(LINE API エラーなど)→ `send_failed` で `pending/` 残置(これは前 ADR 通り)

**運用ルール**:

| 失敗種別 | 処置 | 理由 |
|---|---|---|
| 種実行時の前提失敗(`on_failure` ルート発火)| 庭師が `pending/` → `failed/{...}.FAILED.md` に手動退避 → 種を再キック | べき等性ガードを邪魔せず、次回発火で正常 board を再生成 |
| 配信時の失敗(`status: send_failed`)| `pending/` 残置のまま庭師判断(後追い対応) | 配信本文は揃っているので、原因解消後に再 approve で復帰 |

将来的に「種が自分で `failed/` に退避するか pending に残すか」を `on_failure.move_to_failed: true` のような種フィールドで宣言できるようにする検討余地あり(現状は手動)。

## トレードオフ

### 採用理由

- **4 ディレクトリ体制**: 失敗 board を pending から物理分離することで、べき等性ガード・庭師通知・朝 Triage のすべてがシンプルになる
- **`send_pending.py` への通知統合**: 既に cron 1 分毎で動いている既存プロセスに乗せる方が、別 watcher daemon を立てるより堅牢(障害点が増えない)
- **`blocked` 型の導入**: 連鎖 board を扱うのに「`status: pending` の意味が二重化する」のを避ける(`pending` = 判断可能 / `blocked: true` = まだ無理 が分離)
- **朝 Triage への統合**: 既存の daily-pilot Mode 1 にぶら下げる方が、別 SKILL を立てるよりトーンが揃う

### 妥協点

- **`failed/` の手動退避運用**: 当面は庭師判断(or Claude 補助)で退避。種が自動で `failed/` に行く仕組みは保留(`on_failure.move_to_failed` の宣言型導入は次フェーズ)
- **`status: send_failed` と `failed/` の使い分けの曖昧さ**: 「配信前失敗 = `failed/` 退避 / 配信時失敗 = `pending` 残置」のルールは運用で固める。明文化しないと混乱する可能性あり → 本 ADR で明示
- **通知の冪等化が ISO8601 文字列依存**: `notified_at` の有無で判定するため、frontmatter を手で消すと再通知される。これは仕様(意図的に「通知をやり直したい」場合の動線でもある)

## 未決事項

- **`board/triage/` 側にも notified_at / blocked を適用するか**(現状は剪定系 board のみ。Triage は別ライフサイクルなので必要性低)
- **`failed/` の月次整理ポリシー**(無制限に貯まる。kura への退避タイミングを定める必要あり)
- **配信時失敗(`send_failed`)時の自動リトライ規律**(現状は人手対応。`on_failure.retry` の自動化は Phase 3a 後追い宿題)
- **`blocked` の解除条件を frontmatter 上で宣言する型**(現状はコードに埋め込み。`unblock_when: {prev_seed: shift_manager/month-end-working-hours-prep, prev_target_month_eq: target_month}` のような宣言型に育てる余地)
- **LINE 通知への昇格タイミング**(現状は Discord master のみ。garden-gaku-co 統合 Stage 4 で LINE webhook 受信実装後に再検討)

## 実装メモ(本 ADR と同時に行われた変更)

| 変更 | 位置 |
|---|---|
| Bash 許可追加(shift-manager venv python) | VPS `~/.claude/settings.json` |
| `notify_pending` / `unblock_confirmation` 関数追加 + `process_one` 拡張 | `garden/services/garden-gaku-co/send_pending.py` |
| `extract_send_body` を部分一致に緩和 | `garden/services/garden-gaku-co/send_pending.py` |
| `computed_inputs.board_pending_block` + prompt 拡張 | `garden/seeds/daily-pilot/morning-briefing.md` |
| Mode 1 **Step 1.5** 追加 | `garden/plots/daily-pilot/SKILL.md` |
| 庭師アクション統一テンプレを 3 種に追加 | `garden/seeds/shift_manager/{month-end-working-hours-prep,monthly-shift-survey,monthly-working-hours-confirmation}.md` |
| confirmation の `## 配信本文` セクション必須化 | `garden/seeds/shift_manager/monthly-working-hours-confirmation.md` |
| prep のチェックリスト最終行を誤誘導文から備忘録文へ修正 | `garden/seeds/shift_manager/month-end-working-hours-prep.md` |
| 壊れた board の退避 | `garden/board/failed/2026-06-01-monthly-shift-survey.FAILED.md` |
| 4 ディレクトリ体制の確立 | VPS `/home/vps-harappa/garden-mirror/garden/board/failed/` 新設 |
| 放サボイベント「時間空 → スキップ」バグ修正 | `garden/services/shift-manager/generate_working_hours.py` 行 286-301 |
| ファイル名柔軟化(2026-05.csv / 202605.csv / glob) | `garden/services/shift-manager/import_kodomon.py` `resolve_csv_path()` 追加 |
| CSV 運搬路 α 実装(WSL cron rsync) | `garden/services/kodomon-sync/sync_to_vps.sh` + WSL crontab `*/5 * * * *` |
| 2026-05_稼働時間 タブの再生成 + 取り込み | バックアップ `2026-05_稼働時間_backup_S24` 残置、12 セル放サボ反映成功 |

## 関連

- [board の構造設計(前 ADR)](2026-05-27-garden-board-structure.md) — 本 ADR が追補する基底 ADR
- [shift_manager Garden 化 + post_approval](2026-05-30-shift-manager-garden-and-post-approval.md) — send_pending.py の出自
- [garden-gaku-co 統合方針](2026-05-31-garden-gaku-co-unification.md) — Discord master 通知の経路前提
- [seed-schema-extensions](2026-05-27-seed-schema-extensions.md) — `pruning.channel: none` 等の運用前提
- 実装: [garden/services/garden-gaku-co/send_pending.py](../../garden/services/garden-gaku-co/send_pending.py)
- 実装: [garden/seeds/daily-pilot/morning-briefing.md](../../garden/seeds/daily-pilot/morning-briefing.md)
- 実装: [garden/plots/daily-pilot/SKILL.md](../../garden/plots/daily-pilot/SKILL.md)
