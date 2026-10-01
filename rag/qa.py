"""
qa.py — Groq LLM, RAG prompt, and answer generation.

Preserves the exact behaviour from the working notebook:

  LLM      : ChatGroq(model="openai/gpt-oss-120b", temperature=0)
  Prompt   : the multi-rule document QA prompt from the notebook
  Chain    : prompt | llm | StrOutputParser()
  Retrieval: similarity_search_with_score(query, k=4)
  Context  : "[Page N]\n<chunk text>" joined with "\n\n"
"""

import logging
from typing import Any, Dict, List, Tuple

from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from rag.config import GROQ_API_KEY, GROQ_MODEL_NAME, GROQ_TEMPERATURE, RETRIEVAL_K
from rag.vector_store import similarity_search

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Groq LLM — identical to the notebook cell.
# ---------------------------------------------------------------------------

def _init_llm() -> ChatGroq:
    logger.info("Initialising Groq LLM (model: %s).", GROQ_MODEL_NAME)
    llm = ChatGroq(
        model=GROQ_MODEL_NAME,
        temperature=GROQ_TEMPERATURE,
        api_key=GROQ_API_KEY,
    )
    logger.info("Groq LLM initialised successfully.")
    return llm


# ---------------------------------------------------------------------------
# RAG prompt — copied verbatim from the notebook.
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are a document question-answering assistant.

Your task is to answer the user's question based strictly on the
provided document context.

IMPORTANT RULES:

1. Carefully read ALL the provided context before answering.
2. The answer may be stated directly or indirectly in the context.
3. Use information from multiple context sections if necessary.
4. Do not use outside knowledge.
5. Do not invent or assume facts that are not supported by the context.
6. If the context contains enough information to answer the question,
   provide the answer clearly and directly.
7. Only say that the answer cannot be found if the provided context
   genuinely contains no relevant information.

Context:
{context}

Question:
{question}

Answer:"""

prompt = ChatPromptTemplate.from_template(_PROMPT_TEMPLATE)

# Module-level singletons.
llm = _init_llm()

rag_chain = (
    prompt
    | llm
    | StrOutputParser()
)

logger.info("RAG chain created successfully.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_answer(query: str) -> Tuple[str, List[Tuple[Document, float]]]:
    """
    Retrieve relevant context chunks then generate an answer via Groq.

    This is a direct port of the notebook's generate_answer() function:

        results = retrieve_context(query, k=4)
        context = "\n\n".join(
            [f"[Page {doc.metadata.get('page')}]\n{doc.page_content}"
             for doc, score in results]
        )
        answer = rag_chain.invoke({"context": context, "question": query})
        return answer, results

    Parameters
    ----------
    query : str
        The user's natural-language question.

    Returns
    -------
    answer : str
        The LLM-generated answer.
    results : list of (Document, float)
        The retrieved (chunk, score) pairs used to build the context.
    """
    results: List[Tuple[Document, float]] = similarity_search(query, k=RETRIEVAL_K)

    # Build page-aware context string — identical to the notebook.
    context = "\n\n".join(
        [
            f"[Page {doc.metadata.get('page')}]\n{doc.page_content}"
            for doc, score in results
        ]
    )

    logger.info("Invoking RAG chain for query: %.80s", query)
    answer: str = rag_chain.invoke({"context": context, "question": query})
    logger.info("Answer generated.")

    return answer, results


def format_sources(results: List[Tuple[Document, float]]) -> List[Dict[str, Any]]:
    """
    Convert retrieval results into a JSON-serialisable list.

    Exposes only page number and relevance score — no internal details.

    Parameters
    ----------
    results : list of (Document, float)

    Returns
    -------
    list of {"page": int, "score": float}
    """
    seen_pages: set = set()
    sources = []
    for doc, score in results:
        page = doc.metadata.get("page")
        if page not in seen_pages:
            seen_pages.add(page)
            sources.append({"page": page, "score": round(float(score), 4)})
    return sources
