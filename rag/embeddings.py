"""
embeddings.py — HuggingFace embedding model initialisation.

Preserves the exact model used in the working notebook:
    sentence-transformers/all-MiniLM-L6-v2

The model is loaded once (module-level singleton) so it is not
re-downloaded on every request.
"""

import logging

from langchain_huggingface import HuggingFaceEmbeddings

from rag.config import EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)


def load_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load and return the HuggingFace embedding model.

    Uses the exact same model name as the working notebook:
        sentence-transformers/all-MiniLM-L6-v2
    """
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
    model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    logger.info("Embedding model loaded successfully.")
    return model


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once when the rag package is first imported.
# ---------------------------------------------------------------------------

embedding_model: HuggingFaceEmbeddings = load_embedding_model()
