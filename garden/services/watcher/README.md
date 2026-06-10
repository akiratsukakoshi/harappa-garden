# 番人(Watcher)— cron 失敗の沈黙を破る監視エージェント

S39 新設(2026-06-10)。Garden 語彙「番人」の最小実装。
MAP のロードマップ「Phase 2: VPS 信頼性 watcher の設計」を前倒しで消化したもの。

## 何をするか

VPS の cron `*/10 * * * *` で起動し、2 つの監視を行って異常を **Discord master チャンネル**に通知する:

| 監視 | 検出するもの | 仕組み |
|---|---|---|
| **エラースキャン** | cron ジョブの実行時エラー(Traceback / ERROR / FAIL / Permission denied / exit code 非0) | `garden/log/*.log` の**前回スキャン以降の追記分だけ**を読む(オフセットを state に記録。同じエラーは一度しか通知されない) |
| **ハートビート** | cron 自体の沈黙(S36 型: 実行ビット剥がれ等で cron が静かに死ぬ) | `run-send-pending.sh`(毎分)/ `run-bot.sh`(2分毎)が起動の度に touch するマーカー `.heartbeat-*` の mtime を確認。15 分無更新で警報 |

## ファイル

- [`log_watcher.py`](log_watcher.py) — 本体(stdlib のみ、venv 不要)
- [`run-watcher.sh`](run-watcher.sh) — cron ラッパー(garden-gaku-co/.env から Discord 認証を共用)
- state: `/home/vps-harappa/garden/log/.watcher-state.json`(オフセット + 警報抑制記録)
- 自身のログ: `/home/vps-harappa/garden/log/watcher.log`(スキャン対象外 = 通知ループ防止)

## 設計上の割り切り

- **初見のログファイルは遡らない**(導入時・新サービス追加時の過去ログ洪水を防ぐ。基準点だけ記録)
- **ハートビート警報は 6 時間に 1 回に抑制**(夜中に同じ警報を 36 回受け取らない)
- **番人自身の死は検知できない**(watcher の cron 行が消えたら沈黙する)。
  → 対策は「朝ブリーフィングに watcher.log の最終実行時刻を載せる」が将来候補(苗床)
- エラーパターンの誤検知(ログ本文に "error" を含む正常行)はあり得る。ノイズが出たら
  `NEGATE_RE` に除外パターンを足す

## デプロイ

```bash
rsync -avh -e ssh garden/services/watcher/ harappa:/home/vps-harappa/garden/services/watcher/
ssh harappa "chmod +x /home/vps-harappa/garden/services/watcher/run-watcher.sh"
# cron(登録済み、vps/cron/crontab.snapshot 参照):
#   */10 * * * * /home/vps-harappa/garden/services/watcher/run-watcher.sh >> /home/vps-harappa/garden/log/watcher.log 2>&1
```

## 動作確認(導入時に実施済み)

```bash
# エラー検知 → Discord 通知(2026-06-10 GREEN)
ssh harappa 'echo "[selftest] ERROR: 番人テスト" >> /home/vps-harappa/garden/log/cron-launcher.log \
  && /home/vps-harappa/garden/services/watcher/run-watcher.sh'
# ハートビート: .heartbeat-send-pending / .heartbeat-bot-keepalive が毎分/2分毎に touch されること
ssh harappa 'ls -la /home/vps-harappa/garden/log/.heartbeat-*'
```

## 改善余地(Improvement Hints)

| 案 | 状態 |
|---|---|
| 朝ブリーフィングに「昨夜の番人サマリ(エラー n 件)」を統合 | 未検討 |
| launcher の on_failure 経路と連携(board/failed/ 隔離の自動通知) | 未検討 |
| 番人自身の死活を朝ブリーフィング側から監視(相互監視) | 未検討 |
