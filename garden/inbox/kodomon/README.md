# コドモン勤怠 CSV 受け皿(Garden inbox)

ガクチョが月末/翌月初に **コドモンから職員入退室エクスポート CSV** をダウンロードして配置する場所。

## 命名規約

`{YYYY-MM}.csv`(対象月、例: `2026-05.csv`)

## エンコーディング

Shift-JIS(コドモン書き出し既定)。`import_kodomon.py` が自動判定して読み込む。

## 取り込みフロー

1. ガクチョが 月末日 or 翌日朝 にコドモンからエクスポート
2. このディレクトリに `{YYYY-MM}.csv` として配置
3. 月末 prep 種の「集計実行」承認後、`run_month_end_collect.sh` が自動で:
   - generate_working_hours.py で稼働シートタブ生成
   - **CSV があればそのまま import_kodomon.py で放サボ列に反映**

## VPS 上の実体

`/home/vps-harappa/garden-mirror/garden/inbox/kodomon/{YYYY-MM}.csv`

LiveSync 経由で本 repo の `garden/inbox/kodomon/` にもミラーされるが、CSV はそもそも .gitignore でコミット対象外(個人情報)。

## .gitignore

`*.csv`(個人情報の含まれる勤怠データを git に乗せない)

