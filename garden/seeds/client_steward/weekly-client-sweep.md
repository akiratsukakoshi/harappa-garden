---
type: seed
name: weekly-client-sweep
plot: client_steward
description: 毎週月曜朝、active クライアントの soil 台帳を Gmail(primary_domain)の差分で世話する種(client_steward Mode S)。新着スレッド・要フォロー(こちらが返す番/放置日数)・finance シグナル(見積/請求/入金)・登場担当者を digest にして Discord master へ。解釈(確度変更・新規案件・freee反映の断定)は board 提案。手動「クライアント見て」でも回る。
status: test                     # S49: VPS デプロイ + cron 登録済(月08:20)。dry-run GREEN(MTI、VPS実走)。active = 初回発火 6/22(月)08:20 見届け後
phase: 1
execution_host: vps
hmc_dependency: none
version: 1
created: 2026-06-17
created_by: claude (with ガクチョ, セッション48)
last_updated: 2026-06-17
linked_skills:
  - "garden/plots/client_steward/SKILL.md"   # Mode S
linked_services:
  - "garden/services/client-steward/sweep_client.py"
linked_concepts: []

# === ① いつ点火するか ===
trigger:
  type: cron
  schedule: "20 8 * * 1"         # 毎週月曜 08:20 JST(朝ブリーフィングの後)
  timezone: Asia/Tokyo
  # 手動起動: ガクチョが Discord master で「クライアント見て」「MTI どうなってる」→ ガクコが Mode S/対話を実行

# === ② 何を実行するか ===
engine: claude-code
execute:
  working_dir: /home/vps-harappa/garden/services/client-steward
  timeout_minutes: 15
  computed_inputs:
    today: "$(date +%Y-%m-%d)"
  prompt: |
    あなたは client_steward 区画の種「weekly-client-sweep」です。active クライアントの
    soil 台帳が放置で陳腐化しないよう、Gmail の差分を世話する週次の世話役です。

    まず以下を Read し、指示に従ってください:
      1. /home/vps-harappa/garden/CHARTER.md
      2. /home/vps-harappa/garden/plots/client_steward/SKILL.md(Mode S / 承認境界 / 機密の作法)

    今回の動的入力:
      - today: {today}

    ⚠️ コマンドは絶対パス + cd なし:
      PY=/home/vps-harappa/garden/services/client-steward/.venv/bin/python
      SWEEP=/home/vps-harappa/garden/services/client-steward/sweep_client.py

    Step 1 sweep(全 active client の差分 digest):
      {PY} {SWEEP} --commit-watermark
      → 各クライアントの digest(要フォロー / finance シグナル / 動いたスレッド / 登場担当者)を得る。

    Step 2 剪定の振り分け(承認境界 = SKILL):
      - 生取り込み(新メールの要点)= そのまま digest に載せてよい。
      - 解釈(確度の変更・新規案件の確定・freee反映の断定・案件の統合)= soil に勝手に書かず、
        board(pending)に「{client} 案件更新の提案」として起草する。
      - 担当者の実名はメール署名のみ採用(Plaud 話者は採用しない)。新規担当者を見つけたら soil/people/clients の追加を board 提案。

    Step 3 通知:
      - digest を Discord master に投稿(変化なしのクライアントは1行 "動きなし" でよい)。
      - 要フォロー(こちらが返す番)と finance シグナル(請求→入金の突合要)は先頭に立てる。

    べき等性: 同日の processed/*-client-sweep.md が既存なら log に「skipped: already exists」を書いて exit 0。

    注意(既知の polish): 「ありがとうございました」等の儀礼的クロージングも「要返信」に出うる。
    明らかな締め挨拶は要フォローから外して判断すること(watermark 運用で古い儀礼メールは自然に落ちる)。
    Plaud(打合せ)差分は本 cron に含めない(MCP ブリッジは homework)。打合せは対話時にエージェントが引く。

# === ③ 失敗時 ===
on_failure:
  notify: discord
  note: token 失効(invoice_processor の user OAuth 流用)/ Gmail API quota / soil 読取失敗 を疑う。
---

# weekly-client-sweep(client_steward / クライアント世話役)

毎週月曜 08:20、VPS の launcher から発火する週次 sweep。詳細は [client_steward SKILL](../../plots/client_steward/SKILL.md)(Mode S)。

> ⚠️ frontmatter は必ず閉じ `---` で終える(launcher の extractFrontmatter が `\n---\n` を必須とするため。S54 で欠落を修正 = 初回発火クラッシュ防止)。
