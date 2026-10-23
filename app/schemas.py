
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
