from sentence_transformers import SentenceTransformer
import numpy as np

from config import config

class SemanticSearch:
    def __init__(self, model_name: str = config.EMBEDDINGS_MODEL_NAME):
        """
        Initialize the SemanticSearch with a SentenceTransformer model.

        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        self.model = SentenceTransformer(model_name)
        self.vector_library = []      # List of (text, embedding) tuples

    def add_to_library(self, statements: list[str]):
        """
        Encode statements and add them to the vector library.

        Args:
            statements: List of text statements to add
        """
        embeddings = self.model.encode(statements, convert_to_numpy=True)
        for text, embedding in zip(statements, embeddings):
            self.vector_library.append((text, embedding))

    def load_library(self, statements: list[str], embeddings: np.ndarray):
        """
        Load a pre-existing vector library directly.

        Args:
            statements: List of text statements
            embeddings: Corresponding numpy array of embeddings (shape: [n, dim])
        """
        if len(statements) != len(embeddings):
            raise ValueError("Number of statements must match number of embeddings.")
        self.vector_library = list(zip(statements, embeddings))

    def query(self, query_statement: str, top_k: int = 5) -> list[dict]:
        """
        Query the vector library with a statement and return top-k similar results.

        Args:
            query_statement: The input statement to search for
            top_k: Number of top results to return

        Returns:
            List of dicts with 'text' and 'score' keys, sorted by similarity
        """
        if not self.vector_library:
            raise ValueError("Vector library is empty. Add statements first.")

        # Encode the query
        query_embedding = self.model.encode(query_statement, convert_to_numpy=True)

        # Compute cosine similarities
        results = []
        for text, embedding in self.vector_library:
            score = self._cosine_similarity(query_embedding, embedding)
            results.append({"text": text, "score": float(score)})

        # Sort by score descending and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(vec1, vec2) / (norm1 * norm2)


# --- Example Usage ---
if __name__ == "__main__":
    # 1. Initialize
    searcher = SemanticSearch(model_name="all-MiniLM-L6-v2")

    # 2. Build the vector library
    library_statements = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence.",
        "Python is a popular programming language for data science.",
        "The Eiffel Tower is located in Paris, France.",
        "Deep learning models require large amounts of training data.",
        "Natural language processing enables computers to understand text.",
    ]
    searcher.add_to_library(library_statements)

    # 3. Query
    query = "What programming language is used in AI?"
    results = searcher.query(query, top_k=3)

    print(f"Query: '{query}'\n")
    print("Top Results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. Score: {result['score']:.4f} | {result['text']}")