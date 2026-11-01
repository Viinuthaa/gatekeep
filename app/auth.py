
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings


security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key",
        )

    api_key = credentials.credentials

    for stored_key, tenant_id in settings.GATEKEEP_API_KEYS.items():
        if secrets.compare_digest(api_key, stored_key):
            return tenant_id

    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )
