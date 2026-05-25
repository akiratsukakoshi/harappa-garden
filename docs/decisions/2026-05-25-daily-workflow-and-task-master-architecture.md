# デイリーワークフローの種化とタスクマスタアーキテクチャ

- **日付**: 2026-05-25
- **記録**: セッション6
- **決定者**: 塚越さん (庭師) / Claude (壁打ち相手)
- **ステータス**: 設計合意・実装は Phase 3 で順次

## 背景

HMC の **デイリーワークフロー(朝ブリーフィング → タスク化 → 夜の振り返り)はコア機能だが workflows/ に未登録** だった。`hmc_pilot` SKILL に手順が定義されているのみで、Garden 化の方針も未策定。

塚越さんのペイン:
- 朝から移動だとブリーフィングできず、終日タスクが起動できない
- PC を開かないとタスクがアップデートされない
- マスタが WSL にあり、塚越さんの起動がないと止まる

つまり「塚越さんアクションが起点」の構造そのものがボトルネック。**種(cron)起点に転換し、塚越さんは判断・剪定のみに専念する** 形へ移行することがセッション6 の論点。

副次的に、この設計は **「タスクマスタをどこに置くか」「種の頭脳は何か」「Triage 対話はどう持つか」** という、Garden 全体に波及するアーキテクチャ判断を含む。

---

## 決定 1: タスクマスタの置き場 = (α) Obsidian LiveSync + VPS CouchDB

### 構造

```
[VPS]
  CouchDB (Docker, LiveSync DB)
       ▲
       │ _changes feed リスナ(常駐 daemon)
       ▼
  /opt/garden/tasks/*.md  ← 平文 MD ミラー(seeds はこれを読む)
       ▲
       │ Claude / 種が読み書き(→ CouchDB へ書き戻し)

[クライアント]
  Obsidian PC / iPhone — 両方 LiveSync プラグイン → CouchDB に直結
  → 数秒で push 同期(更新ボタン不要)
```

### 検討した候補と却下理由

| 候補 | 却下理由 |
|---|---|
| 現状(WSL master + Dropbox + Remotely Sync) | モバイルが pull モデルで「更新ボタン」が必要 → 塚越さんのペイン直結 |
| Dropbox 昇格のみ | 上と同じ。Obsidian Mobile の Dropbox 統合が push でない以上、ペインは残る |
| Obsidian Sync(公式・有料) | VPS から直接アクセス不可。月額 $10 |
| Git + Obsidian Git プラグイン | 数分のラグ。「数秒で同期」要件に未達 |
| Syncthing | iPhone 対応が弱い |
| Notion | 塚越さんが UI を好まない / ブロックエディタの異物感 / MD でなくなる |
| SilverBullet | 新エディタへの乗り換えコスト。Obsidian Mobile に既に習熟しているので不要 |

### VPS 信頼性への対処(Garden 共通課題)

VPS が時々停止する問題は本決定の前提課題として並走対応:

| 対策 | 内容 |
|---|---|
| Docker 自動復帰 | `restart: always` + systemd 監視 |
| Obsidian local-first 性質 | VPS が落ちても各端末は通常通り編集可、復帰時に自動同期 |
| CouchDB 日次バックアップ | `couchdb-backup` を cron で外部ストレージへ |
| 平文 MD ミラーの git 日次コミット | CouchDB 破損時の最終バックアップ |
| 死活監視 → LINE 通知 | gaku-co5.0 経由 |
| VPS 信頼性 watcher | Phase 2 の番人候補として MAP.md に登録 |

---

## 決定 2: backlog がマスタ、active_tasks は派生ビュー

### 原則

- **`backlog.md` = 唯一のマスタ**(recurring / inbox / 手動追加 すべての出自がここに合流)
- **`active_tasks.md` = 「今日」のビュー**(backlog から今日締切で抽出した派生物。マスタではない)
- **`archive.md` = 完了履歴**

### HMC からの変更点

HMC では Daily recurring は active_tasks に直行していたが、HMG では **すべての recurring が backlog 経由** に統一。Daily も backlog に「今日締切」で入り、morning-briefing が抽出する形。

理由: 出自ごとに分岐があると「埋もれ漏れ」が起きやすい。マスタを一本化することで、active に出てこないタスク=単に締切が未来というだけ、と単純化できる。

---

## 決定 3: 種の構成 = 4 本立て

セッション5 の「責務で分割(同タイミングでも分ける)」原則に従う:

