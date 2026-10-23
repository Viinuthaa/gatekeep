
from fastapi import FastAPI
from app.schemas import ChatRequest
from app.config import settings

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
