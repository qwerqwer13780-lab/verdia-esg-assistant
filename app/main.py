from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, APP_NAME, APP_VERSION, GROQ_API_KEY, RAG_ENABLED
from app.rag_engine import ask_esg, rag_status
from app.schemas import ChatRequest, ChatResponse, HealthResponse

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description='Verdia ESG Assistant API with optional RAG grounding.',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False if ALLOWED_ORIGINS == ['*'] else True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health', response_model=HealthResponse)
def health():
    status = rag_status()
    return {
        'status': 'ok',
        'service': APP_NAME,
        'version': APP_VERSION,
        'llm_configured': bool(GROQ_API_KEY),
        'rag_enabled': RAG_ENABLED,
        'rag_assets_present': status['rag_assets_present'],
    }


@app.get('/api/esg/status')
def esg_status():
    return {
        'service': APP_NAME,
        'llm_configured': bool(GROQ_API_KEY),
        **rag_status(),
    }


def _chat(request: ChatRequest) -> ChatResponse:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail='AI service is not configured: GROQ_API_KEY is missing.')

    history = [turn.model_dump() for turn in request.history]
    try:
        answer, sources, mode, grounded = ask_esg(
            question=request.question,
            history=history,
            company_context=request.company_context,
        )
        return ChatResponse(answer=answer, sources=sources, mode=mode, grounded=grounded)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'AI generation failed: {type(exc).__name__}') from exc


@app.post('/api/esg/chat', response_model=ChatResponse)
def esg_chat(request: ChatRequest):
    return _chat(request)


# Backward-compatible endpoint for the current Flutter / integration code.
@app.post('/api/rag/chat', response_model=ChatResponse)
def rag_chat(request: ChatRequest):
    return _chat(request)
