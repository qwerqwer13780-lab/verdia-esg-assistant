from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list)
    company_context: dict[str, Any] | None = None


class SourceItem(BaseModel):
    source: str
    page: int | None = None
    heading: str = ''
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = Field(default_factory=list)
    mode: Literal['rag', 'general']
    grounded: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    llm_configured: bool
    rag_enabled: bool
    rag_assets_present: bool
