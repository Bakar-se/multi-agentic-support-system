"""
Document loader for RAG system.

Loads policy documents from the data directory, splits them into chunks,
and returns a list of LangChain Document objects.
"""

from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Get the project root directory (parent of rag/)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Policy documents to load (as specified in SRS)
POLICY_DOCUMENTS = [
    "return_policy.md",
    "care_plus_benefits.md",
    "troubleshooting_guide.md",
]


def load_documents() -> List[Document]:
    """
    Load all policy documents from the data directory and split into chunks.

    Returns:
        List[Document]: List of document chunks (300–500 tokens each)
    """
    all_documents: List[Document] = []

    # ~300–500 tokens ≈ 1200–2000 characters
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    for doc_name in POLICY_DOCUMENTS:
        doc_path = DATA_DIR / doc_name

        if not doc_path.exists():
            print(f"⚠️ Warning: {doc_name} not found at {doc_path}")
            continue

        try:
            loader = TextLoader(str(doc_path), encoding="utf-8")
            documents = loader.load()

            for doc in documents:
                doc.metadata.update(
                    {
                        "source": doc_name,
                        "source_path": str(doc_path),
                    }
                )

            chunks = text_splitter.split_documents(documents)

            for idx, chunk in enumerate(chunks):
                chunk.metadata.update(
                    {
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                    }
                )

            all_documents.extend(chunks)
            print(f"✅ Loaded {len(chunks)} chunks from {doc_name}")

        except Exception as e:
            print(f"❌ Error loading {doc_name}: {e}")

    print(f"\n📚 Total chunks loaded: {len(all_documents)}")
    return all_documents


if __name__ == "__main__":
    docs = load_documents()
    if docs:
        print("\n🔍 Sample chunk preview:")
        print(docs[0].page_content[:200], "...")
        print("Metadata:", docs[0].metadata)
