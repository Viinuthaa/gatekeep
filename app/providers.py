
from openai import AsyncOpenAI

from app.config import settings


if settings.AI_PROVIDER == "ollama":
    client = AsyncOpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=60.0,
        max_retries=0,
    )
elif settings.AI_PROVIDER == "openrouter":
    client = AsyncOpenAI(
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY or "missing-api-key",
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
    if settings.AI_PROVIDER == "ollama":
        selected_model = settings.OLLAMA_MODEL
    elif settings.AI_PROVIDER == "openrouter":
        selected_model = settings.OPENROUTER_MODEL
    else:
        selected_model = model

    response = None
    content = None

    # Retry once only when the provider returns an empty response.
    for attempt in range(2):
        response = await client.chat.completions.create(
            model=selected_model,
            messages=messages,
            max_tokens=500,
            temperature=0.2,
        )

        if not response.choices:
            if attempt == 0:
                continue
            raise RuntimeError(
                "The AI provider returned no completion choices "
                "after retrying."
            )

        choice = response.choices[0]
        message = choice.message
        content = message.content

        if isinstance(content, str):
            content = content.strip()

        if content:
            break

        refusal = getattr(message, "refusal", None)
        if refusal:
            content = f"Request refused by provider: {refusal}"
            break

        if attempt == 1:
            finish_reason = getattr(choice, "finish_reason", None)
            raise RuntimeError(
                "The AI provider returned no text content after retrying. "
                f"Model: {response.model}; "
                f"finish_reason: {finish_reason!r}. "
                "Try another available model."
            )

    usage = response.usage

    return {
        "id": response.id,
        "model": response.model,
        "content": content,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
    }
