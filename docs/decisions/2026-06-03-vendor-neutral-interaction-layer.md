# 2026-06-03 ADR — 対話層のベンダー中立アーキテクチャ(LLM アダプタ + 中立ツール層)+ 内側/外側分離の再確認

- **日付**: 2026-06-03
- **記録**: セッション31
- **決定者**: ガクチョ(庭師) / Claude
- **ステータス**: Accepted(設計確定 / 実装は段階)

## 背景

S31 で「運営スタッフ(LINE)にガクコを対話参加させたい(日々の意思決定サポート + コアへのツール提供)」を検討する過程で、3 つの事実が判明・確認された:

1. **gaku-co5.0 は既に LINE リアルタイム対話 + メンション制御(Stage1 `should_respond`)+ scope 別 persona/権限/記憶を実装済み**で、docker `gaku-co5` として稼働中。S22 統合 ADR が前提にしていた「garden-gaku-co が本流・gaku-co5.0 はレガシー」の構図は、LINE/マルチ scope に関しては **逆転**していた。
2. しかし gaku-co5.0 は **社外メンバー(デジタル原っぱ大学 / AIBOU LAB)** も相手にする。社外スレッドにスタッフ情報が漏れるリスクは、スタッフグループ間の混線より重大。→ 内側(社内)と外側(社外)は **物理デプロイ分離(エアギャップ)** が必須(2026-05-28 ADR 決定4 の再確認)。
3. チーム channel の頭脳は **b = Anthropic SDK(Haiku ゲート)** 採用(2026-05-28 決定3)。だが「ベンダーロックインを避ける」という本プロジェクトの前提([CLAUDE.md ベンダー中立の方針] / memory [vendor-neutrality-skills])と緊張する。「API を使う = Anthropic に縛られる」のではないことを設計で担保する必要がある。

本 ADR は、対話層を **「中立な知識層・行動層 + 差し替え可能な LLM バックエンド」** で構成する原則を確定する。

## 決定

### 決定1: 対話層を 3 層に分離し、ベンダー依存を最下層 1 枚に閉じ込める

| 層 | 中身 | 置き場所 | ベンダー依存 |
|---|---|---|---|
| **知識層**(どう振る舞うか) | SKILL.md / CHARTER.md / persona(scope 別) | プロジェクト内 markdown | **中立**(現状維持) |
| **行動層**(何ができるか) | 素の Python 関数 + 中立ツール定義(name / description / JSON schema)+ capability 設定(scope → 使えるツール) | プロジェクト内 | **中立** |
| **LLM バックエンド**(誰が考えるか) | a: claude subprocess / b: Anthropic SDK / 将来: 他社 SDK | アダプタ 1 枚に隔離 | ここ**だけ**ベンダー固有 |

知識層・行動層は LLM を替えても残る資産。乗り換えコストはアダプタ差し替えに局所化する。

### 決定2: LLM プロバイダ・アダプタ(brain は `import anthropic` しない)

- `brain/provider.py` に統一インターフェース `chat(system, messages, tools) -> {text, tool_calls}` を置く。
- ゲート(Stage1)・応答生成(Stage2)・tool-use ループは **このインターフェースだけ**を呼ぶ。
- プロバイダ実装(`AnthropicProvider` など)はアダプタ内に閉じる。`claude subprocess`(master 用)も同じインターフェースの一実装として扱う。
- **gaku-co5.0 を「レガシー移植」する際、`import anthropic` の散在をそのままコピーしない**。アダプタに集約してから移す(これが移植の中心規律)。

### 決定3: ツールは「素の Python 関数 + 中立スキーマ + capability 設定」、全てプロジェクト内

- function-calling(tool-use)は Anthropic 固有ではなく OpenAI / Gemini も同形式(name + description + JSON schema)。定義は **ほぼ共通**で、移植はアダプタの薄いラッパで済む。
- ツールの **ロジック** = 素の Python 関数。**定義** = 中立スキーマ。**認可** = `capabilities.py` の `scope → frozenset(tool_names)` マップ。
- LLM に渡す時だけアダプタがプロバイダ形式へ変換する。
- これにより、行動層は完全に Garden 内に残り、ベンダー乗り換えに耐える。

### 決定4: 「skill」の二義を整理する

Garden で「skill」は文脈により 2 つを指す。混同を避けるため本 ADR で用語を固定:

- **知識 skill** = `SKILL.md`(手順・判断ルール・知識)。prompt に load される markdown。
- **行動 tool** = LLM が呼べる関数(`get_tasks()` 等)。決定3 の中立ツール。
- **capability** = scope がどの知識 skill / 行動 tool を使えるかのゲート。「コアで使える skills を実装」= 行動 tool を定義 + core_team の capability に追加 + 必要なら知識 skill を scope に load。

### 決定5: 内側/外側の物理分離を再確認し、過去 ADR の表現を訂正

2026-05-28 ADR 決定4 を**正本**として再確認する:

```
内側 = garden-gaku-co(Garden 接続 OK・garden-mirror 読み書き OK)
  ├ ガクチョ      : Discord master      … 稼働中(頭脳 a)
  ├ 運営スタッフ  : LINE core_team      … S31 で着手(頭脳 b)
  └ スタッフALL   : LINE staff          … 次(厳密制御・頭脳 b)
外側 = gaku-co5.0(Garden の mount/credential を一切持たない・soil/memory 非共有)
  ├ デジタル原っぱ大学
  └ AIBOU LAB
```

