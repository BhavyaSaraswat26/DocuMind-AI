"""
config.py — Environment variable loading and validation.

Replaces google.colab.userdata with python-dotenv.
All required credentials must be present or the application will
refuse to start.
"""

import os
from dotenv import load_dotenv

# Load .env from the project root (DocuMind/).
# This is a no-op if the file does not exist (variables must then
# already be set in the process environment).
load_dotenv()


def _require(name: str) -> str:
    """Return the value of an environment variable or raise an error."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            f"Please add it to your .env file."
        )
    return value


# ---------------------------------------------------------------------------
# Credentials — loaded once at import time so every module can import them.
# ---------------------------------------------------------------------------

ASTRA_DB_APPLICATION_TOKEN: str = _require("ASTRA_DB_APPLICATION_TOKEN")
ASTRA_DB_API_ENDPOINT: str = _require("ASTRA_DB_API_ENDPOINT")
GROQ_API_KEY: str = _require("GROQ_API_KEY")

# ---------------------------------------------------------------------------
# Astra DB settings — kept identical to the working notebook.
# ---------------------------------------------------------------------------

ASTRA_COLLECTION_NAME: str = "pdf_qa_demo"

# ---------------------------------------------------------------------------
# Chunking settings — kept identical to the working notebook.
# ---------------------------------------------------------------------------

CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 150
CHUNK_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]

# ---------------------------------------------------------------------------
# Embedding model — kept identical to the working notebook.
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Groq / LLM settings — kept identical to the working notebook.
# ---------------------------------------------------------------------------

GROQ_MODEL_NAME: str = "openai/gpt-oss-120b"
GROQ_TEMPERATURE: float = 0

# ---------------------------------------------------------------------------
# Retrieval settings — kept identical to the working notebook.
# ---------------------------------------------------------------------------

RETRIEVAL_K: int = 4

# ---------------------------------------------------------------------------
# Upload directory
# ---------------------------------------------------------------------------

UPLOAD_FOLDER: str = os.path.join(os.path.dirname(__file__), "..", "uploads")
