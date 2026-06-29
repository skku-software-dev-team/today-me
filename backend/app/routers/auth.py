import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.services.auth import (
    exchange_google_code,
    get_google_auth_url,
    get_or_create_user,
    issue_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,  # prod에서는 True로
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/api/auth",
    )


@router.get("/google")
async def google_login():
    state = secrets.token_urlsafe(16)
    url = get_google_auth_url(state)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        userinfo = await exchange_google_code(code)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Google OAuth failed"
        ) from err

    user = await get_or_create_user(db, userinfo)
    access_token, refresh_token = await issue_tokens(user.id, redis)

    response = RedirectResponse(url=f"{settings.frontend_url}/callback?access_token={access_token}")
    _set_refresh_cookie(response, refresh_token)
    return response


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis=Depends(get_redis),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    access_token, new_refresh_token = await rotate_refresh_token(refresh_token, redis)
    _set_refresh_cookie(response, new_refresh_token)
    return {"access_token": access_token}


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    redis=Depends(get_redis),
):
    if refresh_token:
        await revoke_refresh_token(refresh_token, redis)
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"ok": True}