- **2026-05-31 統合 ADR の「gaku-co5.0 = 撤退対象 / リポジトリ凍結」という表現は誤解を招くため訂正**:gaku-co5.0 は **撤退(消滅)ではなく「社外専用デプロイへ痩せて生存」**(エアギャップ)。社内機能のみが garden-gaku-co に移る。
- 内側 LINE は社外 aibou とは **別の LINE 公式アカウント(別 bot)** を新規作成して受ける(庭師が用意)。内側用 API key も社外とは別建て(請求・失効を分離)。

### 決定6: 頭脳はチャネル単位で選び、両方アダプタの裏に置く

- **master(1対1・低頻度・全発話が宛先)= a(claude subprocess・サブスク・Garden ネイティブツール)**:現状維持。
- **チーム(多人数・大半が非宛・情報境界必須)= b(Anthropic SDK・Haiku ゲート)**。理由(2026-05-28 決定3 + S31 で言語化):
  1. 毎メッセージのゲート経済(「いつ黙るか」を ~100token の Haiku で安く高速判定)
  2. サブスク同時セッション競合の回避(cron 種 + master bot が claude -p を使用中)
  3. LINE reply トークンの時間窓に間に合う速度
  4. **情報境界を capability で構造的に保証**(財務/給与ツールが staff scope の手に存在しない)= prompt 頼みより堅い
- 両頭脳をアダプタ抽象の裏に置くことで、将来 master を別 LLM に移すのも同じ口で済む。

## 実装順序(過剰設計を避ける)

1. **中立基盤を薄い実スライスで先に通す**(本 ADR の「1 の実装」):`brain/provider.py`(アダプタ + Anthropic 実装)+ `tools/registry.py`(ツール 1 個)+ `capabilities.py` 雛形 + smoke test(1 回の chat 往復 + 1 ツール呼び出し)。LINE OA 不要なのでガクチョの bot 作成を待たず着手可。
2. **core_team 機能を基盤の上に積む**(「2」):内側 LINE webhook(FastAPI)+ reply/push + Stage1 ゲート + scope 別 persona/memory(`garden/memory/line_core_team/`)+ 最初の行動 tool 群。LINE OA(別 bot)+ 内側 API key の用意が前提。
3. しばらく運用観察 → スタッフALL(staff、厳密)へ展開。

### ディレクトリ案(garden-gaku-co 内)

```
garden/services/garden-gaku-co/
  bot.py            # Discord master(頭脳 a)— 現状
  brain/
    provider.py     # LLM アダプタ(chat インターフェース + Anthropic 実装、後で claude-sub 実装も)
    gate.py         # Stage1 should_respond
    respond.py      # Stage2 応答 + tool-use ループ
  tools/
    registry.py     # name/description/schema + handler 登録
    *.py            # 行動 tool 群(素 Python)
  capabilities.py   # scope -> frozenset(tool_names)
  line/             # 内側 LINE webhook(FastAPI)— gaku-co5.0 から移植
    webhook.py / sender.py / signature.py
  personas/         # scope 別 persona(master/core_team/staff).md
  memory_logger.py  # 既存(scope 引数化)
```

知識層は既存の `garden/plots/*/SKILL.md` + `garden/CHARTER.md` を scope 別に load(新規ディレクトリ不要)。

## 影響

- **ベンダーロックイン回避が「API を使わない」ではなく「アダプタで隔離する」に再定義される**。b(API Haiku)採用とベンダー中立が両立する。
- gaku-co5.0 の移植は「コピー」ではなく「アダプタ集約しながら取り込む」作業になる(規律が要る分、最初は少し重い)。
- 行動 tool / capability が Garden 内資産として蓄積され、scope 越え濫用が構造的に防げる(情報境界の本実装)。

## 未決事項

- 内側 LINE 公式アカウント(別 bot)の発行 — **庭師作業**(S31 時点で未)。
- 内側 API key の調達・配置(VPS `.env` chmod 600、社外と別建て)。
- 知識 skill(SKILL.md)を scope 別に load する loader の具体(既存の自前 picker を踏襲)。
- master 用 claude-subprocess をアダプタ実装としていつ揃えるか(当面 bot.py 現状維持で可)。

## 関連

- 正本: [2026-05-28 garden-gaku-co interaction-layer](2026-05-28-garden-gaku-co-interaction-layer.md) 決定3・決定4・決定6
- 訂正対象: [2026-05-31 garden-gaku-co 統合方針](2026-05-31-garden-gaku-co-unification.md)(「撤退/凍結」→「社外専用化・生存」)
- 連動: [2026-05-31 記憶の三層分離 + soil 振り分け](2026-05-31-memory-three-layer-and-soil-routing.md) Stage D
- 前提: [CLAUDE.md ベンダー中立の方針] / memory [vendor-neutrality-skills]
- 移植元: gaku-co5.0 `app/line/` `app/llm/switch.py` `app/llm/agent.py` `app/config/channels.py`
