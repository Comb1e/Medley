"""
RAG Pipeline: LangChain + Chroma + Pinecone
Features: streaming responses, async queries, swappable vector stores
Retrieval: powered by SemanticSearch (SentenceTransformer-based)
Incremental ingestion: skips already-converted txt files via manifest
"""

import asyncio
import json
import os
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, Generator

import numpy as np
from custom_tools.sentence_search import SemanticSearch
from config import config

# ── LangChain core ────────────────────────────────────────────────────────────
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# ── Pinecone ──────────────────────────────────────────────────────────────────
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# ─────────────────────────────────────────────────────────────────────────────
# LangChain Embeddings adapter — lets SemanticSearch plug into Chroma/Pinecone
# ─────────────────────────────────────────────────────────────────────────────

class SemanticSearchEmbeddings:
    """
    Thin adapter that wraps SemanticSearch so it satisfies LangChain's
    Embeddings interface (embed_documents / embed_query).
    Passed as the `embedding` argument to Chroma and PineconeVectorStore.
    """

    def __init__(self, semantic_search: SemanticSearch):
        self._ss = semantic_search

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._ss.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self._ss.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

class VectorStoreBackend(Enum):
    CHROMA   = "chroma"
    PINECONE = "pinecone"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-anthropic-api-key")
PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY",  "your-pinecone-api-key")
PINECONE_INDEX    = os.getenv("PINECONE_INDEX",     "langchain-rag")

PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["context", "question"],
    template="""Use the retrieved context below to answer the question.
If the answer is not in the context, say "I don't have that information."

Context:
{context}

Question: {question}

Answer:""",
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Manifest helpers — track which files have already been ingested
# ─────────────────────────────────────────────────────────────────────────────

def load_manifest(manifest_path: Path = config.MANIFEST_PATH) -> dict[str, float]:
    """
    Load the ingestion manifest from disk.

    Returns a dict mapping absolute file path → last-modified timestamp (mtime).
    An empty dict is returned when no manifest exists yet (first run).
    """
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(
    manifest: dict[str, float],
    manifest_path: Path = config.MANIFEST_PATH,
) -> None:
    """Persist the ingestion manifest to disk (atomic-ish write)."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest saved -> {manifest_path} ({len(manifest)} entries)")


def _get_new_files(docs_dir: str, manifest: dict[str, float]) -> list[Path]:
    """
    Return .txt files in docs_dir that are either absent from the manifest
    or whose mtime has changed since they were last ingested.
    """
    new_files = []
    for path in sorted(Path(docs_dir).rglob("*.txt")):
        key = str(path.resolve())
        mtime = path.stat().st_mtime
        if key not in manifest or manifest[key] != mtime:
            new_files.append(path)
    return new_files


# ─────────────────────────────────────────────────────────────────────────────
# 2. Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_llm(streaming: bool = False):
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=ANTHROPIC_API_KEY,
        temperature=0,
        streaming=streaming,
    )

def _stream_large_txt(path: Path, block_chars: int = 5 * 1024 * 1024) -> Generator[Document, None, None]:
    """
    Reads a large text file in character blocks to prevent OOM.
    Yields Document objects incrementally rather than loading the entire file at once.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            while True:
                chunk = f.read(block_chars)
                if not chunk:
                    break
                yield Document(page_content=chunk, metadata={"source": str(path)})
    except UnicodeDecodeError:
        # Fallback: skip malformed characters instead of failing completely
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            while True:
                chunk = f.read(block_chars)
                if not chunk:
                    break
                yield Document(page_content=chunk, metadata={"source": str(path)})

