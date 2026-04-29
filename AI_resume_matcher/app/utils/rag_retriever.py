from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logger import logger


KNOWLEDGE_DIR = Path("docs/knowledge")
_vector_store = None


def load_knowledge_documents() -> list[Document]:
    documents: list[Document] = []

    if not KNOWLEDGE_DIR.exists():
        logger.warning(f"Knowledge directory not found: {KNOWLEDGE_DIR}")
        return documents

    for file_path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            content = file_path.read_text(encoding="utf-8")
            if content.strip():
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "file_name": file_path.name,
                        },
                    )
                )
        except Exception as exc:
            logger.warning(f"Failed to read knowledge file {file_path}: {repr(exc)}")

    logger.info(f"Loaded knowledge documents: {len(documents)}")
    return documents


def build_vector_store():
    documents = load_knowledge_documents()
    if not documents:
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"Knowledge chunks created: {len(chunks)}")

    if not settings.LLM_API_KEY:
        logger.warning("LLM_API_KEY is empty. RAG vector store will not be initialized.")
        return None

    embeddings = OpenAIEmbeddings(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.EMBEDDING_MODEL,
    )

    return FAISS.from_documents(chunks, embedding=embeddings)


def get_vector_store():
    global _vector_store

    if _vector_store is None:
        logger.info("Initializing RAG vector store")
        try:
            _vector_store = build_vector_store()
        except Exception as exc:
            logger.warning(f"Failed to initialize RAG vector store: {repr(exc)}")
            _vector_store = None

    return _vector_store


def retrieve_knowledge(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    vector_store = get_vector_store()
    if vector_store is None:
        logger.warning("Vector store is not available")
        return []

    try:
        docs = vector_store.similarity_search(query, k=top_k)
        results: list[dict[str, Any]] = []

        for index, doc in enumerate(docs):
            content = doc.page_content.strip()
            if not content:
                continue

            results.append(
                {
                    "content": content,
                    "source": doc.metadata.get("source", "unknown"),
                    "file_name": doc.metadata.get("file_name", "unknown"),
                    "rank": index + 1,
                }
            )

        logger.info(f"Retrieved knowledge chunks: {len(results)}")
        return results

    except Exception as exc:
        logger.warning(f"Knowledge retrieval failed: {repr(exc)}")
        return []
