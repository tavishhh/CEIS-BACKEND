from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_admin
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["Vault Auth"])


@router.post("/login")
async def vault_login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    token_resp = await auth_service.authenticate_user(
        email=str(payload.email),
        password=payload.password,
        required_role="admin",
    )
    user_email = str(payload.email)
    try:
        user = await auth_service.user_repo.get_by_email(str(payload.email))
        if user:
            user_email = user.email
    except Exception:
        pass
    user_role = token_resp.role

    response.set_cookie(
        key="access_token",
        value=token_resp.access_token,
        httponly=True,
        samesite="lax",
    )

    return {
        "access_token": token_resp.access_token,
        "token_type": token_resp.token_type,
        "role": user_role,
        "user": {
            "email": user_email,
            "role": user_role,
        },
    }


@router.get("/me")
async def vault_me(current_admin: User = Depends(get_current_admin)):
    return {
        "id": str(current_admin.id),
        "email": current_admin.email,
        "role": current_admin.role,
        "full_name": current_admin.full_name,
    }