| 種 ID | タイミング | 責務 | 触るもの |
|---|---|---|---|
| 🌱 `daily-pilot/recurring-spawn` | cron 毎日 06:25 | recurring_master を見て、当該期間のインスタンスが backlog に無ければ追加(べき等) | recurring_master(R), backlog(W) |
| 🌱 `daily-pilot/morning-briefing` | cron 毎日 06:30 | backlog から今日締切を active に抽出、calendar 取得、Triage、LINE 通知 | calendar(R), backlog(R), active(W), board(W), LINE(W) |
| 🌱 `daily-pilot/night-review` | cron 毎日 22:30 | active の [x]/[ ]/追加 を backlog/archive に反映、active クリア、LINE 通知 | active(R), backlog(W), archive(W), LINE(W) |
| 🌱 `daily-pilot/inbox-process` | event: `inbox/*.md` 投入時 | 振り分け → backlog 追記、ファイル `inbox/processed/` へ移動 | inbox(R/del), backlog(W) |

スケジュール: **平日・土日祝すべて同じ**。早朝移動日は固定時刻で諦め(将来カレンダー連動シフトも検討余地)。「明日の予報」付与なし。

---

## 決定 4: 種の頭脳 = Claude Code ヘッドレス起動(Garden 全体への適用)

これは Garden 全体のアーキテクチャ判断であり、デイリーワークフロー以外の全種・全watcher にも適用される。

### 採用方式

```
[VPS]
  cron 06:30 ──→ claude -p "Run morning-briefing seed"
                     │
                     │ (Claude Code が起動)
                     │
                     ├─ Reads:  backlog.md, calendar(MCP), recurring_master
                     ├─ Reasons: ばらつき耐性・Triage 候補抽出・カテゴリ分け
                     ├─ Writes: active_tasks.md, board/{date}-triage.md
                     └─ Sends:  LINE (gaku-co5.0 経由)
```

### 検討した代替案と判断

| 候補 | 評価 |
|---|---|
| (A) Claude API 直叩き | 既存 SKILL を手動で適用しなおす必要あり |
| (B) Claude Agent SDK | 同上、加えて SKILL を tool として再表現 |
| **(C) Claude Code ヘッドレス** | **採用** — 既存 SKILL・MEMORY・MCP がそのまま動く / Claude Code = HMC の判断主体のメンタルモデルが連続 / SSH で対話モード起動 → 同じ環境で再現可能 |
| (D) ルールのみ(LLM 無し) | 塚越さんの MD 表記ばらつきに耐えられず却下 |
| (E) 配管=コード/判断=LLM ハイブリッド | (C) が結果的にこれを内包(Claude Code 内部で配管+判断を扱う) |

### ベンダー中立性

CLAUDE.md の「Gemini/GPT 等の他LLMからも参照可能な形で設計する」方針に従い、種 YAML に `engine:` フィールドを設けて切り替え余地を残す:

```yaml
name: morning-briefing
engine: claude-code     # 将来: codex / gemini-cli へ切り替え可能
```

**現実的な制約**: SKILL.md は現状 Claude Code 向け書式。本格的に他エンジンへ乗り換える際は SKILL を「全AI 共通の薄い手順書」に書き直す必要が出る。最初は Claude Code 専用で書き、必要時に SKILL 中立化を後追い。

### 起動方式

- **常駐 daemon ではなく cron 都度起動**(最もシンプル)
- プロセス起動コスト(数秒〜数十秒)は朝/夜の用途で許容範囲
- API トークン消費は通常の Anthropic API 利用範囲(TOS 違反なし)

---

## 決定 5: Triage の対話チャネル = LINE + board MD ハイブリッド

### 構造

```
1. morning-briefing 種発火
   → Claude Code が backlog/recurring から曖昧期限・AI 支援候補を抽出
   → board/{date}-morning-briefing.md(質問入り MD)を生成
   → LINE で「Triage 質問あります。確認 → 返信か board 直接編集で」と通知

2. 塚越さんが LINE で短文返信  OR  board MD を Obsidian で直接編集
   → LINE 返信なら gaku-co5.0 が受信 → board ファイルに書き込む
   → board ファイル変更を event 種が検知

3. event 種が claude -p "Resume morning-briefing with new triage input"
   → Claude が回答を反映して最終 brief 確定
   → active_tasks 生成、board status を triage-done へ、LINE で確定通知
```

### 役割分担

