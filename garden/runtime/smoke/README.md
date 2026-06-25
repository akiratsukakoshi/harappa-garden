# runtime smoke

Garden Runtime の runner 切替で最初に通す smoke。

目的は「実業務を動かす」ことではなく、runner 配線が以下を満たすかを低リスクに確認すること。

- seed frontmatter の `engine` が解決される
- prompt / cwd / timeout / log / state が組み立つ
- runner CLI 引数翻訳が観測できる
- master runner の未対応 engine / Claude runner 互換テストが通る
- secret 値・board・soil・hmc_tasks に触れない

## 実行

```bash
python3 garden/runtime/smoke/run-smoke.py
python3 garden/runtime/smoke/run-smoke.py --engine codex
python3 garden/runtime/smoke/run-smoke.py --engine codex --mode scratch-write
```

この smoke は temp directory だけに seed/log/state/lock を作る。実 LLM は呼ばず、runner 実行パスは
`CLAUDE_BIN=/bin/echo` / `CODEX_BIN=/bin/echo` で CLI 引数翻訳を確認する。

実 runner の read-only 初回確認だけを行う場合は、明示的に `--real-runner` を付ける。

```bash
python3 garden/runtime/smoke/run-smoke.py --engine codex --real-runner
python3 garden/runtime/smoke/run-smoke.py --engine codex --mode scratch-write --real-runner
```

`--real-runner` でも production board / soil / hmc_tasks は使わず、temp seed/log/state/lock だけを使う。
`--mode scratch-write` は temp scratch directory を working directory にして、`smoke-output.txt` の生成だけを確認する。
