from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.auth import create_access_token, get_current_user

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class MeResponse(BaseModel):
    email: str
    role: str = "admin"


@router.post("/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    if data.email != settings.admin_email or data.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )
    token = create_access_token(data.email)
    return LoginResponse(access_token=token, email=data.email)


@router.get("/auth/me", response_model=MeResponse)
async def me(email: str = Depends(get_current_user)):
    return MeResponse(email=email)
