# DocuMind AI — Document Intelligence & Question Answering System

A 4th-year B.Tech Computer Science / Artificial Intelligence project.

DocuMind AI allows you to upload any PDF document and ask natural-language questions about its contents. Answers are generated strictly from the uploaded document using Retrieval-Augmented Generation (RAG).

---

## Project Overview

**Single-active-document architecture.**  
When a new PDF is uploaded, the previous document's vectors are cleared from the database and replaced with the new document's chunks. Questions are always answered from the currently active document only.

**Pipeline:**

```
PDF Upload → Text Extraction → Chunking → HuggingFace Embeddings
    → Astra DB Vector Store → Similarity Search (top-4 chunks)
        → Groq LLM → Answer + Source Pages → Frontend
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x |
| PDF extraction | pypdf |
| Text chunking | LangChain `RecursiveCharacterTextSplitter` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace) |
| Vector database | DataStax Astra DB |
| LLM | Groq — `openai/gpt-oss-120b` |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Production server | Gunicorn |

---

## Project Structure

```
DocuMind/
├── DocuMind_AI_RAG_Backend.ipynb   ← original working Colab notebook (source of truth)
├── app.py                          ← Flask application entry point
├── rag/
│   ├── __init__.py
│   ├── config.py                   ← environment variable loading & validation
│   ├── embeddings.py               ← HuggingFace embedding model singleton
│   ├── vector_store.py             ← Astra DB connection, clear/insert, retrieval
│   ├── document_processor.py       ← PDF extraction and chunking
│   └── qa.py                       ← Groq LLM, RAG prompt, answer generation
├── templates/
│   └── index.html                  ← frontend HTML
├── static/
│   ├── css/style.css
│   └── js/script.js
├── uploads/                        ← temporary PDF storage (auto-cleaned after processing)
├── .env                            ← local secrets (gitignored — never commit)
├── .env.example                    ← template with placeholder values only
├── .gitignore
├── requirements.txt
├── render.yaml                     ← Render.com deployment configuration
└── README.md
```

---

## Environment Variables

Three credentials are required. Copy `.env.example` to `.env` and fill in the values.

```
ASTRA_DB_APPLICATION_TOKEN=   # Astra DB application token (Database Administrator role)
ASTRA_DB_API_ENDPOINT=        # Astra DB API endpoint URL
GROQ_API_KEY=                 # Groq API key
```

> **Never commit `.env` to version control.** It is listed in `.gitignore`.

---

## Local Setup

### 1. Clone / open the project

```bash
cd "Internship Project/DocuMind"
```

### 2. Create and activate a virtual environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> The first run downloads the `all-MiniLM-L6-v2` embedding model (~90 MB). Subsequent runs use the local cache.

### 4. Configure environment variables

```bash
copy .env.example .env
# Open .env and fill in your Astra DB and Groq credentials
```

### 5. Run locally

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000/**

---

## Using the Application

1. **Upload a PDF** — drag-and-drop or click "Browse PDF". Click **Upload & Process**.
2. Wait for the green success banner confirming the page and chunk count.
3. **Ask a question** in the text area and click **Ask** (or press Ctrl+Enter).
4. The answer is displayed with source page numbers and similarity scores.
5. Upload a different PDF to replace the active document automatically.

---

## RAG Configuration

These values are preserved exactly from the working Colab notebook:

| Setting | Value |
|---|---|
| Chunk size | 1000 characters |
| Chunk overlap | 150 characters |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Astra DB collection | `pdf_qa_demo` |
| Retrieval k | 4 chunks |
| LLM | `openai/gpt-oss-120b` via Groq |
| Temperature | 0 |

---

## Production Start Command

```bash
gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
```

**Why `--workers 1`:** The HuggingFace embedding model (~90 MB) is loaded as a module-level singleton. Multiple Gunicorn workers would each load the model separately, consuming excessive memory. Use 1 worker for this application.

**Why `--timeout 120`:** The initial PDF processing (embedding + Astra DB insert) can take 30–90 seconds for large documents.

> **Note:** Gunicorn is Linux-only. On Windows, use `python app.py` for local development. Gunicorn is only used in production on Linux-based cloud hosts (Render, Railway, etc.).

---

## Deployment Notes (Render.com)

The repository includes `render.yaml` for Render deployment configuration.

**Pre-deployment checklist:**
- [ ] Push code to a GitHub repository (`.env` must NOT be committed)
- [ ] Create a new Web Service on Render, connect the GitHub repo
- [ ] Set the three environment variables in the Render dashboard under **Environment**:
  - `ASTRA_DB_APPLICATION_TOKEN`
  - `ASTRA_DB_API_ENDPOINT`
  - `GROQ_API_KEY`
- [ ] Render will auto-detect `render.yaml` and configure the build/start commands
- [ ] First deploy takes ~5 minutes (model download + dependency install)

**Important:** This application has not been deployed yet. Do not use any placeholder URLs.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Frontend UI |
| `POST` | `/api/upload` | Upload and index a PDF |
| `POST` | `/api/ask` | Ask a question about the active document |
| `GET` | `/api/health` | Server and document status |

### POST /api/upload

Form data: `file` (PDF, max 50 MB)

```json
{
  "success": true,
  "filename": "budget_speech.pdf",
  "pages": 65,
  "chunks": 146
}
```

### POST /api/ask

```json
// Request
{ "question": "What is the fiscal deficit target for 2026-27?" }

// Response
{
  "success": true,
  "answer": "The fiscal deficit for 2026-27 is targeted at 4.3% of GDP.",
  "sources": [
    { "page": 22, "score": 0.8144 },
    { "page": 23, "score": 0.7785 },
    { "page": 5,  "score": 0.7231 }
  ]
}
```

---

## Academic Context

**Project:** DocuMind AI — Document Intelligence & QA System  
**Degree:** B.Tech Computer Science / Artificial Intelligence — 4th Year  
**Core concepts demonstrated:** RAG (Retrieval-Augmented Generation), vector embeddings, semantic search, LLM integration, REST API design, full-stack web development
