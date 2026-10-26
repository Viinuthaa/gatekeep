
from openai import AsyncOpenAI

from app.config import settings


if settings.AI_PROVIDER == "ollama":
    client = AsyncOpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=60.0,
        max_retries=0,
    )
else:
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY or "missing-api-key",
        timeout=60.0,
        max_retries=0,
    )


async def get_chat_completion(model: str, messages: list[dict]):
    selected_model = (
        settings.OLLAMA_MODEL
        if settings.AI_PROVIDER == "ollama"
        else model
    )

    response = await client.chat.completions.create(
        model=selected_model,
        messages=messages,
        max_tokens=180,
        temperature=0.2,
    )

    usage = response.usage

    return {
        "id": response.id,
        "model": response.model,
        "content": response.choices[0].message.content,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
    }
