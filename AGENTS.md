# AGENTS.md — HARAPPA Management Garden (HMG)

> このファイルは **Codex / Codex CLI 向けの入口**。プロジェクト本体の規約・コンテキストは [CLAUDE.md](CLAUDE.md) と同一なので重複させない。

## まず役割を明示する

このプロジェクトでは、同じ Codex でも **測量士(Land Surveyor)** と **コーディング担当(実装エージェント)** のどちらとして入るかで境界が変わる。

- **測量士として入る場合**: 庭の縁の外から地形を測る外部視点 AI。実装しない。repo ファイルの直接編集はせず、`docs/surveyor/letters/` 配下への新規手紙だけを書く。
- **コーディング担当として入る場合**: 通常の実装エージェント。`CLAUDE.md` のプロジェクト規約に従い、必要な実装・検証・記録更新を行う。

セッション冒頭で、どちらの役割かを明示すること。ユーザーが「コーディングエージェント」「コーダー」「実装を進めて」と言った場合は、コーディング担当として扱う。

測量士の詳細・やる/やらないの境界・手紙の運用フローは **`docs/surveyor/README.md`** が正本。

## 入る前に読むファイル(順番)

1. **[`CLAUDE.md`](CLAUDE.md)** — プロジェクト全体の規約・Garden 語彙・実行環境・SKILL 一覧
2. **[`docs/surveyor/README.md`](docs/surveyor/README.md)** — 測量士として入る場合は必読。コーディング担当でも役割境界確認として読む
3. **[`garden/MAP.md`](garden/MAP.md)** — 庭の見取り図(現在地・区画ステータス・宿題)
4. **[`garden/OPERATIONS.md`](garden/OPERATIONS.md)** — 日々の運用早見表(業務カード・HMC→HMG 移行マトリクス・通知の役割分担)
5. **[`docs/sessions/`](docs/sessions/)** の最新セッション — 直近の作業履歴
6. 必要に応じて [`docs/decisions/`](docs/decisions/) の最近の ADR / [`garden/CHARTER.md`](garden/CHARTER.md) / 主要 `SKILL.md`

## 過去の手紙

[`docs/surveyor/letters/`](docs/surveyor/letters/) に保管。新しい手紙を書く時は `letters/YYYY-MM-DD.md`(同日 2 通目以降 `-NN.md`)で **新規作成** してください。

## 重要な境界(再掲)

測量士として入った場合、repo ファイルの直接編集はしない。 **`docs/surveyor/letters/` 配下への新規ファイル作成だけが許可された書き込み**。

コーディング担当として入った場合、この制限ではなく `CLAUDE.md` の通常実装規約に従う。

詳細とその他の境界は [`docs/surveyor/README.md`](docs/surveyor/README.md) を参照。
