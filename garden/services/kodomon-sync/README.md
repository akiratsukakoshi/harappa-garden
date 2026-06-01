# kodomon-sync

WSL の repo に置かれたコドモン勤怠 CSV を VPS に同期するサービス(S24 新設、経路 α 暫定)。

## 役割

ガクチョの手元 → VPS への CSV 運搬路を作る。本格自動化は **γ(Discord アップロード経路)** で実装予定。

## 経路

```
[ガクチョ] コドモン Web 画面で CSV エクスポート
   ↓
[WSL] /home/tukapontas/harappa-garden/garden/inbox/kodomon/{任意ファイル名}.csv に保存
   ↓ ← この sync_to_vps.sh が拾う(WSL cron */5)
[VPS] /home/vps-harappa/garden-mirror/garden/inbox/kodomon/{同名}.csv
   ↓ ← run_month_end_collect.sh が import_kodomon.py を呼ぶ
[Google Sheets] worktime summary の 放サボ セルに業務時間反映
```

## ファイル名規約

import_kodomon.py 側で **柔軟化済み**(S24):
- `{YYYY-MM}.csv` 例: `2026-05.csv`
- `{YYYYMM}.csv` 例: `202605.csv`
- `*{YYYY-MM}*.csv` / `*{YYYYMM}*.csv` パターン
- フォルダ内に CSV が 1 件だけならそれを採用

→ コドモンのデフォルト名 `職員入退室エクスポート.csv` のままでも、月名を含めば OK。

## crontab 登録(初回設定)

```bash
crontab -e
# 以下を追加
*/5 * * * * /home/tukapontas/harappa-garden/garden/services/kodomon-sync/sync_to_vps.sh >> /tmp/kodomon-sync.log 2>&1
```

## 制約

- **WSL 起動中のみ動作**: PC がスリープ・WSL 停止中は同期されない。月初 cron(8:00)に間に合わせるため、前日中に WSL が起動していれば OK
- `--ignore-existing` 採用: 同名ファイルが VPS にあれば上書きしない(古い CSV の事故再配置防止)
- 上書きしたい場合は VPS 側を先に削除: `ssh harappa "rm /home/vps-harappa/garden-mirror/garden/inbox/kodomon/{name}.csv"`

## 将来(γ への移行)

Discord に CSV をドラッグ&ドロップ → bot.py が受け取って VPS に直接保存。WSL 依存を脱却。
