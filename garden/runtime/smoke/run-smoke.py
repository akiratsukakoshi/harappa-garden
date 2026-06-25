#!/usr/bin/env python3
"""Garden Runtime smoke test.

実 LLM / secret / production board に触れず、runner 切替面の配線だけを見る。
"""
from __future__ import annotations

import os
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


READ_ONLY_PROMPT = """runtime smoke: {marker}"""
SCRATCH_WRITE_PROMPT = """Create a file named smoke-output.txt in the current working directory with exactly this content:
runtime-smoke-ok

Do not modify anything outside the current working directory. After writing the file, reply with done."""


SMOKE_SEED = """---
type: seed
name: {seed_name}
plot: smoke
description: runtime smoke seed
status: draft
trigger:
  type: cron
  schedule: "0 0 * * *"
  timezone: Asia/Tokyo
engine: {engine}
execute:
  working_dir: {root}
{model_line}
  tool_policy:
{tool_policy_mode}
    deny:
      - "Glob"
      - "Grep"
  computed_inputs:
    marker: "runtime-smoke"
  prompt: |
{prompt}
---

# runtime smoke
"""


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: int = 60) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["claude-code", "codex"], default="claude-code")
    parser.add_argument("--mode", choices=["read-only", "scratch-write"], default="read-only")
    parser.add_argument(
        "--real-runner",
        action="store_true",
        help="call the real runner binary instead of /bin/echo; use only for read-only manual checks",
    )
    parser.add_argument("--model", default=None, help="optional model/profile name passed to the seed runner")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="garden-runtime-smoke-") as tmp_s:
        tmp = Path(tmp_s)
        seeds = tmp / "seeds" / "smoke"
        log = tmp / "log"
        locks = tmp / "locks"
        scratch = tmp / "scratch"
        seeds.mkdir(parents=True)
        log.mkdir()
        locks.mkdir()
        scratch.mkdir()
        model = args.model
        if model is None and not args.real_runner:
            model = "smoke-model"
        model_line = f"  model: {model}" if model else ""
        seed_name = "scratch-write" if args.mode == "scratch-write" else "read-only"
        working_root = scratch if args.mode == "scratch-write" else ROOT
        prompt_template = SCRATCH_WRITE_PROMPT if args.mode == "scratch-write" else READ_ONLY_PROMPT
        prompt = "\n".join(f"    {line}" for line in prompt_template.splitlines())
        tool_policy_mode = "    mode: scratch-write" if args.mode == "scratch-write" else ""
        (seeds / f"{seed_name}.md").write_text(
            SMOKE_SEED.format(
                root=working_root.as_posix(),
                engine=args.engine,
                model_line=model_line,
                seed_name=seed_name,
                tool_policy_mode=tool_policy_mode,
                prompt=prompt,
            ),
            encoding="utf-8",
        )

        launcher_env = {
            "GARDEN_SEEDS_ROOT": str(tmp / "seeds"),
            "GARDEN_LOG_ROOT": str(log),
            "GARDEN_STATE_FILE": str(tmp / "state.json"),
            "GARDEN_LOCK_DIR": str(locks),
        }
        if not args.real_runner:
            if args.engine == "claude-code":
                launcher_env["CLAUDE_BIN"] = "/bin/echo"
            if args.engine == "codex":
                launcher_env["CODEX_BIN"] = "/bin/echo"
        launcher_dir = ROOT / "garden" / "services" / "launcher"
        seed_ref = f"smoke/{seed_name}"
        run(["node", "launcher.mjs", "--seed", seed_ref, "--dry-run"], cwd=launcher_dir, env=launcher_env)
        run(
            ["node", "launcher.mjs", "--seed", seed_ref],
            cwd=launcher_dir,
            env=launcher_env,
            timeout=240 if args.real_runner else 60,
        )
        if args.real_runner and args.mode == "scratch-write":
            out = scratch / "smoke-output.txt"
            if not out.exists():
                raise SystemExit(f"scratch write output not found: {out}")
            content = out.read_text(encoding="utf-8").strip()
            if content != "runtime-smoke-ok":
                raise SystemExit(f"unexpected scratch write output: {content!r}")
            print(f"scratch write verified: {out}")

    run(["python3", "-m", "brain.test_runner"], cwd=ROOT / "garden" / "services" / "garden-gaku-co")
    run(["python3", "test_render.py"], cwd=ROOT / "garden" / "runtime")
    print("runtime smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
