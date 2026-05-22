# SNS Pilot - ユーザーマニュアル

**SNS Pilot** は、原っぱ大学のInstagram／Facebookアカウントへの週次投稿を支援するAIスキルです。
「ガクチョーが書いた生素材をAIが整形する」思想に基づき、投稿の声はあくまでガクチョー自身のものを保ちます。

---

## 投稿スケジュール（現行運用）

| 曜日 | 時刻 | 目的 | フォーマット |
|------|------|------|------------|
| 火曜日 | 20:00 | C: 思想共有 | フィード写真 |
| 木曜日 | 20:00 | B: 既存共感 | フィード写真 |
| 土曜日 | 08:00 | A: 新規獲得 | フィード写真 |

Reels（YouTube Shorts転用）は月1〜2回、月曜日に手動投稿。

---

## 週次ワークフロー（モード A）

### Step 1: 素材確認（AIが確認、ガクチョーが判断）

スキルを呼び出すと、AIが以下を確認します：
- `data/sns_pilot/images/candidates/` の候補画像
- 今週の投稿候補（曜日・目的・画像・ひとことコメント案）

ガクチョーが「この写真は木曜用、これは土曜用」と指示してください。
画像は `data/sns_pilot/images/selected/` に移動されます。

### Step 2: キャプション生成（AIが下書き、ガクチョーが加筆修正）

AIがガクチョー文体でキャプション＋ハッシュタグを下書きします。
ガクチョーが読んで、言い回しや追加コメントを加えてください。
修正後の文章をドラフトMDに反映します。

- **出力先:** `data/sns_pilot/drafts/YYYY-MM-DD.md`

### Step 3: Instagram・Facebook 自動スケジュール（AIが実行）

ドラフトMDの内容を確認後、以下を実行します：

```bash
python apps/sns_pilot/schedule_posts.py data/sns_pilot/drafts/YYYY-MM-DD.md
```

実行すると以下が自動登録されます：
- **Instagram**: Xserverクラウドのスケジューラーサーバーに予約ジョブを登録。指定時刻にサーバーが自動投稿。
- **Facebook**: Meta Graph API経由でスケジュール投稿を直接登録。

完了後にAIが以下のような確認結果を報告します：
```
✓ 火（04/29）フィード: IG job_id=12, 予定=2026-04-29 20:00 JST
✓ 木（05/01）フィード: IG job_id=13, 予定=2026-05-01 12:00 JST
✓ 土（05/03）フィード: IG job_id=14, 予定=2026-05-03 08:00 JST
```

---

## 週次レポート（モード B）

週の終わりに「今週のSNSレポート」と呼び出すと：
- 直近投稿のリーチ・保存・シェア数をMeta APIで取得
- Google Sheetsのログに記録
- 改善コメント付きのMDレポートを生成

**出力先:** `data/sns_pilot/reports/YYYY-MM-DD_weekly.md`

---

## ディレクトリ構成

```text
apps/sns_pilot/
├── meta_client.py       # Meta Graph API クライアント
├── schedule_posts.py    # FB投稿スケジューリングスクリプト
├── sheets_client.py     # Google Sheets KPIログ
├── weekly_report.py     # 週次レポート生成
├── drive_uploader.py    # （予備）Drive画像アップロード
└── config.json          # スプレッドシートID・投稿時刻設定

data/sns_pilot/
├── context/             # ガクチョー文体・思想の参照元
├── drafts/              # 週次ドラフト (YYYY-MM-DD.md)
├── images/
│   ├── candidates/      # [Input] 候補画像置き場
│   ├── selected/        # [Working] 今週採用画像
│   └── carry_over/      # [Stock] 次回繰り越し画像
└── reports/             # 週次KPIレポート

.agent/skills/sns_pilot/
├── SKILL.md             # スキル定義・ワークフロー
└── SNS_STRATEGY.md      # SNS戦略・KPI設計書
```

---

## 自動化の状況

| 機能 | 状態 |
|------|------|
| Instagramスケジュール投稿 | ✅ **サーバー経由で自動化済み**（2026-04-23〜） |
| Facebookスケジュール投稿 | ✅ Meta Graph API直接で自動化済み |
| Instagram即時投稿 | ✅ API対応可 |
| Instagramストーリーズ | ❌ APIスケジュール不可（イベント時のみ手動） |

**IGスケジューラーサーバーについて:**
- `https://ig-api.harappa.monster` で稼働中（Xserver VPS）
- 毎分チェックし、予定時刻になったら自動投稿
- 投稿失敗時は `tukapontas@gmail.com` にメールで通知

Facebookのスケジュール済み投稿は **Facebookページ → プロフェッショナルダッシュボード → スケジュール済みの投稿** で確認できます（Meta Business Suiteのカレンダーには表示されない場合があります）。

---

## 注意事項

- 画像ファイルは元のファイル名のまま `selected/` に入れてください（スクリプトがファイル名をMDから読み取ります）
- ドラフトMDの日付（04/23など）は**曜日と一致しているか**必ず確認してください
- `META_ACCESS_TOKEN` は有効期限があります。エラーが出た場合は `docs/sns_pilot_setup.md` を参照してトークンを更新してください
