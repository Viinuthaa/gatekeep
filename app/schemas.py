
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(
        ...,
        description="Who sent the message: system, user, or assistant",
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
        description="The model requested by the client",
    )
    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description="The conversation messages",
    )
