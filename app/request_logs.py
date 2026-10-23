
import logging
import time
from uuid import uuid4


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gatekeep.requests")


def log_request(
    tenant_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
) -> dict:
    request_id = str(uuid4())

    log_data = {
        "request_id": request_id,
        "tenant_id": tenant_id,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "latency_ms": round(latency_ms, 2),
    }

    logger.info("chat_request %s", log_data)

    return log_data
