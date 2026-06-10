# _archive/ — root 残置物の退避場所

HMC 時代の遺物のうち、**現役の参照が無い**ものを root から退避した場所(S39 レビュー指摘 → S40 実施)。
削除ではなく退避(git 履歴は `git mv` で連続)。中身は読み取り専用扱いで、編集・再利用しない。

| 元の場所 | 中身 | 退避理由 |
|---|---|---|
| `main_menu.py` | HMC の対話メニュー(finance_importer の CLI 起動) | Garden では種 + board 経由に置き換え済み |
| `clean.py` | generate_shift_form.py の debug print 除去ワンショット | 役目を終えた使い捨てスクリプト |
| `docs_legacy/` | HMC 時代のマニュアル・SNS 自動化調査メモ等 | 正本は `garden/soil/workflows/` と `docs/` に移行済み |
| `development/` | HMC→HMG 進化の初期議論メモ | 正本は `docs/origin.md` / `docs/concept.md` に継承済み |

なお `apps/` `modules/` は HMC 並行運用中のため対象外(S39 スコープ判断)。
