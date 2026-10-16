from fastapi import APIRouter, HTTPException, status

from app import auth
from app.schemas import LoginRequest, TokenOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest):
    """Devuelve un JWT. Solo es necesario si AUTH_ENABLED=true."""
    if not auth.check_credentials(payload.username, payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    token, ttl = auth.create_token(payload.username)
    return TokenOut(access_token=token, expires_in=ttl)
