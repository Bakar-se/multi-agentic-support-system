"""
FAISS vector store for RAG system.

Builds a FAISS index from policy documents using sentence-transformers embeddings
and provides a retriever interface for document queries.
"""

from typing import Optional

from langchain_core.retrievers import BaseRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from rag.loader import load_documents


# Global variable to store the vector store instance
_vectorstore: Optional[FAISS] = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """
    Create and return a HuggingFace embeddings model using sentence-transformers.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vectorstore() -> FAISS:
    """
    Build FAISS vector store from policy documents.
    """
    print("📄 Loading policy documents...")
    documents = load_documents()

    if not documents:
        raise ValueError("No documents loaded. Cannot build vector store.")

    print(f"🧠 Creating embeddings for {len(documents)} chunks...")
    embeddings = _get_embeddings()

    print("📦 Building FAISS index...")
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embeddings,
    )

    print("✅ FAISS vector store built successfully")
    return vectorstore


def get_vectorstore() -> FAISS:
    """
    Get or create the FAISS vector store instance (singleton).
    """
    global _vectorstore

    if _vectorstore is None:
        _vectorstore = build_vectorstore()

    return _vectorstore


def get_retriever(k: int = 4) -> BaseRetriever:
    """
    Get a retriever interface for querying the vector store.
    """
    vectorstore = get_vectorstore()

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


if __name__ == "__main__":
    print("🧪 Testing FAISS vector store...")

    vs = get_vectorstore()
    print(f"Vector store type: {type(vs)}")
    print(f"Documents indexed: {vs.index.ntotal}")

    retriever = get_retriever(k=2)
    print(f"Retriever type: {type(retriever)}")

    print("\n🎉 Vector store and retriever initialized successfully!")
