# 2026-05-28 ADR — gaku-co を Garden の対話層(interaction layer)として統合し、内側/外側でデプロイ分離する

- **日付**: 2026-05-28
- **記録**: セッション15(continued)
- **決定者**: 塚越さん(庭師) / Claude
- **ステータス**: Accepted + 実装。**セッション16(2026-05-28)で段1-3 稼働** = 夜のレポート(cron 22:40)+ 喋るガクコ(Discord 常駐・オンライン・read-only)。詳細は [garden-gaku-co/README.md](../../garden/services/garden-gaku-co/README.md) / [session16](../sessions/2026-05-28-session16.md)

## 背景

セッション15 で daily-pilot 3 本を active 化し、cron → 種 → VPS MD → CouchDB → Obsidian の循環が無人で回るようになった。しかし塚越さんが「**hmc_pilot にあった秘書との対話(朝ブリーフィングで対話して整理される / 夜にねぎらいの一言)が、自律化の過程で失われた**」と気づいた。

種(claude -p)は**孤独なファイル操作**用で、対話・記憶・グループでの作法を持たない。一方 gaku-co5.0 は LINE/Discord 対応の**会話エージェント**で、2段階発言(Haiku 判定 → Sonnet 応答)・3層記憶(LLM wiki 方式)・チャネル別ペルソナ・承認ゲート・情報境界ルールを既に備える。

塚越さんの整理:「gaku-co の LLM-wiki も知識蓄積のため。3層記憶・2段階反応は**複数メンバーのグループでの反応をスムーズにするため**。gaku-co は **Garden の前段階の設計**と捉えていた」。よって両者を**思想として統合する**ことに躊躇はない。

## 決定

### 決定 1: 役割分担 — gaku-co = 接客(interaction)、Garden = 奥座敷(cultivation)

ひとつの LLM-wiki 生命体の二器官として位置づける:

| 器官 | 役割 | 記憶 |
|---|---|---|
| **Garden(種 / soil / launcher)** | 自律的な耕作・準備(prep)+ ドメインの真実 | soil(ドメイン知識)+ task MD(状態) |
| **gaku-co(対話層)** | 人・グループとの対話 + 配信 + 承認 + 情報境界 | 会話記憶(チャネル別、RAW+WIKI) |

種は「準備」に専念(現状のまま)。gaku-co が「対話と配信」を担う。

### 決定 2: split-brain は「真実の一元化」で回避

脳が2つ(gaku-co の API Sonnet / Garden の claude -p)あっても、次の規律で矛盾しない:

> **ドメインの真実は Garden の MD ただ一箇所**。gaku-co は会話/社会的記憶を持ち、Garden はドメイン記憶(soil)を持つ。両方の脳が**同じ MD を読み書きする**。

橋はすでに存在する:**mirror-daemon + writeback-daemon(S14/S15)** が VPS 上 `/home/vps-harappa/garden-mirror/` に平文 MD を用意済み。gaku-co がこの MD(`hmc_tasks/` `garden/board/` 等)を読み書きするだけで Garden の真実に参加でき、書いた変更は writeback-daemon → CouchDB → Obsidian に伝播する。**新しいトランスポートは不要**。

### 決定 3: 頭脳はチャネル単位で選ぶ

| チャネル | 頭脳 | 理由 |
|---|---|---|
| 塚越さん(Discord master、1-to-1・低頻度) | **claude -p(サブスク・Garden ツール込み)** | 個人インタラクティブ用途に合致。秘書は思考の質>反射速度。Garden ツールをネイティブに持てる。コストはサブスク定額 |
| チーム(LINE staff / core_team、多人数) | **gaku-co API(Haiku ゲート + 承認 + 情報境界)** | グループ作法(いつ黙るか)・承認・財務情報境界が必須。Haiku ゲートで安価 |
| 社外(Digital 原っぱ / AIBOU LAB) | **隔離 gaku-co API** | 決定 4 |

**コスト懸念への回答**: gaku-co は Stage1(Haiku で発話判定)で「喋る時だけ Sonnet 課金」のため元来安い。塚越さん個人の秘書対話は低頻度なので API でも費用は小さいが、サブスク claude -p に載せれば定額で Garden ネイティブ。**同時セッション制限**(既知の宿題)にぶつかったら API key にフォールバック。

### 決定 4: 信頼境界で「内側 / 外側」をデプロイ分離(エアギャップ)

本当の境界線は「gaku-co か Garden か」ではなく **内側(Garden に繋がる)vs 外側(隔離すべき)**:

```
内側(garden-gaku-co)= 塚越さん(Discord master)+ チーム(LINE staff/core)
外側(社外ガクコ)    = Digital 原っぱ大学(Discord)+ AIBOU LAB(LINE)
```

外側は**社外メンバーとの対話**。プロンプトインジェクション等で Garden のツール/記憶に届く事故を構造的にゼロにするため、**プロセス内のチャネル別分離では不十分**。**Garden の mount も credential も持たない別デプロイ**にして、届く先そのものを存在させない。

- **garden-gaku-co**(内側): Garden と自由に統合・garden-mirror 読み書き OK。将来 merge も安全
- **社外ガクコ**(外側): Garden の記憶/ツールを**一切流さない**。federate もしない

### 決定 5: garden-gaku-co は本 repo `garden/services/` に新設、Claude がデプロイ

- **配置**: `harappa-garden/garden/services/garden-gaku-co/`(mirror/writeback/launcher と同列)
- **git**: 本 repo で一元管理(種・soil・他 daemon と同じ履歴)
- **デプロイ**: dev-flow 系統(b)= Claude が `scp/rsync` → `ssh harappa` → `docker compose up -d --build`。mirror/writeback で実証済みの手順
- **既存 gaku-co**(`/home/tukapontas/gaku-co5.0/`、別 repo・GitHub デプロイ)は無傷。これが将来「社外ガクコ」に痩せていく
- **secret**: `.env` は VPS 上のみ(chmod 600)。ローカルに値を置かない([docs/security/README.md](../security/README.md) 準拠)

### 決定 6: 作り方 = 最小ネイティブから育てる

gaku-co を丸ごと写経して刈り込むのではなく、**最小の Garden ネイティブ bot から始め、gaku-co の良い部分(3層記憶・2段階発言・承認ゲート)を必要な段で意図的に移植**する。

- step1: Discord master + claude -p 脳 + garden-mirror 読み書き、の最小形
- 以降: チーム channel を足す段で gaku-co の記憶・承認を取りに行く

理由: 「Garden の一部として最適化・チューニング」(塚越さんの狙い)に最も合う。全継承は gaku-co の構造に引っ張られる。

### 決定 7: master チャネル = Discord

| 観点 | Discord | LINE |
|---|---|---|
| proactive push | **無料・無制限** | クォータ→従量(自発通知は push 扱い) |
| 表示 | markdown/表/embed ネイティブ | プレーン寄り(Flex は重い) |
| 対話整理 | スレッド可 | 無し |
| master 既定 | gaku-co が既に Discord master を想定 | — |
| 遍在性 | △(塚越さんは常用) | ◎(唯一の LINE 優位) |

秘書は本質的に proactive なので、無料無制限 push + 表示の質 + スレッドで **Discord 採用**。

### 決定 8: 最初の挙動 = 夜の一言、移行は big-bang を避ける

- **最初の挙動**: night-review 種の成果を受けて、garden-gaku-co が **ねぎらいの一言を Discord master に push**(軽い・秘書の人格/トーンの初校もここで)
- **次**: 朝の本格対話(claude -p 秘書セッション + garden-mirror 読み + Discord 往復)
- **移行**: garden-gaku-co は最初 **master(Discord)のみ**。既存 gaku-co はチーム/社外を従来通り継続。その後チーム channel を順次移し、既存 gaku-co は社外専用へ。LINE 公式アカウント分割・Discord bot token 所有権の配線は移行の各段で対処(step1 のブロッカーではない)

## 影響

- **watcher daemon は本命から後退**: ライブ対話エージェントが MD を直接書くため、「Obsidian で board 編集 → watcher 検知 → resume」は副経路に。本線は garden-gaku-co ↔ garden-mirror の対話
- **剪定(承認)は gaku-co の `/pending` `/approve` `/reject` に乗る**: board ADR の承認境界を重複実装せず、既存の承認キューに board MD を結ぶ
- **記憶**: 当面 federate(gaku-co 会話記憶 / Garden soil)。merge は判断保留(社外分離が決まったことで内側の merge は将来安全)

## 未決事項

- 朝の深い対話を claude -p 単独で賄うか、gaku-co の記憶機構を移植してからにするか(step2 で判断)
- LINE 公式アカウントの内側/外側分割の具体(別 OA か、ルータか)
- Discord bot token の新規発行 vs 既存 gaku-co master bot の移管
- 二つの wiki の最終的な merge 方針

## 関連

- [garden-board-structure ADR](2026-05-27-garden-board-structure.md) — 剪定/Triage の board 構造(承認は gaku-co に委譲)
- [writeback-daemon ADR](2026-05-27-writeback-daemon-implementation.md) — gaku-co ↔ Garden の共有 substrate
- [mirror-daemon ADR](2026-05-27-mirror-daemon-implementation.md)
- [daily-workflow ADR](2026-05-25-daily-workflow-and-task-master-architecture.md) — Triage ハイブリッドの源流
- gaku-co5.0 `README.md`(チャネル構成・2段階発言・3層記憶)/ `INTERFACE.md`(承認・情報境界)
- [hmc_pilot SKILL](../../.agent/skills/hmc_pilot/SKILL.md) — 失われた「秘書との対話」の原型
