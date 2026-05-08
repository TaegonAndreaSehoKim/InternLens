from __future__ import annotations

from fastapi import HTTPException

from src.api import auth


def test_current_user_id_defaults_to_local_user_in_dev_mode(monkeypatch) -> None:
    monkeypatch.delenv("INTERNLENS_AUTH_MODE", raising=False)

    assert auth.current_user_id(authorization=None, x_internlens_user_id=None) == "local_user"
    assert auth.current_user_id(authorization=None, x_internlens_user_id=" user-a ") == "user-a"


def test_current_user_id_requires_bearer_token_in_cognito_mode(monkeypatch) -> None:
    monkeypatch.setenv("INTERNLENS_AUTH_MODE", "cognito")

    try:
        auth.current_user_id(authorization=None, x_internlens_user_id=None)
    except HTTPException as exc:
        assert exc.status_code == 401
        assert "Missing bearer" in exc.detail
    else:
        raise AssertionError("Expected missing Cognito token to be rejected.")


def test_cognito_verifier_returns_token_subject(monkeypatch) -> None:
    settings = auth.AuthSettings(
        mode="cognito",
        cognito_region="us-east-2",
        cognito_user_pool_id="us-east-2_example",
        cognito_app_client_id="client_123",
    )

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            class SigningKey:
                key = "test-key"

            assert token == "token-value"
            return SigningKey()

    monkeypatch.setattr(auth, "PyJWKClient", lambda url: FakeJwksClient())
    monkeypatch.setattr(
        auth.jwt,
        "decode",
        lambda token, key, algorithms, issuer, options: {
            "sub": "cognito-sub-123",
            "token_use": "access",
            "client_id": "client_123",
        },
    )

    verifier = auth.CognitoTokenVerifier()

    assert verifier.verify("token-value", settings) == "cognito-sub-123"
