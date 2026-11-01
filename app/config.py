
import os

from dotenv import load_dotenv

load_dotenv()


def parse_api_keys(raw_value: str) -> dict[str, str]:
    """Parse API keys in the format key:tenant_id,key:tenant_id."""
    api_keys = {}

    for entry in raw_value.split(","):
        entry = entry.strip()

        if not entry:
            continue

        key, separator, tenant_id = entry.partition(":")

        if not separator or not key.strip() or not tenant_id.strip():
            raise ValueError(
                "Invalid GATEKEEP_API_KEYS format. "
                "Expected key:tenant_id,key:tenant_id."
            )

        api_keys[key.strip()] = tenant_id.strip()

    return api_keys


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Gatekeep")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "ollama").lower()

    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434/v1",
    )
    OLLAMA_MODEL: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen2.5:1.5b",
    )

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    )
    OPENROUTER_MODEL: str = os.getenv(
        "OPENROUTER_MODEL",
        "openrouter/free",
    )

    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:password@localhost:5432/gatekeep",
    ).replace("postgresql://", "postgresql+psycopg://", 1)

    GATEKEEP_API_KEYS: dict[str, str] = parse_api_keys(
        os.getenv("GATEKEEP_API_KEYS", "")
    )

    CORS_ORIGINS: list[str] = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CORS_ORIGINS",
            (
                "http://localhost:5173,"
                "http://127.0.0.1:5173,"
                "http://localhost:5174,"
                "http://127.0.0.1:5174"
            ),
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
