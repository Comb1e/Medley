"""
RAG Pipeline: LangChain + Chroma + Pinecone
Features: streaming responses, async queries, swappable vector stores
Retrieval: powered by SemanticSearch (SentenceTransformer-based)
"""

import asyncio
import os
from enum import Enum
from typing import AsyncIterator

import numpy as np
from custom_tools.sentence_search import SemanticSearch
from config import config

# ── LangChain core ────────────────────────────────────────────────────────────
from langchain_community.vectorstores import Chroma
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
# 1. Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_llm(streaming: bool = False):
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=ANTHROPIC_API_KEY,
        temperature=0,
        streaming=streaming,
    )


def load_and_chunk_documents(docs_dir: str) -> list[Document]:
    try:
        loader = DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
        documents = loader.load()
    except:
        loader = DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader)
        documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"Loaded {len(documents)} docs -> {len(chunks)} chunks")
    return chunks


def ingest_chunks_into_semantic_search(ss: SemanticSearch, chunks: list[Document]) -> None:
    """
    Feed all document chunks into SemanticSearch.add_to_library so they
    are available for retrieval via ss.query().
    """
    texts = [chunk.page_content for chunk in chunks]
    ss.add_to_library(texts)
    print(f"SemanticSearch library populated with {len(texts)} chunks")


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Vector store factory — swap between Chroma and Pinecone here
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

    Usage:
        store = get_vector_store(VectorStoreBackend.CHROMA, embeddings, chunks=chunks)
        store = get_vector_store(VectorStoreBackend.PINECONE, embeddings, load_existing=True)
    """
    if backend == VectorStoreBackend.CHROMA:
        return load_chroma_store(embeddings) if load_existing else build_chroma_store(chunks, embeddings)
    elif backend == VectorStoreBackend.PINECONE:
        return load_pinecone_store(embeddings) if load_existing else build_pinecone_store(chunks, embeddings)
    else:
        raise ValueError(f"Unknown backend: {backend}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. RAG chain builder
# ─────────────────────────────────────────────────────────────────────────────

# Core Function
def retrieve(question: str, vector_store, ss: SemanticSearch, BACKEND) -> str:
    if BACKEND == VectorStoreBackend.CHROMA:
        print("\n[Similarity Search with Scores]")
        results = vector_store.similarity_search_with_score(question, k=3)
        for doc, score in results:
            print(f"Score: {score:.3f} | {doc.page_content[:100]}...")
        return results

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
# 4. Streaming response
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
# 5. Async queries
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
# 6. Main — wire everything together
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Initialise SemanticSearch (model loaded once, reused everywhere) ────
    ss = SemanticSearch(model_name="all-MiniLM-L6-v2")
    embeddings = SemanticSearchEmbeddings(ss)   # LangChain adapter

    # ── Choose backend here ─────────────────────────────────────────────────
    # Swap to VectorStoreBackend.PINECONE to use Pinecone instead of Chroma
    BACKEND = VectorStoreBackend.CHROMA

    # ── Load and chunk documents ────────────────────────────────────────────
    chunks = load_and_chunk_documents(DOCS_DIR)

    # ── Populate SemanticSearch library (primary retriever) ─────────────────
    ingest_chunks_into_semantic_search(ss, chunks)

    # ── Build vectorstore (fallback retriever + similarity search) ──────────
    # Set load_existing=True on subsequent runs to skip re-ingestion
    vectorstore = get_vector_store(BACKEND, embeddings, chunks=chunks, load_existing=False)

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