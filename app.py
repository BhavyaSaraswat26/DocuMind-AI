"""
app.py — Flask entry point for DocuMind AI.

Routes
------
  GET  /              — serve the frontend UI
  POST /api/upload    — accept a PDF, process it, store in Astra DB
  POST /api/ask       — answer a question about the current document
  GET  /api/health    — server + document state
"""

import logging
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Configure logging before importing rag modules so every module's logger
# uses the same format.  Do NOT print credentials anywhere.
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import rag modules.
# These imports trigger module-level singletons:
#   - config.py   validates credentials
#   - embeddings.py loads the HuggingFace model
#   - vector_store.py connects to Astra DB
#   - qa.py initialises Groq and builds the RAG chain
# If any credential is missing, the app will fail here with a clear message.
# ---------------------------------------------------------------------------

from rag.config import UPLOAD_FOLDER
from rag.document_processor import process_pdf
from rag.vector_store import replace_documents
from rag.qa import generate_answer, format_sources

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Ensure the uploads directory exists.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Stage B: limit upload size to 50 MB.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Allowed file extensions.
ALLOWED_EXTENSIONS = {"pdf"}


def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ---------------------------------------------------------------------------
# Stage B: Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(413)
def request_entity_too_large(_error):
    """Return a clean JSON error when the uploaded file exceeds 50 MB."""
    return (
        jsonify(
            {
                "success": False,
                "error": "File too large. Maximum allowed size is 50 MB.",
            }
        ),
        413,
    )


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------


@app.route("/", methods=["GET"])
def index():
    """Serve the frontend UI."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Application state — tracks whether a document has been uploaded.
# ---------------------------------------------------------------------------

_document_loaded: bool = False
_current_document: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    """
    Accept a PDF upload, extract pages, chunk, clear old Astra vectors,
    insert new chunks.

    Returns
    -------
    JSON
        {"success": true, "filename": "...", "pages": N, "chunks": M}
        or
        {"success": false, "error": "..."}
    """
    global _document_loaded, _current_document

    # --- Validate request ---------------------------------------------------
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in the request."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not _allowed_file(file.filename):
        return jsonify({"success": False, "error": "Please upload a PDF file."}), 400

    # --- Save temporarily ---------------------------------------------------
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)
    logger.info("PDF saved temporarily: %s", filename)

    try:
        # --- Process: extract pages + chunk ---------------------------------
        chunks, pdf_name, total_pages, chunk_count = process_pdf(save_path)

        if not chunks:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Could not extract any text from the uploaded PDF.",
                    }
                ),
                422,
            )

        # --- Store: clear old vectors + insert new ones ---------------------
        replace_documents(chunks)

        # Update application state.
        _document_loaded = True
        _current_document = pdf_name

        logger.info(
            "Document processed and stored: %s (%d pages, %d chunks).",
            pdf_name,
            total_pages,
            chunk_count,
        )

        return jsonify(
            {
                "success": True,
                "filename": pdf_name,
                "pages": total_pages,
                "chunks": chunk_count,
            }
        )

    except Exception as exc:
        # Log the full exception server-side; return a safe message to client.
        logger.exception("Error processing PDF '%s': %s", filename, exc)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An error occurred while processing the PDF. "
                    "Please check the server logs.",
                }
            ),
            500,
        )
    finally:
        # Clean up the temporary file.
        if os.path.exists(save_path):
            os.remove(save_path)
            logger.info("Temporary file removed: %s", filename)


@app.route("/api/ask", methods=["POST"])
def ask_question():
    """
    Answer a question about the currently loaded document.

    Request body (JSON)
    -------------------
    {"question": "What is ...?"}

    Returns
    -------
    JSON
        {"success": true, "answer": "...", "sources": [{"page": N, "score": F}]}
        or
        {"success": false, "error": "..."}
    """
    if not _document_loaded:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "No document has been uploaded yet. "
                    "Please upload a PDF first.",
                }
            ),
            400,
        )

    # --- Validate request body ----------------------------------------------
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be JSON."}), 400

    question = data.get("question", "").strip()
    if not question:
        return (
            jsonify({"success": False, "error": "The 'question' field is required."}),
            400,
        )

    # --- Generate answer ----------------------------------------------------
    try:
        answer, results = generate_answer(question)
        sources = format_sources(results)

        return jsonify(
            {
                "success": True,
                "answer": answer,
                "sources": sources,
            }
        )

    except Exception as exc:
        logger.exception("Error generating answer for question '%.80s': %s", question, exc)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An error occurred while generating the answer. "
                    "Please check the server logs.",
                }
            ),
            500,
        )


# ---------------------------------------------------------------------------
# Health-check route (useful for quick sanity testing)
# ---------------------------------------------------------------------------


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "document_loaded": _document_loaded,
            "current_document": _current_document,
        }
    )


# ---------------------------------------------------------------------------
# Entry point — local development only.
#
# Production deployment uses Gunicorn:
#   gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT
#
# Gunicorn never executes this block; it imports the `app` object directly.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
