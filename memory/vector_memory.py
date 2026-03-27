import os
import json
import numpy as np
import anthropic
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
from config import config

class VectorMemory:
    def __init__(self, logs_dir=config.MEMORY_LOGS_PATH, days_to_index=7):
        self.logs_dir = logs_dir
        self.days_to_index = days_to_index
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # In-memory index populated from the last 7 days on startup
        self.memories: list[str] = []
        self.embeddings: list[np.ndarray] = []

        self.memory_conv_ids: list[int] = []   # ← conversation index per memory
        self.current_conv_id: int = 0          # ← incremented on each store() pair

        self._index_recent_days()

    # ── Path helpers ───────────────────────────────────────────────────────────

    def _day_dir(self, date) -> str:
        """Return logs/YYYY-MM-DD/ for a given date."""
        return os.path.join(self.logs_dir, date.strftime("%Y-%m-%d"))

    def _raw_path(self, date) -> str:
        """Return logs/YYYY-MM-DD/raw_memories.jsonl — read-only, never written."""
        return os.path.join(self._day_dir(date), "raw_memories.jsonl")

    def _embeddings_path(self, date) -> str:
        """Return logs/YYYY-MM-DD/embeddings.npy — only cache file written."""
        return os.path.join(self._day_dir(date), "embeddings.npy")

    # ── Raw log reader ─────────────────────────────────────────────────────────

    def _load_raw_records(self, date) -> list[dict]:
        """
        Read logs/YYYY-MM-DD/raw_memories.jsonl and return validated records.

        Each line must match:
            {"timestamp": "...", "role": "user"|"assistant", "content": "..."}

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

    def _records_to_texts(self, records: list[dict], base_conv_id: int = 0) -> list[str]:
        """
        Convert validated raw records into memory strings.

        Consecutive user → assistant pairs are merged into one unit:
            "User: <content>\nAssistant: <content>"

        Unpaired messages are kept as single-role strings.
        """
        texts = []
        conv_ids = []
        conv_id = base_conv_id
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
                conv_ids.append(conv_id)
                conv_id += 1
                i += 2
            else:
                label = "User" if cur["role"] == "user" else "Assistant"
                texts.append(f"{label}: {cur['content']}")
                conv_ids.append(conv_id)
                i += 1
        return texts, conv_ids

    def _load_raw_texts(self, date) -> list[str]:
        """Load raw_memories.jsonl for a date and return paired memory strings."""
        records = self._load_raw_records(date)
        # Use total known conversations so far as the base offset
        base = self.current_conv_id
        texts, conv_ids = self._records_to_texts(records, base_conv_id=base)
        return texts, conv_ids

    # ── Vector cache helpers ───────────────────────────────────────────────────

    def _cache_is_fresh(self, date) -> bool:
        """
        Return True when embeddings.npy exists and its row count matches
        the number of memory strings derivable from raw_memories.jsonl.
        A mismatch means new records were appended since last encoding.
        """
        embeddings_path = self._embeddings_path(date)
        if not os.path.exists(embeddings_path):
            return False

        try:
            matrix = np.load(embeddings_path)
        except Exception:
            return False

        expected = len(self._load_raw_texts(date))
        return matrix.shape[0] == expected

    def _load_vector_cache(self, date):
        """
        Return (texts, matrix) when a fresh cache exists,
        or (None, None) on cache miss or staleness.
        """
        embeddings_path = self._embeddings_path(date)
        if not os.path.exists(embeddings_path):
            return None, None, None

        try:
            matrix = np.load(embeddings_path)          # (N, D)
        except Exception:
            return None, None, None

        # Re-derive texts directly from raw_memories.jsonl (no index.json)
        texts, conv_ids = self._load_raw_texts(date)

        if matrix.shape[0] != len(texts):
            print(f"[VectorMemory] Stale cache on {date.date()}, re-encoding.")
            return None, None, None

        return texts, matrix, conv_ids

    def _save_embeddings(self, date, matrix: np.ndarray):
        """Write embeddings.npy — the only file VectorMemory ever creates."""
        day_dir = self._day_dir(date)
        os.makedirs(day_dir, exist_ok=True)
        np.save(self._embeddings_path(date), matrix)

    # ── Indexing pipeline ──────────────────────────────────────────────────────

    def _index_day(self, date):
        """
        For one calendar date:
          1. Try embeddings.npy cache — if row count matches raw texts, fast path.
          2. On miss/staleness, read raw_memories.jsonl → encode → save embeddings.npy.
          3. Extend the live in-memory index.
        """
        texts, matrix, conv_ids = self._load_vector_cache(date)

        if texts is None:
            texts, conv_ids = self._load_raw_texts(date)
            if not texts:
                return

            print(f"[VectorMemory] Encoding {len(texts)} memories "
                  f"for {date.date()} ...")
            matrix = self.model.encode(texts, show_progress_bar=False)
            self._save_embeddings(date, matrix)
        else:
            print(f"[VectorMemory] Cache hit — {len(texts)} memories "
                  f"from {date.date()}")

        self.memories.extend(texts)
        self.embeddings.extend(matrix)                 # list of 1-D arrays
        self.memory_conv_ids.extend(conv_ids)
        # Advance the global counter to after all conversations loaded so far
        if conv_ids:
            self.current_conv_id = max(conv_ids) + 1

    def _index_recent_days(self):
        """Walk the last `days_to_index` days and build the full in-memory index."""
        today = datetime.now()
        for offset in range(self.days_to_index):
            self._index_day(today - timedelta(days=offset))

        print(f"\n[VectorMemory] Ready — {len(self.memories)} memories indexed "
              f"over the last {self.days_to_index} days.\n")

    # ── Public API ─────────────────────────────────────────────────────────────

    def store(self, role: str, content: str):
        """
        Encode a new role/content record, add to the live index, and
        append a new row to today's embeddings.npy.

        raw_memories.jsonl is NEVER written here — it is owned externally.
        The text index is always re-derived from raw_memories.jsonl on demand.
        """
        label = "User" if role == "user" else "Assistant"
        text = f"{label}: {content}"
        embedding = self.model.encode(text)

        self.memories.append(text)
        self.embeddings.append(embedding)
        self.memory_conv_ids.append(self.current_conv_id)
        if role == "assistant":
            self.current_conv_id += 1

        # Append embedding row to today's embeddings.npy
        today = datetime.now()
        embeddings_path = self._embeddings_path(today)
        os.makedirs(self._day_dir(today), exist_ok=True)

        if os.path.exists(embeddings_path):
            existing = np.load(embeddings_path)
            updated = np.vstack([existing, embedding[np.newaxis, :]])
        else:
            updated = embedding[np.newaxis, :]
        np.save(embeddings_path, updated)

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Return the top-k most semantically similar memories to the query."""
        if not self.memories:
            return []

        # Exclude memories belonging to the last 3 conversations
        recency_cutoff = self.current_conv_id - 3

        query_vec = self.model.encode(query)
        matrix = np.vstack(self.embeddings)            # (N, D)

        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-10, norms)    # avoid division by zero
        scores = matrix.dot(query_vec) / norms

         # Zero out scores for recent conversations
        for i, conv_id in enumerate(self.memory_conv_ids):
            if conv_id >= recency_cutoff:
                scores[i] = -np.inf

        # If everything was filtered, return nothing
        if np.all(scores == -np.inf):
            return []

        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [self.memories[i] for i in top_indices if scores[i] > -np.inf]


class SemanticAgent:
    def __init__(self, days_to_index=7):
        self.memory = VectorMemory(days_to_index=days_to_index)

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