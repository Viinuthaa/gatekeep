
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


security = HTTPBearer(auto_error=False)

API_KEYS = {
    "gk_test_demo_key": "demo-tenant",
}


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key",
        )

    api_key = credentials.credentials

    for stored_key, tenant_id in API_KEYS.items():
        if secrets.compare_digest(api_key, stored_key):
            return tenant_id

    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )
