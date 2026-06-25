# switch-to-codex checklist

> Codex を「移管システムの最初の検証ケース」として扱うための手順。
> 最初から board / soil を編集させず、実編集なしから始める。

## 0. 前提

- この checklist は本番切替ではなく、Codex runner 実走リハーサル用。
- secret の値は表示しない。
- `.env` を source する script に `bash -x` を使わない。
- 既存 active は `engines.yml` 上では `claude-code` のままにする。

## 1. Precheck

- [ ] Codex CLI または対象 runner binary が runtime host にある
- [ ] 認証状態を set/unset または length 比較だけで確認した
- [ ] runner の model/profile 候補を決めた
- [ ] `audit-vendor-lock.py` を実行し、`unclassified` を確認した
- [ ] `grants.yml` の権限語彙を Codex 側へ翻訳できるか確認した
- [ ] MCP config の読み込み方法を確認した

## 2. Dry-run

- [ ] launcher dry-run で `engine: codex` が未対応エラーになることを確認した
- [ ] Codex runner 実装後、dry-run で runner 解決とログだけ確認した
- [ ] prompt / cwd / timeout / model/profile がログで読める
- [ ] secret 値がログに出ていない

## 3. Read-only run

- [ ] repo 読み取りだけの prompt で起動した
- [ ] exit code / stdout / stderr が runner 層で捕捉される
- [ ] 未対応 tool は明示エラーになる
- [ ] timeout が効く

## 4. Scratch write

- [ ] 書き込み先を `/tmp` または専用 scratch に限定した
- [ ] board / soil / hmc_tasks には触っていない
- [ ] 書き込み結果を確認後、不要なら破棄した

## 5. Seed smoke

- [ ] 低リスク seed を 1 本だけ選んだ
- [ ] その seed の実行結果が scratch/log に限定されることを確認した
- [ ] MCP なし seed で先に通した
- [ ] MCP あり seed は別手順で確認した

## 6. Master bot smoke

- [ ] `GARDEN_GAKU_CO_ENGINE=codex` の未対応エラーが user/log に丁寧に返る
- [ ] Codex runner 実装後、短い read-only 応答だけ確認した
- [ ] 常駐 provider(`anthropic`)との軸を混ぜていない

## 7. Rollback

- [ ] `engines.yml` の active を `claude-code` のままに戻す、または維持する
- [ ] `GARDEN_GAKU_CO_ENGINE` を unset / `claude-code` に戻す
- [ ] seed frontmatter の `engine` を `claude-code` に戻す
- [ ] scratch 生成物を破棄する
- [ ] session に実験結果と差分を書く
