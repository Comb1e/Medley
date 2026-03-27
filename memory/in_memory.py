import os
import json
from datetime import datetime

from config import config

class in_memory:
    def __init__(self, max_history=10, logs_dir=config.MEMORY_LOGS_PATH):
        self.max_history = max_history
        self.logs_dir = logs_dir / datetime.now().strftime("%Y-%m-%d")
        if self.logs_dir.exists() == False:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        self.history = self._load_latest_records()

    # ── Storage helpers ────────────────────────────────────────────────────────

    def _log_path(self) -> str:
        """Return the log file path for a given date, e.g. logs/2024-03-26.jsonl"""
        return os.path.join(self.logs_dir, "raw_memories.jsonl")

    def _save_message(self, role: str, content: str):
        """Append a single message with timestamp to today's log file."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        }
        with open(self._log_path(), "a", encoding="utf-8") as f:
            print(self._log_path())
            f.write(json.dumps(record) + "\n")

    def _load_latest_records(self) -> list[dict]:
        """
        Read log files from newest to oldest until we collect
        the latest `max_history` messages. Returns them in
        chronological order (oldest → newest).
        """
        # Collect and sort all .jsonl files, newest first
        log_files = sorted(
            [f for f in os.listdir(self.logs_dir) if f.endswith(".jsonl")],
            reverse=True
        )
        records = []
        for filename in log_files:
            path = os.path.join(self.logs_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Parse each line, skip malformed ones
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    records.append({"role": entry["role"], "content": entry["content"]})
                except (json.JSONDecodeError, KeyError):
                    continue

                if len(records) >= self.max_history:
                    break

            if len(records) >= self.max_history:
                break

        # Reverse so oldest → newest (correct chat order)
        records.reverse()
        print(f"[In-Memory] Loaded {len(records)} messages from logs.")
        return records

    # ── Utility ────────────────────────────────────────────────────────────────

    def show_history(self):
        """Pretty-print the current in-memory history."""
        print("\n── Current Memory Window ──")
        for msg in self.history:
            label = "User" if msg["role"] == "user" else "Assistant"
            print(f"[{label}] {msg['content'][:120]}")
        print("───────────────────────────\n")

    def store(self, user_input: str, reply: str):
        self._save_message("user", user_input)
        self._save_message("assistant", reply)