def load_and_chunk_documents(
    docs_dir: str,
    manifest: dict[str, float] | None = None,
    max_batch_bytes: int = 5 * 1024 * 1024,       # Flush chunks after accumulating ~5MB of text
    max_single_file_bytes: int = 10 * 1024 * 1024, # Switch to streaming mode for files >10MB
) -> tuple[list[Document], list[Path]]:
    """
    Load only new or modified .txt files from docs_dir and split them into
    chunks. Files already recorded in *manifest* with the same mtime are
    skipped entirely.

    Returns:
        chunks     – LangChain Document objects ready for ingestion.
        new_paths  – the Path objects that were actually loaded (used to
                     update the manifest after successful ingestion).

    Calling code that does NOT want incremental behaviour can pass
    manifest={} to force a full reload.
    """
    if manifest is None:
        manifest = load_manifest()

    new_paths = _get_new_files(docs_dir, manifest)

    if not new_paths:
        print("No new or modified files found — skipping ingestion.")
        return [], []

    print(f"Found {len(new_paths)} new/modified file(s) to ingest:")
    for p in new_paths:
        print(f"  + {p}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )

    all_chunks: list[Document] = []
    batch_docs: list[Document] = []
    current_batch_size = 0
    successful_paths: list[Path] = []

    for path in new_paths:
        file_size = os.path.getsize(path)

        try:
            # Decide loading strategy based on file size
            if file_size > max_single_file_bytes:
                print(file_size)
                print(f"  ⚠️ Large file detected ({file_size / 1024 / 1024:.1f} MB), streaming in blocks...")
                doc_source = _stream_large_txt(path)
            else:
                try:
                    loader = TextLoader(str(path), encoding="utf-8")
                except Exception:
                    loader = TextLoader(str(path))
                doc_source = iter(loader.load())

            # Process documents incrementally
            for doc in doc_source:
                batch_docs.append(doc)
                # Track exact UTF-8 byte size for accurate memory estimation
                current_batch_size += len(doc.page_content.encode("utf-8"))

                # Flush immediately when threshold is reached
                if current_batch_size >= max_batch_bytes:
                    batch_chunks = splitter.split_documents(batch_docs)
                    all_chunks.extend(batch_chunks)
                    batch_docs = []  # Break reference cycle to trigger garbage collection
                    current_batch_size = 0
                    print(f"  ✓ Flushed intermediate batch -> {len(batch_chunks)} chunks")

            successful_paths.append(path)

        except Exception as e:
            print(f"⚠️ Failed to load {path}: {e}")
            continue

    # Process any remaining documents in the buffer
    if batch_docs:
        batch_chunks = splitter.split_documents(batch_docs)
        all_chunks.extend(batch_chunks)
        batch_docs = []
        print(f"  ✓ Flushed final batch -> {len(batch_chunks)} chunks")

    print(f"Successfully processed {len(successful_paths)} file(s) -> {len(all_chunks)} chunks")
    return all_chunks, successful_paths


def ingest_chunks_into_semantic_search(ss: SemanticSearch, chunks: list[Document]) -> None:
    """
    Feed all document chunks into SemanticSearch.add_to_library so they
    are available for retrieval via ss.query().
    """
    if not chunks:
        return
    texts = [chunk.page_content for chunk in chunks]
    ss.add_to_library(texts)
    print(f"SemanticSearch library populated with {len(texts)} chunks")


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Vector store factory — swap between Chroma and Pinecone here
# ─────────────────────────────────────────────────────────────────────────────

def build_chroma_store(chunks: list[Document], embeddings: SemanticSearchEmbeddings) -> Chroma:
    """Create (or overwrite) a persisted Chroma store from chunks."""
    store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(config.CHROMA_PERSIST_DIR),
        collection_name=config.CHROMA_COLLECTION,
    )
    print(f"Chroma store persisted -> {str(config.CHROMA_PERSIST_DIR)}")
    return store


def load_chroma_store(embeddings: SemanticSearchEmbeddings) -> Chroma:
    """Load an existing persisted Chroma store (skip re-ingestion)."""
    return Chroma(
        persist_directory=str(config.CHROMA_PERSIST_DIR),
        embedding_function=embeddings,
        collection_name=config.CHROMA_COLLECTION,
    )


def upsert_chroma_store(
    chunks: list[Document],
    embeddings: SemanticSearchEmbeddings,
    max_batch_size: int = 5120,  # Hard cap per ingestion request
) -> Chroma:
    """
    Add new chunks to an existing Chroma collection without wiping it.
    Processes documents in bounded batches to prevent OOM and respect
    vector DB rate limits. Falls back to build_chroma_store when the
    collection doesn't exist yet.
    """
    if not chunks:
        # Nothing to add — just open the existing store.
        return load_chroma_store(embeddings)

    persist_dir = str(config.CHROMA_PERSIST_DIR)
    collection_exists = Path(persist_dir).exists() and any(
        Path(persist_dir).iterdir()
    )

    if collection_exists:
        store = load_chroma_store(embeddings)
        total = len(chunks)

        # Slice chunks into fixed windows capped at max_batch_size
        for start in range(0, total, max_batch_size):
            batch = chunks[start : start + max_batch_size]

            # LangChain handles embedding generation & DB upsert internally
            store.add_documents(batch)

            # Progress feedback after each successful batch
            batch_num = start // max_batch_size + 1
            total_batches = (total + max_batch_size - 1) // max_batch_size
            print(f"  ✓ Upserted batch {batch_num}/{total_batches} ({len(batch)} chunks)")

        print(f"Chroma store updated with {total} new chunks across {total_batches} batch(es)")
        return store

    return build_chroma_store(chunks, embeddings)


