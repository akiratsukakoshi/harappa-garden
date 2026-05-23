# 種(seeds) 設計の基本方針

- **日付**: 2026-05-23
- **記録**: セッション4
- **決定者**: 塚越さん (庭師) / Claude (壁打ち相手)
- **ステータス**: 方針合意。実装(YAML スキーマ・最初の種)は次セッション以降

## 背景

Phase 3「種(自律トリガー)」の入口として、HMC `shift_manager` SKILL を題材に **「誰が」「いつ」「何に発火されて」動くか** を全体像で議論した。塚越さんの要請: 「私の作業・AI の作業・発火のトリガーを、全体の流れとタイミングに置いてイメージを出してほしい」。

shift_manager は年次/月次/開催の3周期 × cron/event/state-change の3トリガー型を持ち、Phase 3 設計の代表題材として適している。

## 決定 1: Garden には3つの時計が回る

| 時計 | 例(shift_manager) | 対応する workflows |
|---|---|---|
| **年の時計** | Annual 取込・3ヶ月先取り企画 | annual-quarterly-planning.md |
| **月の時計** | シフト募集→確定→実施→精算 | monthly-cycle.md |
| **開催の時計** | プログラム当日の運行 | program-execution.md |

種は各時計の文字盤に植わる「時刻 / 事件 / 状態変化」のどれかとして表現する。

## 決定 2: 種は3形式

| 種型 | 発火源 | 例 |
|---|---|---|
| **cron** | 暦が回る | 月末 → 月次シート生成 / 月初 → 稼働時間集計 |
| **event** | 外部で何かが起きる | フォーム回答 / 請求書メール / LINE 着信 |
| **state-change** | 庭内の状態が変わる | Q列(アンケート)チェック / 確定セルチェック / シート編集 |

## 決定 3: AI = 下書き工場 / 庭師 = 剪定者

- 種が点火 → AI が **下書き** を置く → 塚越さんが **剪定**(承認/修正/却下)
- AI が代行するのは「時計を見る」「コマンドを叩く」「機械的な集計・転記」
- 塚越さんが引き続き担うのは「判断・承認・対人対応・経営判断」

## 決定 4: ガクコ(gaku-co5.0) = 庭の出口(門)

LINE Bot ガクコは既に 3チャネル × 双方向 × 承認フローを備える。これを「庭の門」として **そのまま再利用** する(再発明しない)。

| ガクコ概念 | Garden 用語 | 用途 |
|---|---|---|
| `personal` チャネル | 庭師の私書箱 | 経営情報OK / 即時送信 |
| `core_team` チャネル | 運営の寄合場 | 運営4名(現状)・財務OK / 即時送信 |
| `staff` チャネル | 全スタッフの広場 | 財務NG / **必ず剪定経由** |
| `/webhook` → `/queue` | 入口の種(event) | LINE着信を `event` 種として庭が拾う |
| `/send` (require_approval=true) → `/pending` → `/approve` | 既存の剪定機構 | staff 宛はこれを使う |

参考: [/home/tukapontas/gaku-co5.0/INTERFACE.md](file:///home/tukapontas/gaku-co5.0/INTERFACE.md)

## 決定 5: 番人(watcher) の動作 = 定刻 cron + 緊急 push

3案を比較し **C 案** を採用:

| 案 | 動作 | 採否 | 理由 |
|---|---|---|---|
| A. 常駐 polling (60秒間隔) | リアルタイム性高いが運用負荷重い | ✗ | 監視・再起動・通知の設計が一気に重くなる |
| B. 完全オンデマンド (Claude Code 起動時のみ) | 軽いが反応が半日〜1日 | ✗ | スタッフが朝LINEしても夜まで気づかない |
| **C. 定刻 cron + 緊急 push** | OS cron が1日数回起こす。請求書到着など緊急種のみ即 push | **✓** | 現行リズム(朝LINE・夜PC)と整合。冪等にすれば失敗復旧も cron 任せ |

緊急 push の起動方法は別途設計(候補: ガクコ側で「重要マーク」を持ち、該当イベント受信時に HMG ローカルへ webhook 送出 など)。

## 決定 6: 剪定の置き場は「重さで自動振り分け」

下書きを作る AI 自身が、メタデータで剪定チャネルを判定する:

| 重さ | 例 | 置き場 | メタデータ |
|---|---|---|---|
| **軽**(1往復で済む) | 「リマインド送る?」「給与本登録GO?」 | ガクコ `/pending` + LINE `personal` | `pruning_channel: line` |
| **中**(diff を見たい) | 給与 dry-run の差分、稼働時間集計 | `garden/board/pending/` + LINE で「PCで見て」通知のみ | `pruning_channel: board_with_notify` |
| **重**(議論したい) | 種設定変更、土壌編集、フロー見直し | `garden/board/pending/` のみ | `pruning_channel: board` |

**鉄則**: LINE で見えないものを garden に置かない。最低でも「剪定待ち N 件」は LINE 側に見える状態を維持する(さもないと PC を開かない日に剪定が腐る)。

## 決定 7: ガクコ `core_team` チャネルは当面いじらない

- 現状 `core_team` = 塚越さん + 運営4名。**飯田さんは未参加**
- 「企画会議メンバー(5名)」と「ガクコ core_team(4名)」は別概念として土壌で持つ
- HMG が `core_team` へ通知を投げ始めるタイミング(Phase 3 後半)で、飯田さん追加可否を再判断
- [[junki-iida]] ページに「core_team 未参加」を明記済み

## 保留 / 未決

### 稼働時間表のスタッフへの見せ方

塚越さんの懸念: 「スタッフ ALL の LINE を連絡窓口に統合しているので、個別は埋もれる。メンション全員つけるとメッセージが長くなる」。

候補:
- 個別テキスト要約(あなたの稼働時間: 〜)を全員に並列送信 → ガクコに **個別送信機能の追加が必要**
- スプシ個人タブ + 全員に「自分のタブを開いてください」リンク → スマホでタブ切替の手間
- 現状(スクショ) を踏襲 → 塚越さんの手作業が残る

→ **塚越さんが検討、後日結論**

### 種の YAML スキーマ

- 「いつ点火するか / 何を実行するか / 結果をどこに置くか / 誰に剪定依頼するか」の4要素
- `pruning_channel` メタデータの厳密化
- 失敗時の振る舞い(`on_failure`)
- **次セッションの本命**

### ガクコ INTERFACE.md への追加要望(将来)

- 個別 LINE ユーザーID 指定での `/send`(現在は group enum 3値固定)
- `/queue` ポーリング以外の push 経路(緊急種用)

## 関連

- [セッション4 サマリ](../sessions/2026-05-23-session4.md)
- [HMC shift_manager SKILL](file:///home/tukapontas/harappa-cockpit/.agent/skills/shift_manager/SKILL.md)
- [HMC shift_manager マニュアル](file:///home/tukapontas/harappa-cockpit/docs/manuals/shift_manager.md)
- [ガクコ INTERFACE.md](file:///home/tukapontas/gaku-co5.0/INTERFACE.md)
- [garden/soil/workflows/](../../garden/soil/workflows/)
