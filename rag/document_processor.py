"""
document_processor.py — PDF reading, page-wise extraction, and chunking.

Preserves the exact behaviour from the working notebook:

  1. PdfReader reads the uploaded PDF.
  2. Each page is extracted as a LangChain Document with metadata:
         { "source": pdf_name, "document_id": pdf_name, "page": page_number }
     Page numbers start at 1 (notebook used enumerate(..., start=1)).
  3. Pages with no extractable text are skipped.
  4. Documents are chunked with RecursiveCharacterTextSplitter using
     the exact same settings as the notebook:
         chunk_size=1000, chunk_overlap=150,
         separators=["\n\n", "\n", ". ", " ", ""]
"""

import logging
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_SEPARATORS

logger = logging.getLogger(__name__)


def extract_pages(pdf_path: str) -> Tuple[List[Document], str, int]:
    """
    Read a PDF and return one LangChain Document per non-empty page.

    Parameters
    ----------
    pdf_path : str
        Absolute or relative path to the uploaded PDF file.

    Returns
    -------
    documents : list[Document]
        One Document per non-empty page, with metadata:
            source      — original PDF filename (not path)
            document_id — same as source
            page        — 1-based page number
    pdf_name : str
        The bare filename of the PDF (e.g. "report.pdf").
    total_pages : int
        Total number of pages in the PDF (including empty ones).
    """
    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.name  # bare filename — do NOT hard-code

    logger.info("Reading PDF: %s", pdf_name)
    pdfreader = PdfReader(str(pdf_path))
    total_pages = len(pdfreader.pages)

    documents: List[Document] = []

    # enumerate(..., start=1) matches the notebook exactly.
    for page_number, page in enumerate(pdfreader.pages, start=1):
        content = page.extract_text()

        if content and content.strip():
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": pdf_name,
                        "document_id": pdf_name,
                        "page": page_number,
                    },
                )
            )

    logger.info(
        "Extracted %d non-empty pages from %s (total pages: %d).",
        len(documents),
        pdf_name,
        total_pages,
    )
    return documents, pdf_name, total_pages


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split a list of page Documents into smaller chunks.

    Uses the exact same splitter configuration as the working notebook:
        chunk_size=1000, chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]

    Parameters
    ----------
    documents : list[Document]
        Page-level Documents produced by extract_pages().

    Returns
    -------
    list[Document]
        Chunked Documents; each chunk inherits the page metadata from
        its source Document.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=CHUNK_SEPARATORS,
    )

    split_documents = text_splitter.split_documents(documents)
    logger.info("Created %d chunks.", len(split_documents))
    return split_documents


def process_pdf(pdf_path: str) -> Tuple[List[Document], str, int, int]:
    """
    Full pipeline: extract pages then chunk them.

    Parameters
    ----------
    pdf_path : str
        Path to the uploaded PDF.

    Returns
    -------
    chunks : list[Document]
        Chunked Documents ready for Astra DB insertion.
    pdf_name : str
        Bare PDF filename.
    total_pages : int
        Total pages in the PDF.
    chunk_count : int
        Number of chunks produced.
    """
    documents, pdf_name, total_pages = extract_pages(pdf_path)
    chunks = chunk_documents(documents)
    return chunks, pdf_name, total_pages, len(chunks)
