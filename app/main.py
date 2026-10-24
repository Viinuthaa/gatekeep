
import time

from fastapi import Depends, FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, RateLimitError

from app.auth import verify_api_key
from app.cache import get_cached_response, set_cached_response
from app.config import settings
from app.document_store import document_search
from app.limiter import check_rate_limit
from app.providers import get_chat_completion
from app.request_logs import log_request
from app.router import route_request
from app.schemas import (
    ChatRequest,
    DocumentIngestRequest,
    DocumentSearchRequest,
)


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


@app.post("/api/v1/documents")
async def ingest_document(
    request: DocumentIngestRequest,
    tenant_id: str = Depends(verify_api_key),
):
    try:
        chunks = document_search.add_document(
            tenant_id=tenant_id,
            document_id=request.document_id,
            text=request.text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "tenant_id": tenant_id,
        "document_id": request.document_id,
        "chunks_created": len(chunks),
    }


@app.post("/api/v1/documents/search")
async def search_documents(
    request: DocumentSearchRequest,
    tenant_id: str = Depends(verify_api_key),
):
    try:
        results = document_search.search(
            tenant_id=tenant_id,
            query=request.query,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "tenant_id": tenant_id,
        "query": request.query,
        "result_count": len(results),
        "results": results,
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

    decision = route_request(
        messages=messages,
        requested_model=request.model,
    )

    start_time = time.perf_counter()

    try:
        cached_result = await get_cached_response(
            tenant_id=tenant_id,
            model=decision.model,
            messages=messages,
        )

        cache_hit = cached_result is not None

        if cache_hit:
            result = cached_result
            prompt_tokens = 0
            completion_tokens = 0
        else:
            result = await get_chat_completion(
                model=decision.model,
                messages=messages,
            )

            prompt_tokens = result["prompt_tokens"]
            completion_tokens = result["completion_tokens"]

            await set_cached_response(
                tenant_id=tenant_id,
                model=decision.model,
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
            "routing": {
                "complexity": decision.complexity,
                "reason": decision.reason,
                "selected_model": decision.model,
            },
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
