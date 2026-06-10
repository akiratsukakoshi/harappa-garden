# garden launcher — Phase 3a A-1 本番ランチャー

> セッション13(2026-05-27)初版。`.scratch/run-test-seed.sh`(セッション9)を育てた本番品質ランチャー。

## 用途

cron から呼ばれ、指定された **cron 種** を 1 回実行する。

```
node launcher.mjs --seed daily-pilot/morning-briefing
```

## 実装範囲(本版)

| # | 機能 | 状態 |
|---|---|---|
| 1 | frontmatter パース(YAML 最小実装) | ✅ |
| 2 | trigger 検証(cron 種のみ受け付ける) | ✅ |
| 3 | computed_inputs 評価(シェル展開 `$(...)`)| ✅ |
| 4 | prompt 変数置換(`{key}` / `{nested.path}`) | ✅ |
| 5 | `claude -p` 起動 + ログ書き込み | ✅ |
| 6 | 並行制御(lockfile)| ✅ |
| 7 | 状態永続化(state.json: last_fired / last_outcome) | ✅ |
| 8 | dry-run モード | ✅ |

## 実装範囲外(後追い)

| # | 機能 | 配置 |
|---|---|---|
| - | on_failure.retry の自動化 | 当面 cron 冗長化 or 別実装で対応 |
| - | on_failure.fallback の LINE 通知発火 | gaku-co5.0 `/send` 連携が要る |
| - | audit の種ファイル書き戻し | state.json 分離(本版で代替) |
| - | event 種(`trigger.type: event`)| watcher daemon が別途必要 |
| - | board 書き戻し経路(承認後の処理)| mirror-daemon 双方向化 or 別経路 |

## 設定(環境変数)

| 変数 | 既定値 | 用途 |
|---|---|---|
| `GARDEN_SEEDS_ROOT` | `../../seeds`(launcher.mjs から相対) | 種ファイル群のルート |
| `GARDEN_LOG_ROOT` | `/home/vps-harappa/garden/log` | ログ出力先 |
| `GARDEN_STATE_FILE` | `<launcher dir>/state.json` | 状態永続化先 |
| `GARDEN_LOCK_DIR` | `/tmp` | lockfile 配置先 |
| `CLAUDE_BIN` | `~/.npm-global/bin/claude` | Claude Code バイナリ |
| `CLAUDE_TIMEOUT_MS` | `600000`(10 分) | claude -p のタイムアウト |

## VPS 配置

```
/home/vps-harappa/garden/services/launcher/
├── launcher.mjs          (本ファイル)
├── README.md
├── package.json
├── state.json            (ランタイム生成、git 管理外)
└── .gitignore
```

種ファイルは HMG repo にあるので、VPS に **同じ階層で配置** する:

```
/home/vps-harappa/garden/seeds/
├── README.md
├── daily-pilot/
│   ├── recurring-spawn.md
│   ├── morning-briefing.md
│   ├── night-review.md
│   └── inbox-process.md
└── shift_manager/
    └── monthly-shift-survey.md
```

(deploy 方式は scp / rsync。将来 git pull 等に切替可)

## cron 設定例(VPS)

```cron
# daily-pilot 4 本(セッション13 ADR 確定後の active 化候補)
25 6 * * *  cd /home/vps-harappa/garden/services/launcher && node launcher.mjs --seed daily-pilot/recurring-spawn
30 6 * * *  cd /home/vps-harappa/garden/services/launcher && node launcher.mjs --seed daily-pilot/morning-briefing
30 22 * * * cd /home/vps-harappa/garden/services/launcher && node launcher.mjs --seed daily-pilot/night-review
```

`inbox-process`(event 種)は本ランチャーの対象外。watcher daemon が別途必要。

## 動作モード

### 通常実行

```
node launcher.mjs --seed daily-pilot/morning-briefing
```

→ ログを `$GARDEN_LOG_ROOT/{today}-morning-briefing.log` に書く。

### dry-run

```
node launcher.mjs --seed daily-pilot/morning-briefing --dry-run
```

→ frontmatter パース + 変数評価 + prompt 構築までを実行。`claude -p` は呼ばずログに `[dry-run]` を記録。

### unit test(S40 新設)

```
npm test
```

→ [test/launcher.test.mjs](test/launcher.test.mjs)。launcher.mjs 本体は無改修のまま、
サブプロセス起動 + env 差し替え(`GARDEN_SEEDS_ROOT` 等を tmpdir に向ける)+ `--dry-run` で
YAML パース / computed_inputs / {var} 置換 / lock / state / 終了コードを検証する 12 ケース。
最後のケースは **repo の実運用種 3 本を dry-run** して frontmatter の退行を検査する。
VPS には `test/` を rsync しない(launcher.mjs 単体で動く構造は不変)。

## 終了コード

| code | 意味 |
|---|---|
| `0` | 正常完了 |
| `1` | 内部エラー |
| `2` | 引数 / 種ファイル不正 |
| `3` | 並行起動中(ロック取得失敗) |
| `4` | working_dir 不在 |
| `その他` | claude -p の exit code そのまま |

## state.json 構造

```json
{
  "seeds": {
    "daily-pilot/morning-briefing": {
      "last_fired": "2026-06-01T06:30:01+09:00",
      "last_outcome": "success",
      "last_log": "/home/vps-harappa/garden/log/2026-06-01-morning-briefing.log"
    }
  }
}
```

last_outcome の値:

| 値 | 意味 |
|---|---|
| `success` | claude -p が exit 0 |
| `failed` | claude -p が非 0 |
| `error` | ランチャー内エラー |
| `dry_run` | dry-run 実行 |

## 既知の制約

- **本ランチャーは依存なし**(`js-yaml` 等の npm パッケージを使わない自前 YAML パーサ)
  - セッション13 初版で「最小依存」を優先したため
  - 種ファイルの YAML 形式に **インデント 2 空白** + **ブロックスカラー `|`** のみサポート
  - 種ファイルが複雑化したら `js-yaml` 等に切り替え予定
- on_failure.retry は **未実装**。cron の二重化(同じ種を 2 回スケジュール)で代替する想定
- LINE 通知はランチャー外(gaku-co5.0 `/send` 経由は別途)

## 関連

- [seed-schema-extensions ADR](../../../docs/decisions/2026-05-27-seed-schema-extensions.md) — 種スキーマ
- [vault-folder-layout ADR](../../../docs/decisions/2026-05-27-vault-folder-layout.md) — vault 配置
- [garden-board-structure ADR](../../../docs/decisions/2026-05-27-garden-board-structure.md) — board の I/O 構造
- [recurring-respawn-prevention ADR](../../../docs/decisions/2026-05-27-recurring-respawn-prevention.md) — 案 E
- [garden/seeds/README.md](../../seeds/README.md) — 種運用ルール
- [garden/seeds/.scratch/run-test-seed.sh](../../seeds/.scratch/run-test-seed.sh) — 試作版(セッション9)
