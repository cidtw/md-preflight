from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.clerk_auth import ClerkAuthenticationError, verify_clerk_session_token

InvalidClaimCase = tuple[dict[str, str], frozenset[str]]


@dataclass(frozen=True, slots=True)
class RsaKeyPair:
    private_key: rsa.RSAPrivateKey
    public_key: rsa.RSAPublicKey


@dataclass(frozen=True, slots=True)
class FakeJwkClient:
    public_key: rsa.RSAPublicKey

    def get_signing_key_from_jwt(self, token: str) -> rsa.RSAPublicKey:
        del token
        return self.public_key


INVALID_CLAIM_CASES: list[InvalidClaimCase] = [
    ({"azp": "http://evil.example"}, frozenset()),
    ({"iss": "https://other.clerk.accounts.dev"}, frozenset()),
    ({}, frozenset({"azp"})),
]


@pytest.fixture()
def rsa_key_pair() -> RsaKeyPair:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return RsaKeyPair(private_key=private_key, public_key=private_key.public_key())


def test_verify_clerk_session_token_accepts_clerk_style_token_without_aud(
    monkeypatch: pytest.MonkeyPatch,
    rsa_key_pair: RsaKeyPair,
) -> None:
    publishable_key = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"
    install_fake_jwk_client(monkeypatch, rsa_key_pair.public_key)
    token = build_token(
        rsa_key_pair.private_key,
        {
            "sub": "user_123",
            "iss": "https://example.clerk.accounts.dev",
            "azp": "http://localhost:3000",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
    )

    session = verify_clerk_session_token(
        token=token,
        publishable_key=publishable_key,
        authorized_parties=frozenset({"http://localhost:3000"}),
    )

    assert session.user_id == "user_123"


@pytest.mark.parametrize(
    ("claim_overrides", "removed_claims"),
    INVALID_CLAIM_CASES,
)
def test_verify_clerk_session_token_rejects_invalid_claims(
    monkeypatch: pytest.MonkeyPatch,
    rsa_key_pair: RsaKeyPair,
    claim_overrides: dict[str, str],
    removed_claims: frozenset[str],
) -> None:
    publishable_key = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"
    install_fake_jwk_client(monkeypatch, rsa_key_pair.public_key)
    claims = {
        "sub": "user_123",
        "iss": "https://example.clerk.accounts.dev",
        "azp": "http://localhost:3000",
        "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
    }
    for removed_claim in removed_claims:
        _ = claims.pop(removed_claim, None)
    claims.update(claim_overrides)
    token = build_token(rsa_key_pair.private_key, claims)

    with pytest.raises(ClerkAuthenticationError):
        _ = verify_clerk_session_token(
            token=token,
            publishable_key=publishable_key,
            authorized_parties=frozenset({"http://localhost:3000"}),
        )


def test_verify_clerk_session_token_rejects_expired_token(
    monkeypatch: pytest.MonkeyPatch,
    rsa_key_pair: RsaKeyPair,
) -> None:
    publishable_key = "pk_test_ZXhhbXBsZS5jbGVyay5hY2NvdW50cy5kZXYk"
    install_fake_jwk_client(monkeypatch, rsa_key_pair.public_key)
    token = build_token(
        rsa_key_pair.private_key,
        {
            "sub": "user_123",
            "iss": "https://example.clerk.accounts.dev",
            "azp": "http://localhost:3000",
            "exp": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
        },
    )

    with pytest.raises(ClerkAuthenticationError):
        _ = verify_clerk_session_token(
            token=token,
            publishable_key=publishable_key,
            authorized_parties=frozenset({"http://localhost:3000"}),
        )


def install_fake_jwk_client(
    monkeypatch: pytest.MonkeyPatch,
    public_key: rsa.RSAPublicKey,
) -> None:
    def fake_build_jwk_client(jwks_url: str) -> FakeJwkClient:
        del jwks_url
        return FakeJwkClient(public_key)

    monkeypatch.setattr("app.services.clerk_auth.build_jwk_client", fake_build_jwk_client)


def build_token(
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, str | int],
) -> str:
    return str(jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test"}))
