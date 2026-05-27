# 種スキーマ拡張 5 項目 — `channel: none` / `on_complete` / `trigger.exclude` / `trigger.debounce` / `{event.path}`

- **日付**: 2026-05-27(ADR 起草日)
- **決定日**: 2026-05-25(セッション8 で導入・暫定運用)
- **記録**: セッション8 で導入 → セッション13 で正式 ADR 化
- **決定者**: 塚越さん(庭師) / Claude
- **ステータス**: 合意・5 項目すべて draft 種に反映済 / [garden/seeds/README.md](../../garden/seeds/README.md) のスキーマ定義本体に組み込み済

## 背景

セッション7 ADR で種スキーマ草案(MD frontmatter 9 要素)を確定。セッション8 で daily-pilot 4 本の draft 起草中に、**草案が想定していなかった要件** が 5 つ表面化:

| # | 種 | 表面化した要件 |
|---|---|---|
| 1 | recurring-spawn / night-review / inbox-process | 自律完結種(剪定不要)を表現する手段がない。`pruning.channel` は line / board_with_notify / board の 3 値 |
| 2 | night-review | 剪定はないが「処理完了の報告」だけ送りたい(`post_approval` は剪定後の挙動で意味が違う) |
| 3 | inbox-process | event 種で `processed/**` を watch から除外したい |
| 4 | inbox-process | エディタ等が連続書き込み中の途中状態で発火するのを防ぎたい |
| 5 | inbox-process | watcher daemon がマッチしたファイルパスを prompt や computed_inputs に渡したい |

セッション8 では暫定で導入・運用しつつ、本 ADR で正式化する。

## 決定: 5 フィールドを正式採用

### 1. `pruning.channel: none`

**用途**: 自律完結種(剪定なし)を表現。

**スキーマ**:

```yaml
pruning:
  channel: none
  approver: null
  notify: null
```

**運用ルール**:

- `channel: none` の場合、`approver` と `notify` は **明示的に null** を書く(省略不可、誤読防止)
- これは **完全に剪定が発生しない種**。失敗時の `on_failure.fallback` は通常通り動く
- 完了報告を送りたい場合は別途 `on_complete` を使う(`pruning` と `on_complete` は責務が違う)

**該当種**: `daily-pilot/recurring-spawn` / `daily-pilot/night-review` / `daily-pilot/inbox-process`

### 2. `on_complete`(frontmatter top-level)

**用途**: 剪定なし(`channel: none`)で完了報告だけ送る種用。

**スキーマ**:

```yaml
on_complete:
  via: gaku-co
  endpoint: /send
  body:
    group: personal
    require_approval: false
    template_summary: |
      ✅ {seed-name} 完了
      処理件数: {count}
      詳細: {log_path}
```

**運用ルール**:

- 配置は frontmatter top-level(`post_approval` と同じレベル)
- `post_approval` との違い: `post_approval` は **剪定後の挙動**、`on_complete` は **剪定なし種の完了報告**。同一種で両方を持つことは原則ない
- 成功時のみ呼ぶ。失敗時は `on_failure.fallback` が担当

**該当種**: `daily-pilot/night-review`

### 3. `trigger.exclude`

**用途**: event 種の watch 対象から除外する glob。

**スキーマ**:

```yaml
trigger:
  type: event
  watch: garden/inbox/**/*.md
  exclude:
    - garden/inbox/processed/**
    - garden/inbox/.archive/**
```

**運用ルール**:

- `watch` と同じ glob 記法。複数指定可
- watcher daemon が watch にマッチ後、exclude にもマッチしたファイルは無視する
- 既定値なし(指定なければ exclude しない)

**該当種**: `daily-pilot/inbox-process`

### 4. `trigger.debounce`

**用途**: event 種で連続書き込み中の途中状態を避ける。

**スキーマ**:

```yaml
trigger:
  type: event
  watch: garden/inbox/**/*.md
  debounce: 10s    # 最終書き込みから 10 秒静止してから発火
```

**運用ルール**:

- 値は `Ns` / `Nm` 等の単位付き文字列。watcher daemon 側で解釈
- 同一ファイルへの連続イベントは debounce 内なら最新のものだけ保持
- 既定値なし(指定なければ即時発火)

**該当種**: `daily-pilot/inbox-process`

### 5. `{event.path}` 変数

**用途**: watcher daemon がマッチしたファイルパスを渡すための変数名。

**スキーマ**:

```yaml
execute:
  computed_inputs:
    target_file: "{event.path}"
  prompt: |
    対象ファイル: {event.path}
    内容を読んで …
```

**運用ルール**:

- 変数記法は `{event.path}`(中括弧 1 重)
- `computed_inputs` や `prompt` の中で参照可
- watcher daemon が発火時に絶対パスで置換
- 将来 `{event.mtime}` `{event.size}` 等を増やす余地あり(本 ADR ではパスのみ正式化)

**該当種**: `daily-pilot/inbox-process`

## トレードオフ

### 採用理由

