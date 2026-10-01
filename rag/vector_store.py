"""
vector_store.py — AstraDBVectorStore initialisation, clearing, and insertion.

Preserves the exact behaviour from the working notebook:

  Single-active-document architecture:
      astra_vector_store.clear()          ← remove ALL previous vectors
      astra_vector_store.add_documents()  ← insert the new PDF's chunks

  Collection name: "pdf_qa_demo"
"""

import logging
from typing import List, Tuple

from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document

from rag.config import (
    ASTRA_DB_APPLICATION_TOKEN,
    ASTRA_DB_API_ENDPOINT,
    ASTRA_COLLECTION_NAME,
    RETRIEVAL_K,
)
from rag.embeddings import embedding_model

logger = logging.getLogger(__name__)


def _init_vector_store() -> AstraDBVectorStore:
    """
    Initialise and return the AstraDBVectorStore.

    Uses the exact same parameters as the working notebook:
        collection_name = "pdf_qa_demo"
        embedding       = HuggingFaceEmbeddings(all-MiniLM-L6-v2)
        token           = ASTRA_DB_APPLICATION_TOKEN
        api_endpoint    = ASTRA_DB_API_ENDPOINT
    """
    logger.info(
        "Initialising AstraDBVectorStore (collection: %s).",
        ASTRA_COLLECTION_NAME,
    )
    store = AstraDBVectorStore(
        collection_name=ASTRA_COLLECTION_NAME,
        embedding=embedding_model,
        token=ASTRA_DB_APPLICATION_TOKEN,
        api_endpoint=ASTRA_DB_API_ENDPOINT,
    )
    logger.info("AstraDBVectorStore initialised successfully.")
    return store


# ---------------------------------------------------------------------------
# Module-level singleton — one connection for the lifetime of the Flask app.
# ---------------------------------------------------------------------------

astra_vector_store: AstraDBVectorStore = _init_vector_store()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def replace_documents(chunks: List[Document]) -> int:
    """
    Clear all existing vectors then insert the new PDF's chunks.

    This preserves the single-active-document behaviour from the notebook:
        astra_vector_store.clear()
        astra_vector_store.add_documents(split_documents)

    Parameters
    ----------
    chunks : list[Document]
        Chunked Documents produced by document_processor.process_pdf().

    Returns
    -------
    int
        Number of chunks inserted.
    """
    logger.info("Clearing previous document vectors from Astra DB...")
    astra_vector_store.clear()
    logger.info("Previous vectors cleared.")

    logger.info("Inserting %d new chunks into Astra DB...", len(chunks))
    inserted_ids = astra_vector_store.add_documents(chunks)
    logger.info("Inserted %d chunks successfully.", len(inserted_ids))

    return len(inserted_ids)


def similarity_search(query: str, k: int = RETRIEVAL_K) -> List[Tuple[Document, float]]:
    """
    Retrieve the top-k most relevant chunks for the given query.

    Wraps the notebook's:
        astra_vector_store.similarity_search_with_score(query, k=4)

    Parameters
    ----------
    query : str
        The user's natural-language question.
    k : int
        Number of chunks to retrieve (default: 4, same as notebook).

    Returns
    -------
    list of (Document, float) tuples
        Each tuple is (chunk_document, relevance_score).
    """
    logger.info("Running similarity search (k=%d) for query: %.80s", k, query)
    results = astra_vector_store.similarity_search_with_score(query, k=k)
    logger.info("Retrieved %d chunks.", len(results))
    return results
