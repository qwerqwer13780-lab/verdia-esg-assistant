# Verdia ESG Assistant — Railway Ready

This service is the Verdia platform ESG assistant. It supports two modes automatically:

- **General ESG mode**: answers ESG, sustainability, carbon accounting, GHG Protocol, Scope 1/2/3, CBAM, ISSB and related conceptual questions using the configured LLM.
- **RAG mode**: when `storage/esg.index` and `storage/chunks.json` exist, document-grounded questions retrieve relevant approved ESG source material before generation.

It is intentionally **not** a general-purpose assistant. Company-specific facts must come from `company_context` or indexed documents; the model is instructed not to invent company numbers, targets, compliance status or emission factors.

## API

- `GET /health`
- `GET /api/esg/status`
- `POST /api/esg/chat` — preferred endpoint
- `POST /api/rag/chat` — backward-compatible alias

Example request:

```json
{
  "question": "What is Scope 2 and how is it different from Scope 1?",
  "history": []
}
```

Optional platform/company context:

```json
{
  "question": "What should management focus on based on this energy value?",
  "history": [],
  "company_context": {
    "reporting_period": "2026",
    "purchased_electricity_kwh": 820000,
    "sector": "Manufacturing"
  }
}
```

Example response:

```json
{
  "answer": "...",
  "sources": [],
  "mode": "general",
  "grounded": false
}
```

`mode` becomes `rag` when document context is retrieved. `grounded=true` means the answer used retrieved documents and/or explicit company context.

## Local run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Set `GROQ_API_KEY` in `.env` before calling chat.

## Build the ESG knowledge index

For local index building install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Place approved source PDFs in `data/pdfs/`, then run:

```bash
python scripts/build_index.py
```

This creates:

```text
storage/esg.index
storage/chunks.json
```

Commit those two generated assets with the deployment if the knowledge base is static. Do **not** commit confidential company documents.

Recommended source families for the production knowledge base are listed in `ESG_KNOWLEDGE_SOURCES.md`.

## Railway deploy

1. Push this folder to GitHub.
2. Create a Railway project and deploy the repository.
3. Railway will detect the `Dockerfile`.
4. Add `GROQ_API_KEY` in Railway Variables.
5. Generate a public domain for the service.
6. Test `/health`, then call `/api/esg/chat`.

The container starts with Railway's `$PORT` automatically. The health check is configured at `/health`.

### Hugging Face model cache

The embedding model is downloaded only when RAG assets exist and retrieval is first needed. The Dockerfile sets `HF_HOME=/data/huggingface`.

If you want the downloaded embedding model cache to survive service redeploys/restarts, attach a Railway Volume at `/data`. The assistant still works without a Volume; it may just need to download the embedding model again after a fresh deployment.

## Integration recommendation

For development, Flutter can call Railway directly. For production, prefer:

```text
Flutter -> Node backend -> Verdia ESG Assistant
```

This keeps authentication, organization context, quotas and audit logging in the Node backend.

## Smoke test after deployment

Set the deployed URL and run:

```bash
# macOS/Linux
export VERDIA_AI_URL=https://your-service.up.railway.app
python scripts/smoke_test.py
```

On Windows PowerShell:

```powershell
$env:VERDIA_AI_URL='https://your-service.up.railway.app'
python scripts/smoke_test.py
```

The script checks health, two ESG questions, and one unrelated question to verify that the assistant stays in-domain.
