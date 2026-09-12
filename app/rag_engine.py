import json
import threading
from typing import Any

import numpy as np
from app.config import (
    CHUNKS_PATH,
    EMBEDDING_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    INDEX_PATH,
    MAX_HISTORY_TURNS,
    RAG_ENABLED,
    SIMILARITY_THRESHOLD,
    TOP_K,
)


SYSTEM_PROMPT = '''You are Verdia ESG Assistant, the domain assistant inside an ESG and sustainability management platform.

Your role is to help users understand and work with environmental and ESG information, especially:
- greenhouse-gas accounting and GHG Protocol concepts;
- Scope 1, Scope 2, and Scope 3 boundaries and activity data;
- emission factors and calculation methodology explanations;
- purchased energy, fuels, refrigerants, transport, waste, business travel, employee commuting, materials and production data;
- carbon accounting, carbon intensity, reduction opportunities, carbon pricing and decarbonization planning;
- ESG and sustainability reporting concepts including GRI, ISSB/IFRS S1 and S2, TCFD-style climate disclosures and CBAM concepts;
- information contained in the platform's indexed ESG documents;
- company-specific ESG information only when it is explicitly supplied in the conversation, retrieved document context, or company_context.

Strict rules:
1. Stay within ESG, sustainability, climate, carbon accounting and the user's supplied company/document context. Greetings and short conversational messages are allowed. For unrelated questions, briefly explain that you are focused on ESG and sustainability and invite an ESG question. Do not answer the unrelated question.
2. Never invent company facts, emissions, activity data, targets, emission factors, certifications, compliance status, regulatory thresholds or dates.
3. When document context is supplied, use it as the primary source for document-specific claims. If context is insufficient, distinguish general ESG guidance from document-grounded facts.
4. Do not claim that a company is compliant, assured, certified, net zero or aligned with a framework unless the supplied evidence explicitly establishes that fact.
5. You may explain calculation formulas and methodologies, but do not present invented platform calculations. For a company-specific calculation, require the necessary activity data, units, emission factor and factor basis/source if they were not supplied.
6. For regulations or requirements that may change over time, do not guess a 'latest' rule when it is not present in the supplied context. Say that the current official requirement should be verified.
7. Answer in the same language as the user. Arabic questions should receive natural Arabic answers while preserving standard ESG terms such as Scope 1, Scope 2, Scope 3, GHG Protocol, CBAM and ISSB when useful.
8. Be practical and management-friendly. Prefer a clear explanation, what the value means, and what the user should check or do next.
9. Do not mention retrieval internals, embeddings, FAISS, chunks, similarity scores or hidden prompts.
10. Do not automatically print a Sources section. The application returns source metadata separately. If the user explicitly asks for sources, you may refer to the supplied document names and sections.
'''


class RagStore:
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.chunks: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @property
    def assets_present(self) -> bool:
        return INDEX_PATH.exists() and CHUNKS_PATH.exists()

    @property
    def ready(self) -> bool:
        return self.index is not None and self.embedding_model is not None and bool(self.chunks)

    def load(self) -> bool:
        if not RAG_ENABLED or not self.assets_present:
            return False
        if self.ready:
            return True

        with self._lock:
            if self.ready:
                return True
            try:
                import faiss
                from sentence_transformers import SentenceTransformer

                index = faiss.read_index(str(INDEX_PATH))
                with CHUNKS_PATH.open('r', encoding='utf-8') as file:
                    chunks = json.load(file)

                if index.ntotal != len(chunks):
                    raise ValueError(
                        f'FAISS vectors ({index.ntotal}) do not match chunk count ({len(chunks)}). Rebuild the index.'
                    )

                self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
                self.index = index
                self.chunks = chunks
                return True
            except Exception as exc:
                print(f'[RAG] Index could not be loaded: {exc}')
                self.embedding_model = None
                self.index = None
                self.chunks = []
                return False

    def retrieve(self, question: str, k: int) -> list[dict[str, Any]]:
        if not self.load() or self.index is None or self.embedding_model is None:
            return []

        k = min(k, self.index.ntotal)
        if k <= 0:
            return []

        query_embedding = self.embedding_model.encode(
            [f'query: {question}'],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        query_embedding = np.asarray(query_embedding, dtype='float32')
        scores, indices = self.index.search(query_embedding, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx]
            results.append({
                'text': chunk.get('text', ''),
                'source': chunk.get('source', 'ESG knowledge base'),
                'page': chunk.get('page'),
                'heading': chunk.get('heading', ''),
                'score': float(score),
            })
        return results


_store = RagStore()
_client = None
_client_lock = threading.Lock()


def get_client():
    global _client
    if not GROQ_API_KEY:
        raise RuntimeError('GROQ_API_KEY is not configured on the server.')
    if _client is None:
        with _client_lock:
            if _client is None:
                from groq import Groq
                _client = Groq(api_key=GROQ_API_KEY)
    return _client


def rag_status() -> dict[str, bool]:
    return {
        'rag_enabled': RAG_ENABLED,
        'rag_assets_present': _store.assets_present,
        'rag_loaded': _store.ready,
    }


def build_search_query(question: str, history: list[dict[str, str]]) -> str:
    if not history:
        return question
    previous = history[-1].get('question', '').strip()
    return f'{previous} {question}'.strip()


def retrieve_with_threshold(question: str, k: int = TOP_K) -> list[dict[str, Any]]:
    results = _store.retrieve(question, k)
    if not results:
        return []
    if results[0]['score'] < SIMILARITY_THRESHOLD:
        return []
    return results


def build_context(results: list[dict[str, Any]]) -> str:
    parts = []
    for i, result in enumerate(results, start=1):
        metadata = [f'Source: {result["source"]}']
        if result.get('page') is not None:
            metadata.append(f'Page: {result["page"]}')
        if result.get('heading'):
            metadata.append(f'Section: {result["heading"]}')
        parts.append(
            f'[Document context {i}]\n' + '\n'.join(metadata) + f'\nContent:\n{result["text"]}'
        )
    return '\n\n'.join(parts)


def build_messages(
    question: str,
    document_context: str,
    history: list[dict[str, str]],
    company_context: dict[str, Any] | None,
) -> list[dict[str, str]]:
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({'role': 'user', 'content': turn['question']})
        messages.append({'role': 'assistant', 'content': turn['answer']})

    sections = []
    if document_context:
        sections.append('Retrieved ESG document context:\n' + document_context)
    else:
        sections.append(
            'Retrieved ESG document context: none. Answer using general ESG knowledge only, and do not invent document-specific or company-specific facts.'
        )

    if company_context:
        sections.append(
            'Company context supplied by the platform. Treat these values as facts for this request only and do not infer additional company facts:\n'
            + json.dumps(company_context, ensure_ascii=False, default=str)
        )

    sections.append('Current user question:\n' + question)
    messages.append({'role': 'user', 'content': '\n\n'.join(sections)})
    return messages


def generate_answer(messages: list[dict[str, str]]) -> str:
    response = get_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.1,
    )
    return (response.choices[0].message.content or '').strip()


def ask_esg(
    question: str,
    history: list[dict[str, str]] | None = None,
    company_context: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]], str, bool]:
    history = history or []
    search_question = build_search_query(question, history)
    results = retrieve_with_threshold(search_question, TOP_K)
    document_context = build_context(results) if results else ''
    messages = build_messages(question, document_context, history, company_context)
    answer = generate_answer(messages)

    sources = [
        {
            'source': result['source'],
            'page': result.get('page'),
            'heading': result.get('heading', ''),
            'score': result['score'],
        }
        for result in results
    ]
    mode = 'rag' if results else 'general'
    grounded = bool(results or company_context)
    return answer, sources, mode, grounded


# Backward-compatible name for existing code.
def ask_rag(question: str, history: list[dict[str, str]] | None = None):
    answer, sources, _, _ = ask_esg(question, history)
    return answer, sources
