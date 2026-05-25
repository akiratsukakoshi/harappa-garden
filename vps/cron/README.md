---
type: reference
status: active
last_updated: 2026-05-26
purpose: VPS の vps-harappa user の crontab スナップショット
---

# cron スナップショット

VPS の `vps-harappa` user 上の crontab(`crontab -l`)の **正本**。

## 現状(@2026-05-26)

[crontab.snapshot](crontab.snapshot) 参照。

| 行 | 用途 |
|---|---|
| `*/15 * * * * find ... openclaw lock-cleaner` | openclaw のセッション lock を 15 分以上古ければ削除 |
| `0 19 * * * docker restart gaku-co-oc_openclaw-gateway_1` | 毎日 19:00 JST に openclaw gateway を再起動 |

Garden 用 cron は未追加(セッション9 で試作したのみ)。Phase 3a で daily-pilot 種を active 化する際に追加予定。

## 更新フロー

VPS で crontab を編集したら、必ず本ファイルを更新する。**VPS が正本ではなく、本 repo が正本**(理想)。

```bash
# VPS から最新を取得
ssh harappa "crontab -l" > vps/cron/crontab.snapshot

# 本 repo に commit
git add vps/cron/crontab.snapshot
git commit -m "vps/cron: snapshot at YYYY-MM-DD"
```

## 復元(VPS 全壊時)

```bash
scp vps/cron/crontab.snapshot harappa:/tmp/crontab.snapshot
ssh harappa "crontab /tmp/crontab.snapshot && crontab -l"
```

## 関連

- [vps/README.md](../README.md)
- [vps/recovery.md § cron 消失](../recovery.md#cron-消失)
