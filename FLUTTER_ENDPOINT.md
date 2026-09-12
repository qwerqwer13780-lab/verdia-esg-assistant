# Flutter handoff

Use the Railway domain as the base URL.

Preferred endpoint:

```http
POST /api/esg/chat
Content-Type: application/json
```

Body:

```json
{
  "question": "Explain Scope 2 emissions",
  "history": []
}
```

Response:

```json
{
  "answer": "...",
  "sources": [],
  "mode": "general",
  "grounded": false
}
```

The existing `/api/rag/chat` path is retained as an alias, so current integration code does not have to change immediately.

For production, route chat through the Node backend so it can attach organization/company context securely instead of trusting values sent directly by the mobile client.
