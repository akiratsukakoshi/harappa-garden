# ADR: shift_manager 区画の Garden 化 + post_approval 経路の確立

- 日付: 2026-05-30(セッション21)
- 状態: Accepted
- 参加: ガクチョ(塚越暁)、Claude (Opus 4.7)

## 背景

S19 で daily-pilot SKILL(plots 第1号)を立ち上げ、S20 で全 plot 共通の CHARTER + 越境 picker(案 D)+ 菌糸 + 永続記憶 の周辺設計が固まった。直後の S21 で月末月初(5/31 〜 6/1)業務サイクルの **Garden 初運用** が控えており、shift_manager 区画(=plot 第2号)を一気通貫で実装する必要が生じた。

合わせて、これまで未実装だった「**board の `status: approved` を検知して LINE 配信や shell コマンドを発火する**」=post_approval 経路 も同時に立ち上げる必要があった。

## 決定

以下を確定する。

### 1. shift_manager の Garden 完結化(B 案)

HMC `apps/shift_manager/logic/` の **14 本のうち 2 本(`generate_shift_form.py` + `generate_working_hours.py`)を Garden に移植**。残り 12 本は HMC 残置(必要時に段階的判断)。

選択肢:
- A. VPS から HMC を wrapper で起動(コードは HMC のまま)
- **B. Garden 側に移植(採用)** — ガクチョ判断「A をやるなら HMC で手でやる」
- C. シンボリックリンク or submodule

採用理由:
- Garden が責任境界を持つ(コードは Garden、credentials は Garden secrets/)
- HMC 並行運用回避(OAuth race 防止)
- 中身は同じだが「Garden で動かす」がガクチョの意思

### 2. plots 第2号 SKILL.md(CHARTER 継承)

- [garden/plots/shift_manager/SKILL.md](../../garden/plots/shift_manager/SKILL.md)(321 行)
- CHARTER を継承(共通の業務観・呼称・トーン・Output Style 質感)
- Mode 1: Month-end Preparation / Mode 2: Month-start Survey / Mode 3: Month-start Confirmation / Mode 4: Month-day-10 Finalize
- frontmatter `topics:` で picker 用キーワード declare
- `requires_soil_index: true`(staff / business 参照)

### 3. post_approval 経路 = send_pending.py(C 案)

3 案から選定:
- A. 専用 daemon(systemd 管理、ほぼ即時)
- B. bot.py 統合(同一プロセス、ただし bot 落ちが SPOF)
- **C. cron 1 分毎(採用)** — シンプル、依存少、SPOF なし、遅延 ≤ 60 秒

ガクチョ判断:「月 1 回の配信に秒単位精度は不要、既存プロセスを汚さない方が良い」

実装: [garden/services/garden-gaku-co/send_pending.py](../../garden/services/garden-gaku-co/send_pending.py)
- cron `* * * * *` 起動
- `garden/board/pending/*.md` を scan
- `status: approved` を検知 → frontmatter `from_seed` でディスパッチ(LINE staff 配信 / shell 実行)
- `status: test` を検知 → personal LINE にテスト配信 → status を pending に戻す
- frontmatter `scheduled_send: YYYY-MM-DDTHH:MM+09:00` で配信時刻を時刻待機(未来なら静かに skip)

### 4. Mode 3 「稼働確認の見せ方」 = URL 方式

3 案から選定:
- (a) 個別テキスト要約(LINE 個人 ID 必要、準備重)
- (b) Google スプシ個人タブ + 本人だけ閲覧権限(メアド収集 + 権限管理、準備重)
- **(c) 現状継続(staff LINE 投稿)を Garden 化、ただしスクショではなく URL 投稿(採用)**

スクショ自動化を検討したが:
- LINE Bot API は **PDF (file) を直接送れない**(画像/動画/音声のみ)
- PDF → 画像化はフォント崩れ・改ページ・マルチページ問題で品質保証困難
- スプシ URL 共有は「過去月比較」「自分のタブ表示」など、むしろスクショより便利な側面あり

中長期で (a) 個別送信に進化検討(LINE 個人 ID 収集後)。

### 5. 配信タイミング = 19:00 統一

ガクチョの作業時間確保のため:
- cron 起草は 6/1 08:00(両方同時)
- 配信は `scheduled_send: 2026-06-01T19:00:00+09:00` を見て 19:00 発火
- monthly-shift-survey と monthly-working-hours-confirmation は **同時刻別メッセージ**(スタッフの認知負荷を下げる)

### 6. テスト配信機能 = status:test → personal LINE

- 庭師が `status: test` に変更 → 1 分以内に personal LINE に配信
- 配信後 status は **自動で pending に戻る**(同じ board でテスト→修正→テストの反復可)
- 本配信は別途 `status: approved` に変更

### 7. コドモン CSV 自動取込

- 受け皿パス: `garden-mirror/garden/inbox/kodomon/{YYYY-MM}.csv`
- エンコーディング: Shift-JIS(コドモン書き出し既定、フォールバック cp932 / utf-8)
- ガクチョが月末/翌月初に手動配置 → 月末 prep 種の集計実行(承認)で自動取込
- [import_kodomon.py](../../garden/services/shift-manager/import_kodomon.py) が DB_Master_Nicknames 経由で氏名照合 → working_hours sheet の `YYYY-MM_稼働時間` タブの放サボセルに業務時間(`HH:MM`)を batch_update
- [run_month_end_collect.sh](../../garden/services/shift-manager/run_month_end_collect.sh) が generate_working_hours.py + import_kodomon.py を順次実行(CSV なければ警告で続行)

## 影響

- HMC 依存の段階的撤廃が **可能と実証**(2 本だけ移植で済む。残り 12 本も同じパターンで Garden 化可能)
- post_approval 経路成立により、**他 plot でも「board approve → 自動発火」が再利用可能**(daily-pilot の board からも将来呼び出せる)
- コドモン CSV 自動取込で **ガクチョの月末手作業時間が放サボ手入力分削減**
- workflow が改善余地表通りに進化(Mode 3 「見せ方」候補(c) → URL 方式に磨き込み)

## 残課題(継続宿題)

- NPM 経由 `bot.harappa.monster/api/send` の認証(現状ノー認証 = staff LINE スパム経路懸念)
- Bot を LINE staff グループに招待しているかの確認(未招待だと staff 配信失敗)
- 6/1 19:00 の本配信成功確認(本 ADR の正しさの最終検証)
- Mode 4 monthly-shift-finalize(aggregate_responses.py 移植後)
- HMC 並行運用回避の徹底(OAuth race 防止)

## 関連

- セッション: [2026-05-30 セッション21](../sessions/2026-05-30-session21.md)
- 共通規範: [garden/CHARTER.md](../../garden/CHARTER.md)
- 業務正本: [garden/soil/workflows/monthly-cycle.md](../../garden/soil/workflows/monthly-cycle.md)
- 新規 SKILL: [garden/plots/shift_manager/SKILL.md](../../garden/plots/shift_manager/SKILL.md)
- 新規 service: [garden/services/shift-manager/](../../garden/services/shift-manager/)
- 新規 dispatcher: [garden/services/garden-gaku-co/send_pending.py](../../garden/services/garden-gaku-co/send_pending.py)
- ADR 前提: [skill-and-seed-separation(S19)](2026-05-30-skill-and-seed-separation.md) / [garden-charter(S20)](2026-05-30-garden-charter.md) / [mycelium-and-soil-reference(S20)](2026-05-30-mycelium-and-soil-reference.md)