- **5 項目とも実種の draft で必要性が顕在化** したため、机上設計ではなく実装要件起点
- いずれも **既存スキーマと衝突しない**(追加のみ、既存フィールドの挙動変更なし)
- `channel: none` + `on_complete` の組合せで「剪定なし種の完了報告」がきれいに表現できる

### 妥協点 / 留意点

- **`channel: none` 種が剪定を経ない自律実行になるため、誤動作時の影響が大きい**:
  - 対策: `on_failure.fallback` を必ず設定する規律(seeds/README.md に明記済)
  - 対策: 自律完結種の初期は **dry-run モード**(`OUTPUTS_DIR=/tmp` 等)で 1 週間運用してから本番化
- **`trigger.debounce` の実装が watcher daemon 仕様に縛られる**:
  - Phase 3a A-1 で watcher daemon を実装する際に、debounce 仕様(タイマー方式 / inotify CLOSE_WRITE 検出 等)を確定する
- **`{event.path}` の絶対パス前提**:
  - watcher daemon の `watch` 解決基準をどこに置くか(VPS の `/home/vps-harappa/garden-mirror/` 基準 を想定)、A-1 実装時に確定

## 既存スキーマとの統合

[garden/seeds/README.md](../../garden/seeds/README.md) のスキーマ定義(セッション7 草案)に対する追加・改訂:

| 項目 | 改訂内容 |
|---|---|
| `pruning.channel` | `line | board_with_notify | board | none` の 4 値に拡張 |
| `pruning.approver` / `pruning.notify` | `channel: none` なら **明示的に null** |
| `trigger.exclude` | event 種の任意フィールドとして追加 |
| `trigger.debounce` | event 種の任意フィールドとして追加 |
| `on_complete` | frontmatter top-level の任意フィールドとして追加(`post_approval` の下に並ぶ) |
| 変数 `{event.path}` | event 種で `computed_inputs` / `prompt` から参照可能 |

README.md は既に反映済(セッション8)。本 ADR で「暫定 → 正式」のステータス変更が成立。

## 適用範囲

### 即時適用(セッション8 で実施済)

- [garden/seeds/daily-pilot/recurring-spawn.md](../../garden/seeds/daily-pilot/recurring-spawn.md) — `channel: none`
- [garden/seeds/daily-pilot/morning-briefing.md](../../garden/seeds/daily-pilot/morning-briefing.md) — `channel: line`(従来)
- [garden/seeds/daily-pilot/night-review.md](../../garden/seeds/daily-pilot/night-review.md) — `channel: none` + `on_complete`
- [garden/seeds/daily-pilot/inbox-process.md](../../garden/seeds/daily-pilot/inbox-process.md) — `channel: none` + `trigger.exclude` + `trigger.debounce` + `{event.path}`
- [garden/seeds/README.md](../../garden/seeds/README.md) — スキーマ定義に統合
- [garden/MAP.md](../../garden/MAP.md) — 決定索引に追記

### 本 ADR 化に伴う追記(セッション13)

- 5 項目を「暫定」から「正式」へ昇格
- seeds/README.md の「スキーマ拡張メモ」表は **正式スキーマに統合済** のため、表自体は ADR 完了後に削除可(本 ADR への参照リンク化)
- ADR 索引(MAP.md)に正式リンクを追記

### Phase 3a A-1 で具体化する事項

- `trigger.debounce` の watcher daemon 側実装(タイマー / inotify CLOSE_WRITE)
- `{event.path}` の解決基準パス
- `channel: none` 種の初期 dry-run 運用手順
- `on_complete` 配信失敗時の挙動(`on_failure` に倒すか別経路か)

## 未決事項(別議論)

- watcher daemon の実装方式(inotify / fsnotify / polling)
- `{event.*}` 系変数の今後の拡張(mtime / size / event_type)
- `pruning.channel: none` 種の **承認境界**(Phase 2 — 「自律実行 vs 剪定の境界文書化」と接続)

## 既存決定との関係

- **依存**:
  - [セッション4 ADR](2026-05-23-seeds-design-direction.md) — 剪定 3 チャネル(line / board_with_notify / board)
  - [セッション7 ADR](2026-05-25-seed-schema-and-execution-host.md) — スキーマ草案 9 要素
- **拡張**:
  - `channel` に `none` を追加(4 値化)
  - frontmatter に `on_complete` 追加
  - `trigger` に `exclude` / `debounce` 追加
  - 変数規約に `{event.path}` 追加
- **影響**:
  - daily-pilot 全 4 本の draft が本 ADR 準拠で確定
  - 案 E ([recurring-respawn-prevention ADR](2026-05-27-recurring-respawn-prevention.md)) と合わせて、Phase 3a A-1 の実装条件が揃う

## 関連

- [セッション8 サマリ](../sessions/2026-05-25-session8.md)
- [recurring-respawn-prevention ADR](2026-05-27-recurring-respawn-prevention.md)
- [セッション4 ADR(剪定振り分け)](2026-05-23-seeds-design-direction.md)
- [セッション7 ADR(スキーマ草案)](2026-05-25-seed-schema-and-execution-host.md)
- [garden/seeds/README.md](../../garden/seeds/README.md)
- [garden/seeds/daily-pilot/](../../garden/seeds/daily-pilot/)
