"""Local merchant sign-in; buyer sessions never grant merchant access."""
import hashlib
import hmac
import os
import secrets
import time
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from app.core.config import DATA_DIR

router = APIRouter(prefix="/api/merchant-session", tags=["Merchant access"])
_attempts = {}


class MerchantBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            public = path == "/api/health" or path.startswith("/api/buyer/") or path == "/api/merchant-session"
            if path.startswith("/api/") and not public and not authorized(Request(scope)):
                from fastapi.responses import JSONResponse
                await JSONResponse(status_code=401, content={"detail": "Merchant sign-in required."})(scope, receive, send)
                return
        await self.app(scope, receive, send)


def passcode():
    configured = os.getenv("ASC_MERCHANT_PASSWORD")
    path = DATA_DIR / "merchant-access.txt"
    if configured:
        # Keep the documented local access file aligned with the active secret.
        # The file is gitignored and never returned by an API.
        if not path.exists() or path.read_text(encoding="utf-8").strip() != configured:
            path.write_text(configured, encoding="utf-8")
        return configured
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_urlsafe(24))
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8").strip()


def signature(value):
    return hmac.new(passcode().encode(), value.encode(), hashlib.sha256).hexdigest()


def authorized(request):
    token = request.cookies.get("asc_merchant", "")
    try:
        expires, signed = token.split(".")
        return int(expires) > time.time() and hmac.compare_digest(signature(expires), signed)
    except (ValueError, TypeError):
        return False


class Login(BaseModel):
    password: str


@router.post("")
def login(payload: Login, request: Request, response: Response):
    client = request.client.host if request.client else "local"
    recent = [t for t in _attempts.get(client, []) if t > time.time() - 60]
    if len(recent) >= 10: raise HTTPException(429, "Please wait a minute before trying again.")
    if not hmac.compare_digest(payload.password, passcode()):
        _attempts[client] = [*recent, time.time()]
        raise HTTPException(401, "Incorrect merchant passcode.")
    _attempts.pop(client, None)
    expires = str(int(time.time()) + 43200)
    response.set_cookie("asc_merchant", f"{expires}.{signature(expires)}", httponly=True, samesite="strict", max_age=43200)
    return {"authenticated": True}


@router.get("")
def status(request: Request):
    return {"authenticated": authorized(request)}


@router.delete("")
def logout(response: Response):
    response.delete_cookie("asc_merchant")
    return {"authenticated": False}
