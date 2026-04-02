import os
import json
from datetime import datetime
from config import config
from pathlib import Path
from collections import deque
from small_agents.semantic_agent import SemanticAgent
class InMemory:
    def __init__(self, ss, max_history=10, logs_dir=config.MEMORY_PATH):
        self.max_history = max_history
        self.logs_dir = Path(logs_dir) / datetime.now().strftime("%Y-%m-%d")
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs_dir / "raw_memories.jsonl"
        self.agent = SemanticAgent(ss=ss, need_index=False)

        # 2. This list buffers all new messages in THIS session
        self.session_history = deque()  # use deque for FIFO

    # ── Storage helpers ────────────────────────────────────────────────────────

    def _save_message(self, role: str, content: str):
        """Buffer a new message (not writing to disk yet)."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        }
        self.session_history.append(record)
        # After every 10 new messages (not total), flush to disk
        if len(self.session_history) >= self.max_history:
            self.flush_session_history()

    def flush_session_history(self):
        """Write all new (not previously loaded) messages to disk and clear session buffer."""
        if len(self.session_history) > self.max_history:
            to_save = self.session_history.popleft()  # remove oldest
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(to_save, ensure_ascii=False) + "\n")

    def flush_all_memories(self):
        """
        At the end of a dialog box, flush all new in-memory messages to disk.
        Only write messages from current session, not re-saving past loaded logs.
        """
        while self.session_history:
            to_save = self.session_history.popleft()
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(to_save, ensure_ascii=False) + "\n")

    # ── Utility ────────────────────────────────────────────────────────────────

    def show_history(self):
        """Pretty-print combined (loaded + session) history."""
        print("\n── Full Memory Window ──")
        # Show past + current (does not duplicate)
        all_history = [
            {'role': d['role'], 'content': d['content']}
            for d in self.session_history
        ]
        for msg in all_history:
            label = "User" if msg["role"] == "user" else "Assistant"
            print(f"[{label}] {msg['content'][:120]}")
        print("───────────────────────────\n")

    def store(self, user_input: str, reply: str):
        self._save_message("user", user_input)
        self._save_message("assistant", reply)
        self.agent.store(user_input, reply)

    def get_session_history(self):
        return self.session_history
