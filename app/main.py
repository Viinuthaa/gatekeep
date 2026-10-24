
import time

from fastapi import Depends, FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, RateLimitError

from app.auth import verify_api_key
from app.cache import get_cached_response, set_cached_response
from app.config import settings
from app.limiter import check_rate_limit
from app.providers import get_chat_completion
from app.request_logs import log_request
from app.schemas import ChatRequest


app = FastAPI(
    title=settings.APP_NAME,
    description="A gateway that guards every LLM call.",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


@app.get("/")
def home():
    return {
        "message": "Welcome to Gatekeep!",
        "description": "A gateway that guards every LLM call.",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/v1")
def api_info():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "A gateway that guards every LLM call.",
    }


@app.post("/api/v1/chat/completions/validate")
def validate_chat_request(request: ChatRequest):
    return {
        "valid": True,
        "model": request.model,
        "message_count": len(request.messages),
    }


@app.post("/api/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    tenant_id: str = Depends(verify_api_key),
):
    await check_rate_limit(tenant_id)

    messages = [
        {"role": message.role, "content": message.content}
        for message in request.messages
    ]

    start_time = time.perf_counter()

    try:
        cached_result = await get_cached_response(
            tenant_id=tenant_id,
            model=request.model,
            messages=messages,
        )

        cache_hit = cached_result is not None

        if cache_hit:
            result = cached_result
            prompt_tokens = 0
            completion_tokens = 0
        else:
            result = await get_chat_completion(
                model=request.model,
                messages=messages,
            )

            prompt_tokens = result["prompt_tokens"]
            completion_tokens = result["completion_tokens"]

            await set_cached_response(
                tenant_id=tenant_id,
                model=request.model,
                messages=messages,
                response=result,
            )

        latency_ms = (time.perf_counter() - start_time) * 1000

        request_log = log_request(
            tenant_id=tenant_id,
            model=result["model"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

        return {
            **result,
            "tenant_id": tenant_id,
            "request_id": request_log["request_id"],
            "latency_ms": request_log["latency_ms"],
            "cache_hit": cache_hit,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="The AI provider rate limit was reached. Try again later.",
        )

    except APIConnectionError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to the AI provider.",
        )

    except APIStatusError:
        raise HTTPException(
            status_code=502,
            detail="The AI provider returned an error.",
        )