def build_pinecone_store(chunks: list[Document], embeddings: SemanticSearchEmbeddings) -> PineconeVectorStore:
    """Upsert chunks into a Pinecone index (creates index if missing)."""
    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX not in existing:
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=384,          # matches all-MiniLM-L6-v2 output dim
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print(f"Pinecone index '{PINECONE_INDEX}' created")

    store = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=PINECONE_INDEX,
    )
    print(f"Pinecone store ready -> index: {PINECONE_INDEX}")
    return store


def load_pinecone_store(embeddings: SemanticSearchEmbeddings) -> PineconeVectorStore:
    """Connect to an existing Pinecone index (skip re-ingestion)."""
    return PineconeVectorStore(
        index_name=PINECONE_INDEX,
        embedding=embeddings,
    )


def get_vector_store(
    backend: VectorStoreBackend,
    embeddings: SemanticSearchEmbeddings,
    chunks: list[Document] | None = None,
    load_existing: bool = False,
):
    """
    Unified factory. Pass chunks to ingest, or load_existing=True to skip ingestion.

    Incremental mode: pass the *new* chunks only — Chroma uses add_documents()
    to append rather than rebuild, and Pinecone upserts naturally.

    Usage:
        store = get_vector_store(VectorStoreBackend.CHROMA, embeddings, chunks=new_chunks)
        store = get_vector_store(VectorStoreBackend.PINECONE, embeddings, load_existing=True)
    """
    if backend == VectorStoreBackend.CHROMA:
        if load_existing:
            return load_chroma_store(embeddings)
        return upsert_chroma_store(chunks or [], embeddings)

    elif backend == VectorStoreBackend.PINECONE:
        if load_existing or not chunks:
            return load_pinecone_store(embeddings)
        return build_pinecone_store(chunks, embeddings)

    else:
        raise ValueError(f"Unknown backend: {backend}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. RAG chain builder
# ─────────────────────────────────────────────────────────────────────────────

# Core Function
def retrieve(question: str, vector_store, ss: SemanticSearch, BACKEND):
    if BACKEND == VectorStoreBackend.CHROMA:
        print("\n[Similarity Search with Scores]")
        results = vector_store.similarity_search_with_score(question, k=3)
        result = []
        for doc, score in results:
            if score > 1.5:
                result.append(doc)
                print(f"Score: {score:.3f} | {doc.page_content[:100]}...")
        return result

    # Primary: SemanticSearch cosine similarity retrieval
    if ss.vector_library:
        results = ss.query(question, top_k=5)
        print(results)
        return "\n\n".join(r["text"] for r in results)

    # Fallback: vectorstore MMR retrieval
    if vector_store:
        docs = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.7},
        ).invoke(question)
        print(docs)
        return format_docs(docs)

    return ""

def build_rag_chain(ss: SemanticSearch, vectorstore=None, streaming: bool = False):
    """
    Returns a LCEL chain: retriever | prompt | llm | parser

    Retrieval strategy:
      - Primary:  ss.query(question, top_k=5) via SemanticSearch
      - Fallback: vectorstore MMR retriever if ss library is empty
    Works with any vectorstore backend (Chroma or Pinecone).
    """

    llm = get_llm(streaming=streaming)

    chain = (
        {"context": RunnableLambda(retrieve), "question": RunnablePassthrough()}
        | PROMPT_TEMPLATE
        | llm
        | StrOutputParser()
    )
    return chain


# ─────────────────────────────────────────────────────────────────────────────
# 5. Streaming response
# ─────────────────────────────────────────────────────────────────────────────

def stream_query(ss: SemanticSearch, question: str, vectorstore=None) -> None:
    """
    Stream tokens to stdout as they arrive.
    Uses LangChain's .stream() on the LCEL chain.
    """
    print(f"\n[Streaming] {question}\n{'─' * 50}")
    chain = build_rag_chain(ss, vectorstore, streaming=True)

    for token in chain.stream(question):
        print(token, end="", flush=True)

    print("\n")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Async queries
# ─────────────────────────────────────────────────────────────────────────────

async def async_query(ss: SemanticSearch, question: str, vectorstore=None) -> str:
    """Single async query using .ainvoke()."""
    chain = build_rag_chain(ss, vectorstore)
    return await chain.ainvoke(question)


async def async_stream_query(ss: SemanticSearch, question: str, vectorstore=None) -> AsyncIterator[str]:
    """Async streaming — yields tokens as they arrive."""
    chain = build_rag_chain(ss, vectorstore, streaming=True)
    async for token in chain.astream(question):
        yield token


async def async_batch_queries(ss: SemanticSearch, questions: list[str], vectorstore=None) -> list[str]:
    """
    Run multiple queries concurrently with asyncio.gather.
    Much faster than sequential when hitting the LLM for many questions.
    """
    chain = build_rag_chain(ss, vectorstore)
    tasks = [chain.ainvoke(q) for q in questions]
    return await asyncio.gather(*tasks)


