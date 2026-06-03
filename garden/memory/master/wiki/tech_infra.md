---
scope: master
layer: wiki
topic: tech_infra
created: 2026-06-02
last_updated: 2026-06-03
last_updated_by: mycelium (Mode 1 ingest-raw, 2026-06-03)
---

# tech_infra — Garden / VPS / インフラ

Discord master scope の対話から抽出した、Garden システム・技術基盤に関する **判断・評価・意図** を時系列で記録する。

---

### 2026-05-31 - ガクコの実行スタックと自己認識

ガクコ自身が自己のアーキテクチャを説明した。

- 実行基盤: Anthropic の Claude Agent SDK
- ペルソナ・業務レイヤー: 起動時に CHARTER(Garden 全体の業務観・トーン規範) と daily-pilot SKILL(タスク・スケジュール管理の手順)を両方ロードして判断の軸とする
- 現在の立ち位置: Discord master channel 経由で動作しているが、実体は Claude Code セッション。常駐サービス bot.py とは別の経路
- 自己評価: 骨格は見えているが、正確な自己認識には限界があることを自覚している(過信しない)

ガクチョは「素晴らしい理解！」と肯定した(S31 11:38)。

---

### 2026-06-02 - morning-briefing active 仕様(フィルタなし)に関する認識

ガクチョが「今日の active に 6/3 以降の締め切りタスクが表示されている」と問い合わせ(09:09)。ガクコが仕様説明: morning-briefing Mode 1 Step 3 は backlog をそのまま active にコピーするため、今日締切以外のタスクも転写される(意図的仕様)。

ガクコから改善案を提示: 「今日〜◯日以内のタスクだけ active に載せるフィルタを追加」。ガクチョの採否は未確定(続報待ち)。

---

### 2026-06-02 - shift_manager S27 ダミーテスト 承認動線確認

shift_manager/monthly-shift-survey の承認動線確認用ダミーテスト(S27)が完了。

- board: `2026-06-02-dummy-test-s27.md`
- 種: `shift_manager/monthly-shift-survey`
- 対象月: 2099-12(遠未来・実配信なし)
- ガクチョが「承認します」と Discord 指示 → ガクコが status を `pending` → `approved` に変更(20:55)
- 承認後 `board/processed/` への移動が次の tick で確認できれば完了

Discord の自然言語指示だけで board の status 変更が完結する承認動線が正常に機能することを確認。
