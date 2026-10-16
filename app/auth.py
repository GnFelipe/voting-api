"""Autenticacion JWT opcional (AUTH_ENABLED=true para activarla)."""
import hmac
import os
import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _secret() -> str:
    return os.getenv("JWT_SECRET", "dev-secret-change-me-dev-secret-change-me")


def _expire_seconds() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", "60")) * 60


def check_credentials(username: str, password: str) -> bool:
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    # compare_digest evita ataques de timing
    ok_user = hmac.compare_digest(username.encode(), expected_user.encode())
    ok_pass = hmac.compare_digest(password.encode(), expected_pass.encode())
    return ok_user and ok_pass


def create_token(username: str) -> tuple[str, int]:
    now = int(time.time())
    ttl = _expire_seconds()
    token = jwt.encode(
        {"sub": username, "iat": now, "exp": now + ttl}, _secret(), algorithm=ALGORITHM
    )
    return token, ttl


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if not auth_enabled():
        return
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token invalido o ausente",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        jwt.decode(credentials.credentials, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise unauthorized