async def run_async_examples(ss: SemanticSearch, vectorstore=None) -> None:
    """Demonstrate all async query patterns."""

    # ── Single async query ──────────────────────────────────────────────────
    print("\n[Async Single Query]")
    answer = await async_query(ss, "What is the refund policy?", vectorstore)
    print(answer)

    # ── Async streaming ─────────────────────────────────────────────────────
    print("\n[Async Streaming]")
    async for token in async_stream_query(ss, "Summarise the main topics in the docs", vectorstore):
        print(token, end="", flush=True)
    print()

    # ── Concurrent batch ────────────────────────────────────────────────────
    questions = [
        "What are the payment options?",
        "How do I contact support?",
        "What is the cancellation policy?",
    ]
    print(f"\n[Async Batch — {len(questions)} queries concurrently]")
    answers = await async_batch_queries(ss, questions, vectorstore)
    for q, a in zip(questions, answers):
        print(f"\nQ: {q}\nA: {a}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Main — wire everything together
# ─────────────────────────────────────────────────────────────────────────────

def get_rag_params(ss: SemanticSearch):
    embeddings = SemanticSearchEmbeddings(ss)   # LangChain adapter

    # ── Choose backend here ─────────────────────────────────────────────────
    BACKEND = VectorStoreBackend.CHROMA

    # ── Load manifest (tracks previously ingested files) ────────────────────
    manifest = load_manifest()

    # ── Load and chunk only new/modified documents ──────────────────────────
    # Returns empty lists when everything is already up to date.
    new_chunks, new_paths = load_and_chunk_documents(config.DOCS_DIR, manifest)

    # ── Populate SemanticSearch with new chunks only ─────────────────────────
    ingest_chunks_into_semantic_search(ss, new_chunks)

    # ── Upsert only new chunks into the vectorstore ──────────────────────────
    # upsert_chroma_store (called inside get_vector_store) appends rather than
    # rebuilding, so existing vectors are preserved.
    vectorstore = get_vector_store(BACKEND, embeddings, chunks=new_chunks)

    # ── Persist manifest — record newly ingested files ───────────────────────
    if new_paths:
        for path in new_paths:
            manifest[str(path.resolve())] = path.stat().st_mtime
        save_manifest(manifest)

    return embeddings, BACKEND, vectorstore

def main():
    # ── Initialise SemanticSearch (model loaded once, reused everywhere) ────
    ss = SemanticSearch(model_name="all-MiniLM-L6-v2")
    embeddings = SemanticSearchEmbeddings(ss)   # LangChain adapter

    # ── Choose backend here ─────────────────────────────────────────────────
    BACKEND = VectorStoreBackend.CHROMA

    # ── Load manifest (tracks previously ingested files) ────────────────────
    manifest = load_manifest()

    # ── Load and chunk only new/modified documents ──────────────────────────
    # Returns empty lists when everything is already up to date.
    new_chunks, new_paths = load_and_chunk_documents(config.DOCS_DIR, manifest)

    # ── Populate SemanticSearch with new chunks only ─────────────────────────
    ingest_chunks_into_semantic_search(ss, new_chunks)

    # ── Upsert only new chunks into the vectorstore ──────────────────────────
    # upsert_chroma_store (called inside get_vector_store) appends rather than
    # rebuilding, so existing vectors are preserved.
    vectorstore = get_vector_store(BACKEND, embeddings, chunks=new_chunks)

    # ── Persist manifest — record newly ingested files ───────────────────────
    if new_paths:
        for path in new_paths:
            manifest[str(path.resolve())] = path.stat().st_mtime
        save_manifest(manifest)

    # ── 1. Sync streaming ───────────────────────────────────────────────────
    stream_query(ss, "What is the refund policy for enterprise customers?", vectorstore)

    # ── 2. Async examples (single, streaming, batch) ────────────────────────
    asyncio.run(run_async_examples(ss, vectorstore))

    # ── 3. Similarity search with scores (Chroma only) ──────────────────────
    if BACKEND == VectorStoreBackend.CHROMA:
        print("\n[Similarity Search with Scores]")
        results = vectorstore.similarity_search_with_score("refund policy", k=3)
        for doc, score in results:
            print(f"Score: {score:.3f} | {doc.page_content[:100]}...")

    # ── 4. Direct SemanticSearch retrieval ──────────────────────────────────
    print("\n[SemanticSearch Direct Query]")
    results = ss.query("refund timeline", top_k=3)
    for r in results:
        print(f"  · [{r['score']:.3f}] {r['text'][:120]}")


if __name__ == "__main__":
    main()