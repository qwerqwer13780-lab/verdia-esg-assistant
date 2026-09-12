# Verdia ESG Assistant — Notebook Logic on Railway

This package keeps the RAG behavior aligned with the original notebook and adapts only the deployment/runtime layer for Railway.

## Public Swagger API

Only these two endpoints are intentionally visible in `/docs`:

- `GET /health` — service availability check.
- `POST /api/esg/chat` — the endpoint the Flutter/Node team should integrate with.

`POST /api/rag/chat` is retained for backward compatibility but hidden from Swagger.

## RAG pipeline

PDFs → PyMuPDF4LLM Markdown → heading-aware splitting → recursive chunks (`1200`, overlap `180`) → `intfloat/multilingual-e5-base` → normalized embeddings → FAISS `IndexFlatIP` → top-5 retrieval → similarity threshold `0.45` → Groq response grounded only in retrieved context.

The seven fixed PDFs are under `data/pdfs/`. There is no user PDF upload endpoint.

## Railway deployment

The `Dockerfile` installs dependencies, downloads the embedding model, builds the FAISS index from the fixed PDFs during image build, and then starts FastAPI.

Railway only needs the secret:

```text
GROQ_API_KEY=your_real_key
```

Optional variables can keep their defaults:

```text
GROQ_MODEL=openai/gpt-oss-20b
EMBEDDING_MODEL=intfloat/multilingual-e5-base
SIMILARITY_THRESHOLD=0.45
TOP_K=5
MAX_HISTORY_TURNS=5
```

## Update the existing Railway service

Do not create a new Railway project. Use the GitHub repo already connected to your current Railway service.

1. Keep the repo's `.git` folder.
2. Replace the old project files with this package's contents.
3. Run:

```bash
git status
git add .
git commit -m "Align ESG assistant with notebook RAG and clean Swagger"
git push
```

4. Railway redeploys automatically.
5. Wait until the deployment becomes `Active`.
6. Open:

```text
https://verdia-esg-assistant-production.up.railway.app/docs
```

Swagger should show only:

```text
GET  /health
POST /api/esg/chat
```

## Request used by Flutter/Node

```http
POST /api/esg/chat
Content-Type: application/json
```

```json
{
  "question": "What is Scope 2?",
  "history": []
}
```

The response shape is:

```json
{
  "answer": "...",
  "sources": [
    {
      "source": "Scope 2 Guidance.pdf",
      "page": 34,
      "heading": "...",
      "score": 0.78
    }
  ]
}
```
