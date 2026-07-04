"""Verifies Supabase-issued JWTs on protected routes.

Uses the project's JWT secret (HS256) from Supabase Settings > API > JWT Settings.
Note: newer Supabase projects can opt into asymmetric (RS256/ES256) signing keys
verified via JWKS instead — check the project's JWT settings before relying on this."""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload["sub"]
