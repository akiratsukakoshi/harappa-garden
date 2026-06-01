# board/failed/

種実行が `on_failure` 経路を通って起草された board(form URL 未取得など)、または手動退避した board の隔離先。

詳細は [board のライフサイクル拡張と承認依頼通知の経路(2026-06-01 ADR)](../../../docs/decisions/2026-06-01-board-lifecycle-and-notification.md) の **決定 1** を参照。

## 役割

- 種の `on_failure` 起草 board を **「実行はしたが配信不能」** として隔離
- べき等性ガードのグロブ(`pending/` `processed/` 直下のみ)から外し、種再キックで新規 board を起草可能にする
- 失敗の記録として **削除しない**(原因究明・運用改善のため残す)

## 命名規約

```
{元のファイル名}.FAILED.md
```

例: `2026-06-01-monthly-shift-survey.FAILED.md`

## 運用フロー

1. 種実行失敗 → 庭師判断(or Claude 補助)で `pending/{name}.md` を `failed/{name}.FAILED.md` に手動退避
2. 原因解消(コマンド許可追加・前段完了・URL 手動補完など)
3. 種を launcher で再キック → `pending/` に新規 board が起草される
4. 通常フロー(pending → approved → processed)再開

## 将来課題

- 種の `on_failure.move_to_failed: true` 宣言で自動退避できるようにする
- 月次で `failed/` を kura に退避する整理ポリシー
