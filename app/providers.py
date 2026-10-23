
from openai import AsyncOpenAI

from app.config import settings


client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY or "missing-api-key"
)


async def get_chat_completion(model: str, messages: list[dict]):
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )

    usage = response.usage

    return {
        "id": response.id,
        "model": response.model,
        "content": response.choices[0].message.content,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
    }
