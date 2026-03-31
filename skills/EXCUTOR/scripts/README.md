# SecureExecutor — Safe Python Runner for Windows AI Agents

A production-ready tool that lets AI agents execute arbitrary Python code on a
Windows host while enforcing strict security boundaries.

---

## Files

| File | Purpose |
|---|---|
| `secure_executor.py` | Core sandbox engine — static analysis + subprocess isolation |
| `agent_tool.py` | Agent-facing tool definition (Anthropic tool schema + dispatcher) |
| `windows_job_object.py` | Windows Job Object helper for hard memory caps |
| `tests.py` | Full test suite |
| `examples.py` | Usage examples including Anthropic API loop |

---

## Quick Start

```python
from secure_executor import SecureExecutor

executor = SecureExecutor()
result = executor.run("print(2 ** 32)")
print(result.to_json())
```

---

## Security Layers

### 1 — Static Analysis (before execution)
The AST is walked before any code runs. Violations cause immediate rejection:
- **Blocked imports** (`subprocess`, `ctypes`, `winreg`, `socket`, `importlib`, …)
- **Dangerous builtins** (`exec`, `eval`, `compile`, `__import__`)
- **Suspicious dunder access** (`__subclasses__`, `__globals__`, …)
- **OS escape patterns** (`.system()`, `.popen()`, `.execve()`)

### 2 — Runtime Guard (injected into every script)
A security preamble is prepended to user code that:
- Replaces `builtins.open` with a jail wrapper — writes only to the per-run `TEMP` dir
- Replaces `builtins.__import__` with a runtime blocklist check
- Disables `exec` / `eval` / `compile` entirely

### 3 — Process Isolation (subprocess)
- Code runs in a **child subprocess**, not the agent's own process
- Subprocess `env` is stripped to a minimal safe set; `HOME`/`USERPROFILE`/`TEMP` all
  point to the sandbox directory
- `CREATE_NEW_PROCESS_GROUP` on Windows for clean kill on timeout

### 4 — Resource Limits
| Resource | Mechanism | Default |
|---|---|---|
| Wall-clock time | `proc.wait(timeout=…)` → `proc.kill()` | 10 s |
| Output size | Streaming byte counter | 1 MB |
| Memory (hard) | Windows Job Object (`windows_job_object.py`) | 256 MB |

### 5 — Filesystem Jail
- The sandbox directory (`tempfile.TemporaryDirectory`) is the **only** writable location
- Any `open(..., 'w')` outside it raises `PermissionError` at runtime
- The entire sandbox is deleted automatically when the run completes

---

## Configuration

```python
from secure_executor import ExecutionConfig, SecureExecutor

config = ExecutionConfig(
    timeout_seconds=30,
    max_output_bytes=2 * 1024 * 1024,   # 2 MB
    max_memory_mb=512,
    allow_network=True,                  # unblock socket etc.
    allow_filesystem_write=False,        # read-only mode
    extra_blocked_imports=["pandas"],    # add to blocklist
    extra_allowed_imports=["socket"],    # remove from blocklist
)
executor = SecureExecutor(config)
```

---

## Agent Integration

### Anthropic tool_use

```python
from agent_tool import TOOL_DEFINITION, dispatch_tool_call

# Register TOOL_DEFINITION in your client.messages.create(tools=[...]) call.
# When stop_reason == "tool_use":
result_json = dispatch_tool_call(block.name, block.input)
# Return result_json as the tool_result content.
```

See `examples.py` for a complete agentic loop.

---

## Running Tests

```
python tests.py
```

All tests pass on Python 3.10+, Windows 10/11, and Linux (Job Object features
gracefully degrade on non-Windows platforms).

---

## What is NOT protected

- **CPU-intensive code that completes before the timeout** — the wall-clock limit
  is the primary CPU guard; for tighter CPU accounting consider Windows Job Object
  `PerJobUserTimeLimit`.
- **Side-channels via allowed stdlib modules** — `os.getcwd()`, `os.listdir()`,
  `pathlib.Path.read_text()` are intentionally allowed for read operations.
- **Compiled extensions** — if a `.pyd`/`.so` in `sys.path` provides a syscall
  wrapper, it will bypass import-level checks. Mitigate by restricting `sys.path`
  or running in a dedicated virtualenv.