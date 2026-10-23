
from fastapi import FastAPI

app = FastAPI(
    title="Gatekeep",
    description="A gateway that guards every LLM call.",
    version="0.1.0",
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
        "name": "Gatekeep",
        "version": "0.1.0",
        "description": "A gateway that guards every LLM call.",
    }
