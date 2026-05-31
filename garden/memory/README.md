# garden/memory/ — 記憶層

Garden の対話記憶を保持する層。

設計: [docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md](../../docs/decisions/2026-05-31-memory-three-layer-and-soil-routing.md)

## 三層分離

| 層 | 入れる対象 | 分類軸 | 漏洩制御 |
|---|---|---|---|
| **RAW** | 対話の生ログ | scope(チャネル)軸 | scope 間で交わらない |
| **SOIL** | 「事実」だけ(`garden/soil/` 配下、本ディレクトリ外) | 意味(対象)軸 | master のみ完全読み取り、下位 scope は投影ビュー |
| **MEMORY WIKI** | 「判断・評価・意図」 | scope(チャネル)軸 | scope 間で交わらない |

本ディレクトリは **RAW + MEMORY WIKI**(scope 軸)を扱う。SOIL は `garden/soil/` 側。

## 配置

```
garden/memory/
  master/                       # Discord ガクチョ私用 scope
    raw/                        # 日次 MD、14 日保持(Stage B でバッチ削除)
      YYYY-MM-DD.md
    wiki/                       # 主題別章立て(Stage A.5 / B で書き込み開始)
    index.md                    # 主題一覧(Stage A.5 で生成)
  line_staff/                   # Stage D で稼働開始(LINE スタッフグループ)
    raw/
    wiki/
    index.md
  line_aibou_{group_id}/        # Stage D で稼働開始(個人別 LINE)
    raw/
    wiki/
    index.md
```

## Stage 段階(現在: Stage A)

| Stage | 内容 | ステータス |
|---|---|---|
| **A** | `master/raw/` で Discord 対話の RAW logging だけ開始 | 🌱 S22 着手 |
| **A.5** | 菌糸 Mode 1 Ingest 最小実装(RAW → soil + master memory wiki) | ⬜ S23 以降 |
| **B** | 夜間バッチ(EXTRACT + CONSOLIDATE)+ 14 日経過 RAW 削除 | ⬜ A.5 安定後 |
| **C** | bot 起動時に master index + 最近 RAW を context にロード | ⬜ B 後 |
| **D** | LINE 統合 + 下位 scope RAW + 投影ビュー + マスター透視権 | ⬜ チーム公開時 |

## 書き込み口

- **Stage A**: [garden/services/garden-gaku-co/memory_logger.py](../services/garden-gaku-co/memory_logger.py)
  - `bot.py` の on_message から `memory_logger.append_turn("master", ...)` で呼ばれる
- **Stage A.5 以降**: 菌糸が RAW を読み soil / wiki へ振り分ける

## 注意事項

- `master/raw/` の中身は **機密扱い**(Discord 対話の生ログ = ガクチョの判断ログ含む)
- git にコミットしない(`.gitignore` で `garden/memory/**/raw/*.md` を除外)
- 14 日経過は Stage B のバッチで削除する設計だが、Stage A 時点では蓄積し続ける(運用 1 週間程度なら問題なし)
