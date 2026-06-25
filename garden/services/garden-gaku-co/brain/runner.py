"""Agent runner 抽象 — サブプロセス型 LLM エージェントのベンダー中立レイヤ。

launcher.mjs の resolveRunner(JS) の Python 版(測量士 2026-06-24 提案2)。
bot.py / morning_greet.py / night_cheer.py が `claude -p` を直接 spawn していたのを、
engine 切替可能な runner の裏に退避する。これにより「主担当 LLM を替える」前に
「主担当を替えられる構造」を先に作る。

軸の違い(重要 — 混ぜない):
  - brain/provider.py = API 常駐チャット(registry tool 制限付き、in-process)。LINE/team 用。
  - brain/runner.py   = サブプロセス全権エージェント(repo cwd、OS 権限は .claude/settings.json)。
                        master Discord / 定時あいさつ用。ここは後者。

engine は GARDEN_GAKU_CO_ENGINE(既定 claude-code)。未対応 engine は resolve_runner() が
明示エラー(ValueError)で落とす — 黙って claude にフォールバックしない(launcher と同方針)。
codex / gemini runner を足すときは別 Runner クラスを書いて RUNNERS に登録する。
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field


@dataclass
class AgentResult:
    """サブプロセス実行の中立結果。user 向け文面の整形は呼び出し側が行う。"""
    ok: bool
    text: str = ""
    returncode: int | None = None
    error: str | None = None  # "timeout" 等、非ゼロ終了以外の失敗種別


@dataclass
class ToolPolicy:
    """runner へ渡す tool 利用方針。各 runner が自分の CLI/API 表現へ翻訳する。"""

    allow: list[str] | None = None
    deny: list[str] | str | None = None
    mode: str | None = None


@dataclass
class McpSpec:
    """MCP 接続・権限の中立指定。Claude CLI フラグは runner 側に閉じる。"""

    config: str | None = None
    strict: bool = False
    permission_mode: str | None = None
    allowed_tools: list[str] | None = None


@dataclass
class AgentRunSpec:
    """サブプロセス型エージェントに渡す中立入力。"""

    prompt: str
    system: str | None = None
    model: str | None = None
    profile: str | None = None
    cwd: str | None = None
    timeout: int = 300
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    mcp: McpSpec = field(default_factory=McpSpec)
    extra_args: list[str] | None = None


class UnsupportedEngineError(ValueError):
    """runner 未実装 engine を指定したときの明示エラー。"""

    def __init__(self, engine: str, supported: list[str]):
        self.engine = engine
        self.supported = supported
        super().__init__(
            f"engine '{engine}' is not supported by runner yet "
            f"(supported: {', '.join(supported)}). codex/gemini runner は未実装。"
        )


def supported_engines() -> list[str]:
    return sorted(RUNNERS)


def unsupported_engine_message(exc: UnsupportedEngineError) -> str:
    """Discord/log にそのまま出せる未対応 engine の説明。"""
    supported = ", ".join(exc.supported) if exc.supported else "(none)"
    return (
        f"⚠️ Garden runner の未対応 engine が指定されています: {exc.engine}\n"
        f"対応済み engine: {supported}\n"
        "この環境ではまだ該当 runner が登録されていないため、実行していません。"
    )


def _normalize_tools(tools) -> str | None:
    """disallowed_tools を claude CLI の 1 引数(空白区切り)へ正規化。

    list[str] でも空白区切り str でも受ける(呼び出し側の既存定数を壊さないため)。
    """
    if not tools:
        return None
    if isinstance(tools, (list, tuple)):
        return " ".join(str(t) for t in tools)
    return str(tools)


class AgentRunner:
    """サブプロセス型エージェントの抽象基底。"""

    engine: str = "abstract"

    def run(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        disallowed_tools=None,
        strict_mcp: bool = False,
        cwd: str | None = None,
        timeout: int = 300,
        extra_args=None,
    ) -> AgentResult:
        spec = AgentRunSpec(
            prompt=prompt,
            system=system,
            model=model,
            cwd=cwd,
            timeout=timeout,
            tool_policy=ToolPolicy(deny=disallowed_tools),
            mcp=McpSpec(strict=strict_mcp),
            extra_args=list(extra_args) if extra_args else None,
        )
        return self.run_spec(spec)

    def run_spec(self, spec: AgentRunSpec) -> AgentResult:
        raise NotImplementedError


class ClaudeSubprocessRunner(AgentRunner):
    """`claude -p` をサブプロセス起動する runner(現状の唯一の実装)。"""

    engine = "claude-code"

    def __init__(self, bin_path: str | None = None):
        self.bin = bin_path or os.environ.get("CLAUDE_BIN", "claude")

    def build_cmd(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        disallowed_tools=None,
        strict_mcp: bool = False,
        extra_args=None,
    ) -> list[str]:
        """claude CLI 引数列を組み立てる(spawn せず・テスト可能に分離)。

        ★prompt は positional として -p の直後に置く。--disallowedTools 等の可変長
          オプションを末尾に置くと直後の prompt を飲み込んで落ちる(launcher S54 と同根)。
        """
        cmd = [self.bin, "-p", prompt]
        if system:
            cmd += ["--system-prompt", system]
        if strict_mcp:
            cmd += ["--strict-mcp-config"]
        tools = _normalize_tools(disallowed_tools)
        if tools:
            cmd += ["--disallowedTools", tools]
        if model:
            cmd += ["--model", model]
        if extra_args:
            cmd += list(extra_args)
        return cmd

    def run(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        disallowed_tools=None,
        strict_mcp: bool = False,
        cwd: str | None = None,
        timeout: int = 300,
        extra_args=None,
    ) -> AgentResult:
        spec = AgentRunSpec(
            prompt=prompt,
            system=system,
            model=model,
            cwd=cwd,
            timeout=timeout,
            tool_policy=ToolPolicy(deny=disallowed_tools),
            mcp=McpSpec(strict=strict_mcp),
            extra_args=list(extra_args) if extra_args else None,
        )
        return self.run_spec(spec)

    def run_spec(self, spec: AgentRunSpec) -> AgentResult:
        cmd = self.build_cmd(
            spec.prompt,
            system=spec.system,
            model=spec.model,
            disallowed_tools=spec.tool_policy.deny,
            strict_mcp=spec.mcp.strict,
            extra_args=spec.extra_args,
        )
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=spec.timeout, cwd=spec.cwd
            )
        except subprocess.TimeoutExpired:
            return AgentResult(ok=False, error="timeout")
        if proc.returncode != 0:
            return AgentResult(
                ok=False,
                returncode=proc.returncode,
                error=(proc.stderr or "").strip(),
            )
        return AgentResult(ok=True, text=(proc.stdout or "").strip(), returncode=0)


class CodexSubprocessRunner(AgentRunner):
    """`codex exec` を read-only / ephemeral で起動する runner。"""

    engine = "codex"

    def __init__(self, bin_path: str | None = None):
        self.bin = bin_path or os.environ.get("CODEX_BIN", "codex")

    def build_cmd(self, spec: AgentRunSpec) -> list[str]:
        prompt = spec.prompt
        if spec.system:
            prompt = f"{spec.system}\n\n{spec.prompt}"
        sandbox = "workspace-write" if spec.tool_policy.mode == "scratch-write" else "read-only"
        cmd = [
            self.bin,
            "exec",
            "--sandbox",
            sandbox,
            "--color",
            "never",
            "--skip-git-repo-check",
            "--ephemeral",
        ]
        if spec.cwd:
            cmd += ["-C", spec.cwd]
        if spec.model:
            cmd += ["--model", spec.model]
        if spec.profile:
            cmd += ["--profile", spec.profile]
        if spec.extra_args:
            cmd += list(spec.extra_args)
        cmd.append(prompt)
        return cmd

    def run_spec(self, spec: AgentRunSpec) -> AgentResult:
        if spec.mcp.config or spec.mcp.allowed_tools or spec.mcp.permission_mode:
            return AgentResult(ok=False, error="codex runner does not support MCP translation yet")
        cmd = self.build_cmd(spec)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=spec.timeout, cwd=spec.cwd
            )
        except subprocess.TimeoutExpired:
            return AgentResult(ok=False, error="timeout")
        if proc.returncode != 0:
            return AgentResult(
                ok=False,
                returncode=proc.returncode,
                error=(proc.stderr or "").strip(),
            )
        return AgentResult(ok=True, text=(proc.stdout or "").strip(), returncode=0)


# engine -> Runner クラス。codex/gemini を足すときはここに 1 行登録する。
RUNNERS: dict[str, type[AgentRunner]] = {
    "claude-code": ClaudeSubprocessRunner,
    "codex": CodexSubprocessRunner,
}


def resolve_runner(engine: str | None = None) -> AgentRunner:
    """engine 名から Runner を解決する。未対応 engine は ValueError で落とす。"""
    key = engine or os.environ.get("GARDEN_GAKU_CO_ENGINE", "claude-code")
    cls = RUNNERS.get(key)
    if cls is None:
        raise UnsupportedEngineError(key, supported_engines())
    return cls()
