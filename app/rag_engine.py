import json

import faiss
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer

from app.config import (
    CHUNKS_PATH,
    EMBEDDING_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    INDEX_PATH,
    MAX_HISTORY_TURNS,
    SIMILARITY_THRESHOLD,
    TOP_K,
)


# Same RAG assets used in the notebook, loaded once when the service starts.
client = Groq(api_key=GROQ_API_KEY)
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
index = faiss.read_index(str(INDEX_PATH))

with CHUNKS_PATH.open('r', encoding='utf-8') as file:
    chunks = json.load(file)


# Same system prompt used in ESG_RAG_Clean_Structured_v3.
SYSTEM_PROMPT = """You are a helpful AI assistant for an ESG and sustainability management platform.

Use the supplied document context as the only source of factual information.

Rules:
- Answer only what the retrieved context directly supports.
- Do not add facts from general knowledge.
- Do not invent formulas, emission factors, thresholds, regulations, definitions, or reporting requirements.
- If the available information is incomplete, say so naturally and briefly.
- If there is not enough information, say you do not have enough information to answer confidently.
- Answer in the same language as the user when practical.
- Write naturally and professionally, like a polished ESG assistant.
- Give a clear, complete answer rather than sounding like raw retrieved text.
- Use short paragraphs or bullets only when they improve readability.
- Be direct and concise unless the user asks for more detail.
- Do not mention file names, page numbers, sources, citations, retrieved chunks, or the knowledge base unless the user explicitly asks for them.
- Do not add a Sources section.
- Avoid tables unless the user asks for one.

For greetings or short conversational messages, reply naturally.
"""


def embed_query(question):
    query_embedding = embedding_model.encode(
        [f'query: {question}'],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(query_embedding, dtype='float32')


def retrieve(question, k=TOP_K):
    k = min(k, index.ntotal)
    query_embedding = embed_query(question)
    scores, indices = index.search(query_embedding, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        chunk = chunks[idx]
        results.append({
            'text': chunk['text'],
            'source': chunk['source'],
            'page': chunk['page'],
            'heading': chunk['heading'],
            'score': float(score),
        })

    return results


def retrieve_with_threshold(question, k=TOP_K):
    results = retrieve(question, k)

    if not results:
        return None

    if results[0]['score'] < SIMILARITY_THRESHOLD:
        return None

    return results


def build_context(results):
    context_parts = []

    for i, result in enumerate(results, start=1):
        context_part = f'[Context {i}]\n'

        if result['heading']:
            context_part += f'Section: {result["heading"]}\n'

        context_part += result['text']
        context_parts.append(context_part)

    return '\n\n'.join(context_parts)


def generate_answer(question, context='', previous_question=''):
    conversation_note = ''

    if previous_question:
        conversation_note = f'Previous user question:\n{previous_question}\n\n'

    user_prompt = f"""{conversation_note}Document context:
{context if context else 'No document context was retrieved.'}

Current user question:
{question}"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_prompt},
        ],
        temperature=0,
    )

    return response.choices[0].message.content


def is_greeting(question):
    text = question.strip().lower()

    greetings = {
        'hi', 'hello', 'hey',
        'اهلا', 'أهلا',
        'السلام عليكم', 'سلام',
        'شكرا', 'شكرًا',
        'thanks', 'thank you',
    }

    return text in greetings


def is_follow_up(question):
    text = question.strip().lower()
    words = text.split()

    follow_up_starts = (
        'and ', 'what about', 'how about', 'and what',
        'طيب', 'طب', 'وماذا', 'وما ', 'وايه', 'و ايه', 'وإيه',
    )

    return len(words) <= 5 or text.startswith(follow_up_starts)


def ask_rag(question, history=None):
    history = history or []
    previous_question = history[-1]['question'] if history else ''

    if is_greeting(question):
        answer = generate_answer(question)
        return answer

    search_question = question

    if previous_question and is_follow_up(question):
        search_question = f'{previous_question} {question}'

    results = retrieve_with_threshold(search_question, k=TOP_K)

    if results is None:
        if any('\u0600' <= char <= '\u06ff' for char in question):
            return 'المعلومات المتاحة لدي لا تكفي للإجابة على هذا السؤال بثقة.'
        return "I don't have enough information to answer that confidently."

    context = build_context(results)
    answer = generate_answer(
        question,
        context,
        previous_question=previous_question if is_follow_up(question) else '',
    )

    return answer
