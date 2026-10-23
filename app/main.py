
from fastapi import FastAPI, HTTPException
from openai import APIConnectionError, APIStatusError, RateLimitError

from app.config import settings
from app.providers import get_chat_completion
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
async def chat_completions(request: ChatRequest):
    try:
        result = await get_chat_completion(
            model=request.model,
            messages=[
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
        )
        return result

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
