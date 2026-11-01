import logging
from uuid import uuid4

from app.models import RequestLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gatekeep.requests")


def log_request(
    tenant_id,
    model,
    prompt_tokens,
    completion_tokens,
    latency_ms,
    db=None,
    prompt="",
    cache_hit=False,
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
        "cache_hit": cache_hit,
    }

    if db is not None:
        record = RequestLog(
            request_id=request_id,
            tenant_id=tenant_id,
            model=model,
            prompt=prompt[:2000],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_ms, 2),
            cache_hit=cache_hit,
        )
        try:
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist request history")

    logger.info("chat_request %s", log_data)
    return log_data