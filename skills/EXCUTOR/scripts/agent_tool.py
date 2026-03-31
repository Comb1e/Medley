"""
agent_tool.py — Drop-in tool definition for AI agent frameworks.

Exposes `run_python_tool` as both:
  - A plain Python function agents can call directly
  - An Anthropic-compatible tool schema (TOOL_DEFINITION)

Supports Anthropic tool_use, LangChain, and any function-calling framework.
"""

from __future__ import annotations

import json
from typing import Any

from secure_executor import ExecutionConfig, ExecutionResult, SecureExecutor

# ──────────────────────────────────────────────
# Anthropic / OpenAI-style tool schema
# ──────────────────────────────────────────────

TOOL_DEFINITION: dict[str, Any] = {
    "name": "run_python",
    "description": (
        "Execute a Python code snippet in a secure, isolated sandbox on the host "
        "Windows machine. Returns stdout, stderr, return code, and execution time. "
        "Filesystem writes are restricted to a per-run temp directory. "
        "Network access and dangerous system imports are blocked by default. "
        "Use this tool to perform calculations, data manipulation, file parsing, "
        "or any task expressible in Python that does not require external network calls."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Valid Python source code to execute.",
            },
            "timeout_seconds": {
                "type": "number",
                "description": "Maximum wall-clock seconds allowed (default 10, max 60).",
                "default": 10,
                "minimum": 1,
                "maximum": 60,
            },
            "allow_network": {
                "type": "boolean",
                "description": "If true, socket-based imports are allowed. Default false.",
                "default": False,
            },
            "max_output_kb": {
                "type": "integer",
                "description": "Maximum combined stdout+stderr in KB (default 1024).",
                "default": 1024,
                "minimum": 1,
                "maximum": 10240,
            },
        },
        "required": ["code"],
    },
}


# ──────────────────────────────────────────────
# Callable tool function
# ──────────────────────────────────────────────

def run_python_tool(
    code: str,
    timeout_seconds: float = 10.0,
    allow_network: bool = False,
    max_output_kb: int = 1024,
) -> dict[str, Any]:
    """
    Execute Python code in the secure sandbox.

    Returns a dict suitable for returning as a tool_result to an AI agent.
    The dict contains:
      - success (bool)
      - stdout (str)
      - stderr (str)
      - return_code (int)
      - wall_time_seconds (float)
      - timed_out (bool)
      - static_violations (list[str])
      - error (str | None)
    """
    config = ExecutionConfig(
        timeout_seconds=min(float(timeout_seconds), 60.0),
        max_output_bytes=min(int(max_output_kb), 10240) * 1024,
        allow_network=bool(allow_network),
    )
    executor = SecureExecutor(config)
    result: ExecutionResult = executor.run(code)
    return result.to_dict()


def dispatch_tool_call(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    Entry point for agent frameworks that pass (tool_name, tool_input) pairs.
    Returns a JSON string to be sent back as the tool_result content.
    """
    if tool_name != "run_python":
        return json.dumps({"error": f"Unknown tool: {tool_name!r}"})

    result = run_python_tool(
        code=tool_input.get("code", ""),
        timeout_seconds=tool_input.get("timeout_seconds", 10.0),
        allow_network=tool_input.get("allow_network", False),
        max_output_kb=tool_input.get("max_output_kb", 1024),
    )
    return json.dumps(result, indent=2)