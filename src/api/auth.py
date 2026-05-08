from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from src.api.settings import env_value
from src.storage.profile_store import DEFAULT_USER_ID


@dataclass(frozen=True)
class AuthSettings:
    mode: str
    cognito_region: str
    cognito_user_pool_id: str
    cognito_app_client_id: str


def auth_settings_from_env() -> AuthSettings:
    return AuthSettings(
        mode=env_value("INTERNLENS_AUTH_MODE", "dev").lower(),
        cognito_region=env_value("INTERNLENS_COGNITO_REGION", ""),
        cognito_user_pool_id=env_value("INTERNLENS_COGNITO_USER_POOL_ID", ""),
        cognito_app_client_id=env_value("INTERNLENS_COGNITO_APP_CLIENT_ID", ""),
    )


def cognito_issuer(region: str, user_pool_id: str) -> str:
    return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _user_id_from_claims(claims: Dict[str, Any]) -> str:
    user_id = str(claims.get("sub", "")).strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication token is missing a subject.")
    return user_id


class CognitoTokenVerifier:
    def __init__(self) -> None:
        self._jwks_clients: Dict[str, PyJWKClient] = {}

    def verify(self, token: str, settings: AuthSettings) -> str:
        if not settings.cognito_region or not settings.cognito_user_pool_id:
            raise HTTPException(status_code=500, detail="Cognito authentication is not configured.")

        issuer = cognito_issuer(settings.cognito_region, settings.cognito_user_pool_id)
        jwks_url = f"{issuer}/.well-known/jwks.json"
        jwks_client = self._jwks_clients.setdefault(jwks_url, PyJWKClient(jwks_url))

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=issuer,
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid authentication token.") from exc

        token_use = claims.get("token_use")
        if token_use not in {"access", "id"}:
            raise HTTPException(status_code=401, detail="Unsupported Cognito token type.")

        if settings.cognito_app_client_id:
            if token_use == "id" and claims.get("aud") != settings.cognito_app_client_id:
                raise HTTPException(status_code=401, detail="Token audience does not match this app.")
            if token_use == "access" and claims.get("client_id") != settings.cognito_app_client_id:
                raise HTTPException(status_code=401, detail="Token client does not match this app.")

        return _user_id_from_claims(claims)


_COGNITO_VERIFIER = CognitoTokenVerifier()


def current_user_id(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_internlens_user_id: Optional[str] = Header(default=None, alias="X-InternLens-User-Id"),
) -> str:
    settings = auth_settings_from_env()

    if settings.mode == "cognito":
        token = _bearer_token(authorization)
        if token is None:
            raise HTTPException(status_code=401, detail="Missing bearer authentication token.")
        return _COGNITO_VERIFIER.verify(token, settings)

    normalized = str(x_internlens_user_id or DEFAULT_USER_ID).strip()
    return normalized or DEFAULT_USER_ID
