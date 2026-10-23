
from fastapi import FastAPI

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
