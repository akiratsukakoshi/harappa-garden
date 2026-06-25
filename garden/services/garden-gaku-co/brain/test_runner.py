"""brain/runner.py の unit test(S60 / 測量士 2026-06-24 提案2)。

launcher.test.mjs の engine ケースに対応する Python 版。subprocess は実 claude を
呼ばず /bin/echo・/bin/false で success/failure パスを検証する(ネットワーク不要)。

実行: garden-gaku-co/ で `python -m brain.test_runner`(または python brain/test_runner.py)
"""
from __future__ import annotations

import os
import sys

# brain.runner を service ルート基準で import できるように
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.runner import (  # noqa: E402
    AgentResult,
    AgentRunSpec,
    ClaudeSubprocessRunner,
    CodexSubprocessRunner,
    McpSpec,
    ToolPolicy,
    UnsupportedEngineError,
    _normalize_tools,
    resolve_runner,
    unsupported_engine_message,
)


def test_resolve_default_is_claude():
    r = resolve_runner()
    assert isinstance(r, ClaudeSubprocessRunner)
    assert r.engine == "claude-code"


def test_resolve_explicit_claude():
    assert resolve_runner("claude-code").engine == "claude-code"


def test_resolve_explicit_codex():
    assert resolve_runner("codex").engine == "codex"


def test_resolve_unknown_engine_raises():
    # 未対応 engine は黙ってフォールバックせず ValueError(launcher と同方針)
    try:
        resolve_runner("gemini")
    except UnsupportedEngineError as e:
        assert e.engine == "gemini"
        assert e.supported == ["claude-code", "codex"]
        assert "gemini" in str(e) and "not supported" in str(e)
    else:
        raise AssertionError("gemini は ValueError を投げるべき")


def test_resolve_respects_env():
    os.environ["GARDEN_GAKU_CO_ENGINE"] = "gemini"
    try:
        resolve_runner()
    except UnsupportedEngineError as e:
        assert "gemini" in str(e)
    else:
        raise AssertionError("env の未対応 engine も ValueError")
    finally:
        del os.environ["GARDEN_GAKU_CO_ENGINE"]


def test_unsupported_engine_message_is_user_facing():
    err = UnsupportedEngineError("gemini", ["claude-code", "codex"])
    msg = unsupported_engine_message(err)
    assert "gemini" in msg
    assert "claude-code" in msg
    assert "codex" in msg
    assert "実行していません" in msg


def test_normalize_tools():
    assert _normalize_tools(["A", "B"]) == "A B"
    assert _normalize_tools("A B") == "A B"
    assert _normalize_tools(None) is None
    assert _normalize_tools([]) is None


def test_build_cmd_order():
    r = ClaudeSubprocessRunner(bin_path="claude")
    cmd = r.build_cmd(
        "PROMPT",
        system="SYS",
        model="sonnet",
        disallowed_tools=["Glob", "Grep"],
        strict_mcp=True,
    )
    # ★prompt は -p の直後(S54)
    assert cmd[:3] == ["claude", "-p", "PROMPT"]
    assert "--system-prompt" in cmd and cmd[cmd.index("--system-prompt") + 1] == "SYS"
    assert "--strict-mcp-config" in cmd
    assert cmd[cmd.index("--disallowedTools") + 1] == "Glob Grep"
    assert cmd[cmd.index("--model") + 1] == "sonnet"


def test_build_cmd_minimal():
    r = ClaudeSubprocessRunner(bin_path="claude")
    cmd = r.build_cmd("P")
    assert cmd == ["claude", "-p", "P"]  # 任意フラグ無しは素の -p のみ


def test_run_spec_translates_neutral_spec_to_claude_flags():
    r = ClaudeSubprocessRunner(bin_path="/bin/echo")
    spec = AgentRunSpec(
        prompt="hello-spec",
        system="SYS",
        model="sonnet",
        tool_policy=ToolPolicy(deny=["Glob", "Grep"]),
        mcp=McpSpec(strict=True),
    )
    res = r.run_spec(spec)
    assert res.ok
    assert "hello-spec" in res.text
    assert "--system-prompt SYS" in res.text
    assert "--strict-mcp-config" in res.text
    assert "--disallowedTools Glob Grep" in res.text
    assert "--model sonnet" in res.text


def test_codex_build_cmd_is_read_only_ephemeral():
    r = CodexSubprocessRunner(bin_path="codex")
    spec = AgentRunSpec(
        prompt="hello-codex",
        system="SYS",
        model="gpt-5-codex",
        cwd="/tmp",
    )
    cmd = r.build_cmd(spec)
    assert cmd[:2] == ["codex", "exec"]
    assert "--sandbox" in cmd and cmd[cmd.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in cmd
    assert "-C" in cmd and cmd[cmd.index("-C") + 1] == "/tmp"
    assert "--model" in cmd and cmd[cmd.index("--model") + 1] == "gpt-5-codex"
    assert cmd[-1] == "SYS\n\nhello-codex"


def test_codex_build_cmd_scratch_write_uses_workspace_write():
    r = CodexSubprocessRunner(bin_path="codex")
    spec = AgentRunSpec(
        prompt="write scratch",
        cwd="/tmp/garden-smoke",
        tool_policy=ToolPolicy(mode="scratch-write"),
    )
    cmd = r.build_cmd(spec)
    assert "--sandbox" in cmd and cmd[cmd.index("--sandbox") + 1] == "workspace-write"
    assert "-C" in cmd and cmd[cmd.index("-C") + 1] == "/tmp/garden-smoke"


def test_codex_run_success_via_echo():
    r = CodexSubprocessRunner(bin_path="/bin/echo")
    res = r.run_spec(AgentRunSpec(prompt="hello-codex", cwd="/tmp"))
    assert res.ok and res.returncode == 0
    assert "exec --sandbox read-only" in res.text
    assert "hello-codex" in res.text


def test_run_success_via_echo():
    # /bin/echo は全引数を表示して exit 0 → ok=True・text に prompt が乗る
    r = ClaudeSubprocessRunner(bin_path="/bin/echo")
    res = r.run("hello-prompt", model="sonnet")
    assert isinstance(res, AgentResult)
    assert res.ok and res.returncode == 0
    assert "hello-prompt" in res.text


def test_run_failure_via_false():
    # /bin/false は exit 1 → ok=False
    r = ClaudeSubprocessRunner(bin_path="/bin/false")
    res = r.run("x")
    assert not res.ok and res.returncode == 1


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"✔ {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"✘ {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
