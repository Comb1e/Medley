import os
import json
import numpy as np
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer

class VectorMemory:
    def __init__(self, raw_dir="logs/raw", vector_dir="logs/vector", days_to_index=7):
        self.raw_dir = raw_dir
        self.vector_dir = vector_dir
        self.days_to_index = days_to_index
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        os.makedirs(vector_dir, exist_ok=True)

        # In-memory index populated from the last 7 days on startup
        self.memories: list[str] = []
        self.embeddings: list[np.ndarray] = []
        self._index_recent_days()

    # ── Raw log reader ─────────────────────────────────────────────────────────

    def _raw_path(self, date) -> str:
        """Resolve logs/raw/YYYY-MM-DD.json for a given date."""
        return os.path.join(self.raw_dir, date.strftime("%Y-%m-%d") + ".json")

    def _load_raw_texts(self, date) -> list[str]:
        """
        Read logs/raw/YYYY-MM-DD.json and return a flat list of memory strings.

        Supports three shapes:
          1. list of strings          → used as-is
          2. list of {"text": "..."}  → extract "text" field
          3. list of {"role","content"} message dicts
             → pairs are joined as "User: ...\nAssistant: ..."
        """
        path = self._raw_path(date)
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[VectorMemory] Cannot read {path}: {e}")
            return []

        if not isinstance(data, list) or not data:
            return []

        texts = []
        first = data[0]

        # Shape 1: plain strings
        if isinstance(first, str):
            texts = [entry for entry in data if isinstance(entry, str) and entry.strip()]

        # Shape 2: {"text": "..."} objects
        elif isinstance(first, dict) and "text" in first:
            texts = [
                entry["text"]
                for entry in data
                if isinstance(entry, dict) and entry.get("text", "").strip()
            ]

        # Shape 3: role/content message dicts → pair up as exchanges
        elif isinstance(first, dict) and "role" in first and "content" in first:
            i = 0
            while i < len(data) - 1:
                user_msg = data[i]
                asst_msg = data[i + 1]
                if (user_msg.get("role") == "user" and
                        asst_msg.get("role") == "assistant"):
                    texts.append(
                        f"User: {user_msg['content']}\n"
                        f"Assistant: {asst_msg['content']}"
                    )
                    i += 2
                else:
                    i += 1

        return texts

    # ── Vector storage helpers ─────────────────────────────────────────────────

    def _vector_dir_for(self, date) -> str:
        """Return logs/vector/YYYY-MM-DD/ for a given date."""
        return os.path.join(self.vector_dir, date.strftime("%Y-%m-%d"))

    def _save_vectors(self, date, texts: list[str], embeddings: np.ndarray):
        """
        Persist texts + embeddings for a given date.
          logs/vector/YYYY-MM-DD/memories.jsonl  — one record per line
          logs/vector/YYYY-MM-DD/embeddings.npy  — (N, D) float32 matrix
        """
        day_dir = self._vector_dir_for(date)
        os.makedirs(day_dir, exist_ok=True)

        # Write memories.jsonl (overwrite — derived from raw, so always reproducible)
        memories_path = os.path.join(day_dir, "memories.jsonl")
        with open(memories_path, "w", encoding="utf-8") as f:
            for text in texts:
                f.write(json.dumps({"text": text}) + "\n")

        # Write embeddings.npy
        np.save(os.path.join(day_dir, "embeddings.npy"), embeddings)

    def _load_vector_cache(self, date):
        """
        Return (texts, embeddings) from an existing vector cache,
        or (None, None) if the cache is missing or corrupt.
        """
        day_dir = self._vector_dir_for(date)
        memories_path = os.path.join(day_dir, "memories.jsonl")
        embeddings_path = os.path.join(day_dir, "embeddings.npy")

        if not os.path.exists(memories_path) or not os.path.exists(embeddings_path):
            return None, None

        texts = []
        with open(memories_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    texts.append(json.loads(line)["text"])
                except (json.JSONDecodeError, KeyError):
                    continue

        try:
            matrix = np.load(embeddings_path)
        except Exception:
            return None, None

        if matrix.shape[0] != len(texts):
            print(f"[VectorMemory] Cache mismatch on {date}, will re-encode.")
            return None, None

        return texts, matrix

    # ── Indexing pipeline ──────────────────────────────────────────────────────

    def _index_day(self, date):
        """
        For one calendar date:
          1. Try the vector cache first (fast path).
          2. If missing/stale, load raw texts → encode → save cache.
          3. Add to the live in-memory index.
        """
        texts, matrix = self._load_vector_cache(date)
        print(texts)

        if texts is None:
            # Cache miss — build from raw log
            texts = self._load_raw_texts(date)
            if not texts:
                return  # No raw data for this day either

            print(f"[VectorMemory] Encoding {len(texts)} memories for {date.date()} ...")
            matrix = self.model.encode(texts, show_progress_bar=False)
            self._save_vectors(date, texts, matrix)

        self.memories.extend(texts)
        self.embeddings.extend(matrix)  # list of 1-D arrays
        print(f"[VectorMemory] Indexed {len(texts)} memories from {date.date()}")

    def _index_recent_days(self):
        """Walk the last `days_to_index` days and build the full in-memory index."""
        today = datetime.now()
        for offset in range(self.days_to_index):
            self._index_day(today - timedelta(days=offset))

        print(f"[VectorMemory] Total indexed: {len(self.memories)} memories "
              f"over the last {self.days_to_index} days.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def store(self, text: str):
        """
        Add a new memory to the live index and append it to today's vector cache.
        (Raw storage is handled externally — we only update the vector side.)
        """
        embedding = self.model.encode(text)
        self.memories.append(text)
        self.embeddings.append(embedding)

        # Append to today's cache files
        today = datetime.now()
        day_dir = self._vector_dir_for(today)
        os.makedirs(day_dir, exist_ok=True)

        memories_path = os.path.join(day_dir, "memories.jsonl")
        with open(memories_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"text": text}) + "\n")

        embeddings_path = os.path.join(day_dir, "embeddings.npy")
        if os.path.exists(embeddings_path):
            existing = np.load(embeddings_path)
            updated = np.vstack([existing, embedding[np.newaxis, :]])
        else:
            updated = embedding[np.newaxis, :]
        np.save(embeddings_path, updated)

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """Return the top-k most semantically similar memories to the query."""
        if not self.memories:
            return []

        query_vec = self.model.encode(query)
        matrix = np.vstack(self.embeddings)              # (N, D)

        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vec)
        norms = np.where(norms == 0, 1e-10, norms)      # avoid division by zero
        scores = matrix.dot(query_vec) / norms

        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [self.memories[i] for i in top_indices]


class SemanticAgent:
    def __init__(self, days_to_index=7):
        self.memory = VectorMemory(days_to_index=days_to_index)

    def store(self, user_input: str, reply: str):
        self.memory.store(f"User: {user_input}\nAssistant: {reply}")

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        self.memory.retrieve(query, top_k=top_k)

    def show_index_stats(self):
        print(f"\n── Vector Index Stats ──")
        print(f"Total memories : {len(self.memory.memories)}")
        print(f"Days indexed   : {self.memory.days_to_index}")
        print(f"Embedding dim  : "
              f"{self.memory.embeddings[0].shape[0] if self.memory.embeddings else 'N/A'}")
        print("────────────────────────\n")


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