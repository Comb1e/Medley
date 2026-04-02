import os
import json
import numpy as np
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer

from config import config
from custom_tools.verification import check_env_vars

VECTOR_MEMORY_REQUIRED_ENV_VARS = [
    "EMBEDDINGS_MODEL_NAME"
]
check_env_vars(VECTOR_MEMORY_REQUIRED_ENV_VARS)

class VectorMemory:
    def __init__(self, need_index, ss, logs_dir=config.MEMORY_PATH, days_to_index=7):
        self.logs_dir = logs_dir
        self.days_to_index = days_to_index
        self.searcher = ss
        if need_index:
            self._index_recent_days()

    # ── Path helpers ───────────────────────────────────────────────────────────

    def _day_dir(self, date) -> str:
        """Return logs/YYYY-MM-DD/ for a given date."""
        return os.path.join(self.logs_dir, date.strftime("%Y-%m-%d"))

    def _raw_path(self, date) -> str:
        """Return logs/YYYY-MM-DD/raw_memories.jsonl — read-only, never written."""
        return os.path.join(self._day_dir(date), "raw_memories.jsonl")

    def _embeddings_path(self, date) -> str:
        """Return logs/YYYY-MM-DD/embeddings.npy — only file VectorMemory writes."""
        return os.path.join(self._day_dir(date), "embeddings.npy")

    # ── Raw log reader ─────────────────────────────────────────────────────────

    def _load_raw_records(self, date) -> list[dict]:
        """
        Read logs/YYYY-MM-DD/raw_memories.jsonl.
        Each line: {"timestamp": "...", "role": "user"|"assistant", "content": "..."}
        Malformed or unrecognised lines are silently skipped.
        """
        path = self._raw_path(date)
        if not os.path.exists(path):
            return []

        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if (isinstance(entry, dict)
                            and entry.get("role") in ("user", "assistant")
                            and str(entry.get("content", "")).strip()):
                        records.append(entry)
                except json.JSONDecodeError:
                    continue
        return records

    def _records_to_texts(self, records: list[dict]) -> list[str]:
        """
        Convert validated raw records into memory strings.
        Consecutive user → assistant pairs are merged into one unit:
            "User: <content>\\nAssistant: <content>"
        Unpaired messages are kept as single-role strings.
        """
        texts = []
        i = 0
        while i < len(records):
            cur = records[i]
            if (cur["role"] == "user"
                    and i + 1 < len(records)
                    and records[i + 1]["role"] == "assistant"):
                texts.append(
                    f"User: {cur['content']}\n"
                    f"Assistant: {records[i + 1]['content']}"
                )
                i += 2
            else:
                label = "User" if cur["role"] == "user" else "Assistant"
                texts.append(f"{label}: {cur['content']}")
                i += 1
        return texts

    def _load_raw_texts(self, date) -> list[str]:
        """Load raw_memories.jsonl for a date and return paired memory strings."""
        return self._records_to_texts(self._load_raw_records(date))

    # ── Vector cache helpers ───────────────────────────────────────────────────

    def _load_vector_cache(self, date) -> tuple[list[str], np.ndarray] | tuple[None, None]:
        """
        Return (texts, matrix) when a fresh embeddings.npy exists and its
        row count matches the texts derived from raw_memories.jsonl.
        Returns (None, None) on miss, corruption, or staleness.
        """
        embeddings_path = self._embeddings_path(date)
        if not os.path.exists(embeddings_path):
            return None, None

        try:
            matrix = np.load(embeddings_path)          # (N, D)
        except Exception:
            return None, None

        texts = self._load_raw_texts(date)

        if matrix.shape[0] != len(texts):
            print(f"[VectorMemory] Stale cache on {date.date()} "
                  f"({matrix.shape[0]} rows vs {len(texts)} texts), re-encoding.")
            return None, None

        return texts, matrix

    def _save_embeddings(self, date, matrix: np.ndarray):
        """Write embeddings.npy — the only file VectorMemory ever creates."""
        day_dir = self._day_dir(date)
        os.makedirs(day_dir, exist_ok=True)
        np.save(self._embeddings_path(date), matrix)

    # ── Indexing pipeline ──────────────────────────────────────────────────────

    def _index_day(self, date):
        """
        For one calendar date:
          1. Try embeddings.npy cache — fast path if row count matches raw texts.
          2. On miss/staleness, read raw_memories.jsonl → encode → save embeddings.npy.
          3. Load into SemanticSearch via load_library() (cache) or add_to_library() (new).
        """
        texts, matrix = self._load_vector_cache(date)

        if texts is None:
            texts = self._load_raw_texts(date)
            if not texts:
                return

            print(f"[VectorMemory] Encoding {len(texts)} memories "
                  f"for {date.date()} ...")
            # Use SemanticSearch's own model to encode so embeddings stay consistent
            matrix = self.searcher.model.encode(texts, convert_to_numpy=True)
            self._save_embeddings(date, matrix)
        else:
            print(f"[VectorMemory] Cache hit — {len(texts)} memories "
                  f"from {date.date()}")

        # Extend the shared vector library directly
        for text, embedding in zip(texts, matrix):
            self.searcher.vector_library.append((text, embedding))

    def _index_recent_days(self):
        """Walk the last `days_to_index` days and populate the SemanticSearch library."""
        today = datetime.now()
        for offset in range(self.days_to_index):
            self._index_day(today - timedelta(days=offset))

        print(f"\n[VectorMemory] Ready — {len(self.searcher.vector_library)} memories "
              f"indexed over the last {self.days_to_index} days.\n")

    # ── Public API ─────────────────────────────────────────────────────────────

    def store(self, role: str, content: str):
        """
        Encode a new role/content record, add to the SemanticSearch library,
        and append a new row to today's embeddings.npy.
        raw_memories.jsonl is NEVER written here — it is owned externally.
        """
        label = "User" if role == "user" else "Assistant"
        text = f"{label}: {content}"
        # add_to_library encodes and appends to vector_library in one call
        self.searcher.add_to_library([text])

        # Persist the new embedding row to today's .npy
        today = datetime.now()
        new_embedding = self.searcher.vector_library[-1][1]  # just-added embedding
        embeddings_path = self._embeddings_path(today)
        os.makedirs(self._day_dir(today), exist_ok=True)

        if os.path.exists(embeddings_path):
            existing = np.load(embeddings_path)
            updated = np.vstack([existing, new_embedding[np.newaxis, :]])
        else:
            updated = new_embedding[np.newaxis, :]
        np.save(embeddings_path, updated)

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """
        Return the top-k most semantically similar memories to the query.
        Delegates entirely to SemanticSearch.query().
        """
        if not self.searcher.vector_library:
            return []
        results = self.searcher.query(query, top_k=top_k)
        return [r["text"] for r in results]


class SemanticAgent:
    def __init__(self, need_index, ss, days_to_index=7):
        self.memory = VectorMemory(ss=ss, need_index=need_index, days_to_index=days_to_index)

    def get_relevant(self, user_input: str, top_k: int = 3):
        return self.memory.retrieve(user_input, top_k)

    def store(self, user_input: str, reply: str):
        self.memory.store("user", user_input)
        self.memory.store("assistant", reply)

    def show_index_stats(self):
        mem = self.memory
        print(f"\n── Vector Index Stats ──────────────────")
        print(f"  Total memories : {len(mem.memories)}")
        print(f"  Days indexed   : {mem.days_to_index}")
        print(f"  Embedding dim  : "
              f"{mem.embeddings[0].shape[0] if mem.embeddings else 'N/A'}")
        print(f"  Logs root      : {mem.logs_dir}/YYYY-MM-DD/")
        print(f"────────────────────────────────────────\n")


# ── Example usage ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = SemanticAgent(days_to_index=7)

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        if user_input.lower() == "/stats":
            agent.show_index_stats()
            continue

        reply = agent.chat(user_input)
        print(f"Agent: {reply}\n")