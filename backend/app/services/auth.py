import uuid
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token
from app.models.user import OAuthAccount, User

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

REFRESH_TOKEN_TTL = int(timedelta(days=settings.refresh_token_expire_days).total_seconds())


def get_google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_google_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()


async def get_or_create_user(db: AsyncSession, userinfo: dict) -> User:
    provider_uid = userinfo["id"]

    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_uid == provider_uid,
        )
    )
    oauth = result.scalar_one_or_none()

    if oauth:
        user_result = await db.execute(select(User).where(User.id == oauth.user_id))
        return user_result.scalar_one()

    user_result = await db.execute(select(User).where(User.email == userinfo["email"]))
    user = user_result.scalar_one_or_none()

    if not user:
        user = User(
            email=userinfo["email"],
            nickname=userinfo.get("name"),
            avatar_url=userinfo.get("picture"),
        )
        db.add(user)
        await db.flush()

    oauth = OAuthAccount(
        user_id=user.id,
        provider="google",
        provider_uid=provider_uid,
    )
    db.add(oauth)
    await db.commit()
    await db.refresh(user)
    return user


async def issue_tokens(user_id: uuid.UUID, redis) -> tuple[str, str]:
    uid = str(user_id)
    access_token = create_access_token(uid)
    refresh_token = create_refresh_token(uid)
    await redis.setex(f"refresh:{refresh_token}", REFRESH_TOKEN_TTL, uid)
    return access_token, refresh_token


async def rotate_refresh_token(old_refresh_token: str, redis) -> tuple[str, str]:
    from fastapi import HTTPException, status

    from app.core.jwt import decode_token

    user_id = await redis.get(f"refresh:{old_refresh_token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    decode_token(old_refresh_token)

    await redis.delete(f"refresh:{old_refresh_token}")

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    await redis.setex(f"refresh:{refresh_token}", REFRESH_TOKEN_TTL, user_id)
    return access_token, refresh_token


async def revoke_refresh_token(refresh_token: str, redis):
    await redis.delete(f"refresh:{refresh_token}")
