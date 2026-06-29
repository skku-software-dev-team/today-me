import secrets
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.services.auth import (
    exchange_google_code,
    get_google_auth_url,
    get_or_create_user,
    issue_tokens,
    rotate_refresh_token,
    revoke_refresh_token,
)
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_MAX_AGE = 60 * 60 * 24 * settings.refresh_token_expire_days


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/api/auth",
    )


STATE_TTL = 60 * 10  # 10분 안에 로그인 완료해야 함


@router.get("/google")
async def google_login(redis=Depends(get_redis)):
    state = secrets.token_urlsafe(16)
    await redis.setex(f"oauth_state:{state}", STATE_TTL, "1")
    url = get_google_auth_url(state)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    # state 검증 — Redis에 없으면 위조된 요청
    valid = await redis.getdel(f"oauth_state:{state}")
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")

    try:
        userinfo = await exchange_google_code(code)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google OAuth failed")

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
