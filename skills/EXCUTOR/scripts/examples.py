"""
examples.py — Usage examples for SecureExecutor and the agent tool.

1. Direct Python usage
2. Simulated Anthropic tool_use loop (no live API call needed)
3. How to wire into a real Anthropic messages call
"""

from __future__ import annotations

import json

# ──────────────────────────────────────────────
# Example 1: Direct usage
# ──────────────────────────────────────────────

print("=" * 60)
print("EXAMPLE 1 — Direct executor usage")
print("=" * 60)

from secure_executor import ExecutionConfig, SecureExecutor

executor = SecureExecutor()

snippets = [
    # Normal computation
    "import math; print(math.factorial(10))",
    # Blocked import attempt
    "import subprocess; subprocess.run(['whoami'])",
    # Timeout
    "while True: pass",
    # Network blocked
    "import socket; socket.gethostbyname('google.com')",
    # File write inside sandbox
    """
import os, tempfile
p = os.path.join(os.environ['TEMP'], 'out.txt')
open(p, 'w').write('data')
print('wrote', p)
""",
]

for snippet in snippets:
    cfg_override = ExecutionConfig(timeout_seconds=2)
    r = SecureExecutor(cfg_override).run(snippet)
    print(f"\nCode   : {snippet.strip()[:60]!r}")
    print(f"Success: {r.success}")
    if r.stdout:
        print(f"Stdout : {r.stdout.strip()}")
    if r.stderr:
        print(f"Stderr : {r.stderr.strip()[:120]}")
    if r.timed_out:
        print("  ⚠ TIMED OUT")


# ──────────────────────────────────────────────
# Example 2: Simulated Anthropic tool_use loop
# ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("EXAMPLE 2 — Simulated Anthropic tool_use dispatch")
print("=" * 60)

from agent_tool import TOOL_DEFINITION, dispatch_tool_call

# Mimic what the model would send back as a tool_use block
simulated_tool_use_blocks = [
    {
        "type": "tool_use",
        "id": "toolu_01",
        "name": "run_python",
        "input": {
            "code": "nums = list(range(1, 11))\nprint(sum(nums))",
        },
    },
    {
        "type": "tool_use",
        "id": "toolu_02",
        "name": "run_python",
        "input": {
            "code": "import requests",  # blocked
        },
    },
]

for block in simulated_tool_use_blocks:
    print(f"\nTool call id : {block['id']}")
    print(f"Input code   : {block['input']['code'].strip()!r}")
    result_json = dispatch_tool_call(block["name"], block["input"])
    result = json.loads(result_json)
    print(f"success      : {result['success']}")
    print(f"stdout       : {result['stdout'].strip()!r}")
    if result["stderr"]:
        print(f"stderr       : {result['stderr'].strip()[:120]!r}")
    if result["static_violations"]:
        print(f"violations   : {result['static_violations']}")


# ──────────────────────────────────────────────
# Example 3: Real Anthropic API integration sketch
# ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("EXAMPLE 3 — Real Anthropic API integration (pseudo-code)")
print("=" * 60)

INTEGRATION_SKETCH = """
import anthropic
from agent_tool import TOOL_DEFINITION, dispatch_tool_call

client = anthropic.Anthropic()

messages = [{"role": "user", "content": "Calculate the 15th Fibonacci number in Python."}]

while True:
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        tools=[TOOL_DEFINITION],
        messages=messages,
    )

    # Append assistant turn
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason != "tool_use":
        # Final text answer — print and exit
        for block in response.content:
            if block.type == "text":
                print(block.text)
        break

    # Process all tool_use blocks in this turn
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result_str = dispatch_tool_call(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str,
            })

    # Feed results back
    messages.append({"role": "user", "content": tool_results})
"""

print(INTEGRATION_SKETCH)

print("=" * 60)
print("Tool schema (for reference):")
print(json.dumps(TOOL_DEFINITION, indent=2))