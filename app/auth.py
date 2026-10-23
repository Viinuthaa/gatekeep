
import secrets

from fastapi import Header, HTTPException


API_KEYS = {
    "gk_test_demo_key": "demo-tenant",
}


async def verify_api_key(
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key",
        )

    api_key = authorization.removeprefix("Bearer ").strip()

    for stored_key, tenant_id in API_KEYS.items():
        if secrets.compare_digest(api_key, stored_key):
            return tenant_id

    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )
