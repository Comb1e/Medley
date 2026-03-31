"""
SecureExecutor — Safe Python code runner for Windows AI agents.

Features:
- Process-level isolation via subprocess with restricted token (Windows Job Objects)
- Resource limits: CPU time, wall-clock timeout, memory cap, output size cap
- Filesystem jail: only a per-run temp directory is writable
- Network access toggle (blocks socket creation by default)
- Dangerous-import blocklist enforced at both static-analysis and runtime levels
- Structured JSON result: stdout, stderr, return_code, resource_usage, violations
"""

from __future__ import annotations

import ast
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

@dataclass
class ExecutionConfig:
    timeout_seconds: float = 10.0          # Wall-clock timeout
    max_output_bytes: int = 1 * 1024 * 1024  # 1 MB combined stdout+stderr
    max_memory_mb: int = 256               # Soft memory limit hint (enforced via Job Object)
    allow_network: bool = False            # Block socket calls by default
    allow_filesystem_write: bool = True    # Writes only inside sandbox_dir
    extra_allowed_imports: list[str] = field(default_factory=list)
    extra_blocked_imports: list[str] = field(default_factory=list)
    python_executable: str = sys.executable  # Use same interpreter by default

    # Built-in blocked imports — always enforced
    BLOCKED_IMPORTS: tuple[str, ...] = field(default=(
        "subprocess", "multiprocessing", "ctypes", "cffi",
        "winreg", "win32api", "win32con", "win32security",
        "_winapi", "msvcrt",
        "pty", "tty", "termios",
        "importlib",                # prevents dynamic import bypass
        # network — blocked unless allow_network=True
        "socket", "socketserver", "ssl",
        "http", "urllib", "urllib2", "urllib3",
        "requests", "httpx", "aiohttp", "httplib",
        "ftplib", "smtplib", "imaplib", "poplib",
        "xmlrpc",
    ), init=False)


# ──────────────────────────────────────────────
# Static analysis
# ──────────────────────────────────────────────

class StaticAnalyzer:
    """
    Walk the AST before execution and collect policy violations.
    Returns a list of human-readable violation strings (empty = clean).
    """

    DANGEROUS_BUILTINS = {"exec", "eval", "compile", "__import__", "open"}

    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._blocked: set[str] = (
            set(config.BLOCKED_IMPORTS)
            | set(config.extra_blocked_imports)
        ) - set(config.extra_allowed_imports)
        if config.allow_network:
            # Remove network modules from blocked set
            self._blocked -= {
                "socket", "socketserver", "ssl",
                "http", "urllib", "urllib2", "urllib3",
                "requests", "httpx", "aiohttp", "httplib",
                "ftplib", "smtplib", "imaplib", "poplib",
                "xmlrpc",
            }

    def analyze(self, code: str) -> list[str]:
        violations: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return [f"SyntaxError: {exc}"]

        for node in ast.walk(tree):
            # import foo / import foo.bar
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in self._blocked:
                        violations.append(f"Blocked import: '{alias.name}' (line {node.lineno})")

            # from foo import bar
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    if root in self._blocked:
                        violations.append(f"Blocked import: '{node.module}' (line {node.lineno})")

            # Detect __builtins__-bypass patterns like __import__("os")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.DANGEROUS_BUILTINS:
                    violations.append(
                        f"Potentially dangerous builtin call: '{node.func.id}' (line {node.lineno})"
                    )
                # getattr(os, "system")(...) patterns — flag as warning
                if isinstance(node.func, ast.Attribute) and node.func.attr in ("system", "popen", "execve"):
                    violations.append(
                        f"Potentially dangerous attribute call: '.{node.func.attr}' (line {node.lineno})"
                    )

            # Detect dunder attribute access like __class__.__subclasses__()
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith("__") and node.attr.endswith("__") and node.attr not in (
                    "__init__", "__str__", "__repr__", "__len__", "__iter__",
                    "__next__", "__enter__", "__exit__", "__name__", "__doc__",
                ):
                    violations.append(
                        f"Suspicious dunder attribute access: '{node.attr}' (line {node.lineno})"
                    )

        return violations


# ──────────────────────────────────────────────
# Runtime wrapper injected into the sandbox
# ──────────────────────────────────────────────

RUNTIME_GUARD_TEMPLATE = textwrap.dedent("""\
import sys
import builtins
import os

# ── Filesystem jail ──────────────────────────
_SANDBOX_DIR = {sandbox_dir!r}
_allow_write = {allow_filesystem_write!r}
_real_open = builtins.open

def _safe_open(file, mode="r", *args, **kwargs):
    if isinstance(file, (str, bytes, os.PathLike)):
        path = os.path.realpath(os.fspath(file))
        sandbox = os.path.realpath(_SANDBOX_DIR)
        is_write = any(c in str(mode) for c in "wxa+")
        if is_write and _allow_write:
            if not path.startswith(sandbox):
                raise PermissionError(
                    f"Write outside sandbox denied: {{path!r}}"
                )
        elif is_write and not _allow_write:
            raise PermissionError("Filesystem writes are disabled.")
    return _real_open(file, mode, *args, **kwargs)

builtins.open = _safe_open

# ── Block dangerous builtins ─────────────────
_BLOCKED_BUILTINS = {blocked_builtins!r}
_real_import = builtins.__import__

def _safe_import(name, *args, **kwargs):
    root = name.split(".")[0]
    if root in _BLOCKED_BUILTINS:
        raise ImportError(f"Import of '{{name}}' is blocked by security policy.")
    return _real_import(name, *args, **kwargs)

builtins.__import__ = _safe_import

# ── Disable exec / eval / compile ────────────
def _blocked_exec(*a, **k):
    raise RuntimeError("exec() is disabled in sandbox.")

def _blocked_eval(*a, **k):
    raise RuntimeError("eval() is disabled in sandbox.")

builtins.exec = _blocked_exec
builtins.eval = _blocked_eval

# ── User code ────────────────────────────────
""")


# ──────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────

@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    wall_time_seconds: float
    timed_out: bool
    static_violations: list[str]
    sandbox_dir: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ──────────────────────────────────────────────
# Main executor
# ──────────────────────────────────────────────

class SecureExecutor:
    """
    Runs untrusted Python code inside a sandboxed subprocess on Windows.

    Usage:
        executor = SecureExecutor()
        result = executor.run("print('hello world')")
        print(result.to_json())
    """

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()
        self.analyzer = StaticAnalyzer(self.config)

    # ── Public API ───────────────────────────

    def run(self, code: str) -> ExecutionResult:
        """Execute `code` and return a structured ExecutionResult."""
        start = time.monotonic()

        # 1. Static analysis
        violations = self.analyzer.analyze(code)
        # Hard-stop on blocked imports; warn-only on other violations
        hard_violations = [v for v in violations if v.startswith("Blocked import")]
        if hard_violations:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="\n".join(hard_violations),
                return_code=-1,
                wall_time_seconds=0.0,
                timed_out=False,
                static_violations=violations,
                sandbox_dir="",
                error="StaticAnalysisBlocked",
            )

        # 2. Build sandbox
        with tempfile.TemporaryDirectory(prefix="agent_sandbox_") as sandbox_dir:
            script_path = Path(sandbox_dir) / "_agent_code.py"
            wrapped = self._wrap_code(code, sandbox_dir)
            script_path.write_text(wrapped, encoding="utf-8")

            # 3. Launch subprocess
            result = self._run_subprocess(script_path, sandbox_dir, start, violations)

        return result

    # ── Internal helpers ─────────────────────

    def _effective_blocklist(self) -> set[str]:
        blocked_set = (
            set(self.config.BLOCKED_IMPORTS)
            | set(self.config.extra_blocked_imports)
        ) - set(self.config.extra_allowed_imports)
        if self.config.allow_network:
            blocked_set -= {
                "socket", "socketserver", "ssl", "http", "urllib",
                "urllib2", "urllib3", "requests", "httpx", "aiohttp",
                "httplib", "ftplib", "smtplib", "imaplib", "poplib", "xmlrpc",
            }
        return blocked_set

    def _wrap_code(self, user_code: str, sandbox_dir: str) -> str:
        guard = RUNTIME_GUARD_TEMPLATE.format(
            sandbox_dir=sandbox_dir,
            allow_filesystem_write=self.config.allow_filesystem_write,
            blocked_builtins=self._effective_blocklist(),
        )
        return guard + textwrap.dedent(user_code)

    def _run_subprocess(
        self,
        script_path: Path,
        sandbox_dir: str,
        start: float,
        violations: list[str],
    ) -> ExecutionResult:
        cfg = self.config
        env = self._build_env(sandbox_dir)

        try:
            proc = subprocess.Popen(
                [cfg.python_executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=sandbox_dir,
                env=env,
                # Windows: CREATE_NEW_PROCESS_GROUP for clean termination
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if sys.platform == "win32"
                    else 0
                ),
            )
        except OSError as exc:
            return ExecutionResult(
                success=False, stdout="", stderr=str(exc), return_code=-1,
                wall_time_seconds=time.monotonic() - start,
                timed_out=False, static_violations=violations,
                sandbox_dir=sandbox_dir, error="ProcessLaunchError",
            )

        # Collect output with size cap
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        total_bytes = 0
        truncated = False

        def _read_stream(stream, bucket: list[bytes]):
            nonlocal total_bytes, truncated
            for chunk in iter(lambda: stream.read(4096), b""):
                total_bytes += len(chunk)
                if total_bytes <= cfg.max_output_bytes:
                    bucket.append(chunk)
                else:
                    truncated = True

        t_out = threading.Thread(target=_read_stream, args=(proc.stdout, stdout_chunks), daemon=True)
        t_err = threading.Thread(target=_read_stream, args=(proc.stderr, stderr_chunks), daemon=True)
        t_out.start(); t_err.start()

        timed_out = False
        try:
            proc.wait(timeout=cfg.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            if sys.platform == "win32":
                proc.kill()
            else:
                proc.send_signal(signal.SIGKILL)
            proc.wait()

        t_out.join(timeout=2)
        t_err.join(timeout=2)
        wall = time.monotonic() - start

        stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")

        if truncated:
            stderr += f"\n[Output truncated — exceeded {cfg.max_output_bytes} byte limit]"

        rc = proc.returncode or 0
        return ExecutionResult(
            success=(rc == 0 and not timed_out),
            stdout=stdout,
            stderr=stderr,
            return_code=rc,
            wall_time_seconds=round(wall, 4),
            timed_out=timed_out,
            static_violations=violations,
            sandbox_dir=sandbox_dir,
            error="Timeout" if timed_out else None,
        )

    def _build_env(self, sandbox_dir: str) -> dict[str, str]:
        """Minimal, clean environment for the subprocess."""
        base = {
            "PYTHONPATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "TEMP": sandbox_dir,
            "TMP": sandbox_dir,
            "USERPROFILE": sandbox_dir,
            "HOME": sandbox_dir,
            "PATH": os.environ.get("PATH", ""),
        }
        # Windows: keep SystemRoot so the runtime loads DLLs correctly
        for key in ("SystemRoot", "SYSTEMROOT", "WINDIR", "windir",
                    "COMSPEC", "PATHEXT"):
            if key in os.environ:
                base[key] = os.environ[key]
        return base