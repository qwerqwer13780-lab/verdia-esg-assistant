from typing import List

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    question: str
    answer: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    history: List[ChatTurn] = Field(default_factory=list)


class SourceItem(BaseModel):
    source: str
    page: int
    heading: str = ''
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = Field(default_factory=list)
