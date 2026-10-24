
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="The role of the message sender",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="The text content of the message",
    )


class ChatRequest(BaseModel):
    model: str = Field(
        ...,
        min_length=1,
        description="The requested model",
    )
    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description="The conversation messages",
    )


class DocumentIngestRequest(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1)


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
