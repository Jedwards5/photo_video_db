"""Single-password JWT authentication for the web interface."""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env")

bearer_scheme = HTTPBearer(auto_error=False)


def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"exp": expire, "sub": "user"}, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(default=None),  # query param fallback for image/video src URLs
) -> str:
    raw = (credentials.credentials if credentials else None) or token
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        jwt.decode(raw, SECRET_KEY, algorithms=[ALGORITHM])
        return raw
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