| 要素 | 役割 |
|---|---|
| LINE | プッシュ通知 + 軽い片手返信 |
| board/*.md | 対話セッションの状態保持 + 振り返れるログ |
| Obsidian | board を MD として閲覧・編集する UI |

### 「LINE だけ」「MD だけ」を採らない理由

- **LINE 単独**: スレッドが流れる・履歴追跡困難・複数 Triage が混在しやすい
- **MD 単独**: 移動中にゼロタップで気付けない / Obsidian を都度開く手間

---

## 決定 6: night-review の挙動 = (C) 常に処理(差分のみ反映)

### 動作

| 入力状態 | 動作 |
|---|---|
| `[x]` チェック有り | backlog から削除 + archive 追記 |
| `[ ]` 未チェック | backlog に残す(active から消すだけ) |
| `## 追加` セクションに項目 | backlog へ追記(締切処理は決定 7 参照) |
| 完全に未編集(終日触らず) | LINE で 0件報告のみ、active は通常通りクリア |

active は **常にクリア**。

### 「未編集ならスキップ」を採らない理由

- backlog がマスタなので、active を毎晩クリアしても情報は失われない
- 翌朝の morning-briefing が backlog から今日締切を再抽出する設計のため、未完了タスクは自動で翌日に持ち越される(deadline が原型で残るので「期限超過」も自然に表現される)
- 分岐ロジックを入れないシンプルさが運用しやすい

### LINE フォーマット

```
🌱 夜のレビュー YYYY-MM-DD
✅ 完了: X件 (archive へ)
🔄 持ち越し: X件 (backlog 残存)
➕ 新規追加: X件
```

---

## 決定 7: `## 追加` の締切なしタスク = 翌日デフォルトで暫定締切付与

### 動作

night-review が `## 追加` を処理する際の 4 分岐:

| ケース | 動作 |
|---|---|
| `[x]` | 直接 archive へ(締切なくても完了済みなので OK) |
| `[ ]` + 締切記述あり | そのまま backlog へ追記 |
| `[ ]` + **締切なし** | **翌日デフォルトで暫定締切付与** → backlog へ。MD 形式: `- [ ] **{タスク}** (MM/DD締切・暫定)` |
| (空) | 何もしない |

### 翌朝の自動エスカレーション

morning-briefing が暫定締切タスクを **Triage 候補に自動格上げ**:

```markdown
### Q1: 締切確認が必要なタスク(夜種で暫定設定)
- [ ] 「{タスク}」 → 暫定: 今日(MM/DD)
  - [ ] (a) 今日のままで OK
  - [ ] (b) 今週中(金曜まで)
  - [ ] (c) 自由記述: ____
```

### 「翌日デフォルト」を選ぶ理由

- 必ず翌朝の active に登場 → Triage で確実に確認される → 埋もれない
- 翌営業日にすると土日に浮上しない可能性 — 「埋もれ防止」を優先するため非採用
- 今日 + 3日 / 7日はクッションが大きく、確認漏れリスクが残る

### 締切なし backlog タスクの起源

このルールの存在意義: **締切なし backlog タスク = 翌朝の active に登場しない = 埋もれる** という backlog-as-master 原則の盲点を、エントリポイントで強制対処する。

---

## 適用範囲

### 即時適用(本セッション)

- 本 ADR 起草
- 新規 `garden/soil/workflows/daily-cycle.md`(A 案テンプレ)起草
- `garden/MAP.md` に Phase 1/3 進捗追加、決定索引追加、宿題更新
- `docs/sessions/2026-05-25-session6.md` 起草

### Phase 3 実装課題(次セッション以降)

- 種 YAML スキーマ確定 + `morning-briefing` を pilot として実装
- VPS の CouchDB セットアップ手順策定
- Obsidian LiveSync プラグイン PC + iPhone 設定
- gaku-co5.0 側に「LINE 返信 → board MD 書き戻し」処理を実装
- 平文 MD ミラー daemon の実装(`_changes` feed リスナ)
- VPS 信頼性 watcher の設計(Phase 2 番人候補)

### 既存決定との関係

- **継承**: セッション4 ADR(種設計の方針)/ セッション5 ADR(workflow 正本性 + A 案テンプレ + 責務分割)
- **拡張**: 種候補リストに 4 本(daily-pilot 系)追加
- **影響**: Garden 全体の「頭脳」が Claude Code ヘッドレスに統一(以降のすべての種・番人に適用)

---

## 関連

- [セッション6 サマリ](../sessions/2026-05-25-session6.md)
- [セッション5 ADR — workflow 正本性 + 改善対象](2026-05-24-workflows-as-truth-and-improvement-targets.md)
- [セッション4 ADR — 種設計の方針](2026-05-23-seeds-design-direction.md)
- [garden/soil/workflows/daily-cycle.md](../../garden/soil/workflows/daily-cycle.md) — 新規起草の workflow
- [HMC hmc_pilot SKILL](../../../harappa-cockpit/.agent/skills/hmc_pilot/SKILL.md) — 移行元の処理定義
- [CLAUDE.md](../../CLAUDE.md)
