from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .database import lookup_key, touch_key, check_rate_limit, check_quota

security = HTTPBearer(auto_error=False)

async def verify_api_key(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials and credentials.credentials:
        raw_key = credentials.credentials
    else:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "): raw_key = auth[7:]
        else: raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    key_info = lookup_key(raw_key)
    if key_info is None: raise HTTPException(status_code=401, detail="Invalid API key")
    if key_info["status"] == "disabled": raise HTTPException(status_code=403, detail="API key has been disabled")
    if key_info["status"] != "active": raise HTTPException(status_code=403, detail="API key is not active")

    limit = key_info.get("rate_limit_per_minute", 60)
    if limit > 0 and not check_rate_limit(key_info["id"], limit):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if not check_quota(key_info):
        raise HTTPException(status_code=402, detail="Token quota exceeded")

    touch_key(key_info["id"])
    return key_info