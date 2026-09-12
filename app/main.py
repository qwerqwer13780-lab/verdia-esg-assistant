from fastapi import FastAPI

from app.rag_engine import ask_rag
from app.schemas import ChatRequest, ChatResponse


app = FastAPI(
    title='Verdia ESG Assistant API',
    description=(
        'Evidence-grounded ESG assistant powered by the fixed Verdia knowledge base. '
        'Use the chat endpoint to ask questions about GHG accounting, Scope 1/2/3, '
        'CBAM, and the ESG topics covered by the indexed documents.'
    ),
    version='1.0.0',
    docs_url='/docs',
    redoc_url=None,
)


@app.get(
    '/health',
    tags=['System'],
    summary='Health Check',
    description='Check whether the Verdia ESG Assistant service is online.',
)
def health():
    return {
        'status': 'ok',
        'service': 'Verdia ESG Assistant',
    }


def _chat(request: ChatRequest):
    history = [turn.model_dump() for turn in request.history]
    answer = ask_rag(request.question, history)
    return {'answer': answer}


@app.post(
    '/api/esg/chat',
    response_model=ChatResponse,
    tags=['ESG Assistant'],
    summary='Ask Verdia ESG Assistant',
    description=(
        'Ask an ESG question. The assistant retrieves relevant evidence from the fixed '
        'Verdia ESG PDF knowledge base and returns a clean grounded answer.'
    ),
)
def esg_chat(request: ChatRequest):
    return _chat(request)


# Backward-compatible alias. It still works but stays hidden from Swagger.
@app.post('/api/rag/chat', response_model=ChatResponse, include_in_schema=False)
def rag_chat(request: ChatRequest):
    return _chat(request)
