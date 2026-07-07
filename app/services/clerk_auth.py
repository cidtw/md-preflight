from __future__ import annotations

from base64 import urlsafe_b64decode
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import jwt
from jwt import InvalidTokenError, PyJWKClient


class ClerkAuthenticationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class VerifiedClerkSession:
    user_id: str


def verify_clerk_session_token(
    *,
    token: str,
    publishable_key: str,
    secret_key: str,
    authorized_parties: frozenset[str],
) -> VerifiedClerkSession:
    del secret_key
    jwk_client = build_jwk_client(build_clerk_jwks_url(publishable_key))
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            issuer=build_clerk_issuer(publishable_key),
        )
    except InvalidTokenError as exc:
        raise ClerkAuthenticationError("invalid Clerk session token") from exc
    validate_authorized_party(payload.get("azp"), authorized_parties)
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise ClerkAuthenticationError("Clerk session token missing subject")
    return VerifiedClerkSession(user_id=subject)


def validate_authorized_party(azp_claim: object, authorized_parties: frozenset[str]) -> None:
    if not authorized_parties:
        return
    if not isinstance(azp_claim, str) or not azp_claim.strip():
        raise ClerkAuthenticationError("Clerk session token missing azp")
    if normalize_origin(azp_claim) not in authorized_parties:
        raise ClerkAuthenticationError("invalid Clerk session azp")


def build_clerk_jwks_url(publishable_key: str) -> str:
    return f"{build_clerk_issuer(publishable_key)}/.well-known/jwks.json"


def build_clerk_issuer(publishable_key: str) -> str:
    try:
        encoded_domain = publishable_key.split("_", maxsplit=3)[2]
    except IndexError as exc:
        raise ClerkAuthenticationError("invalid Clerk publishable key format") from exc
    domain = normalize_origin(f"https://{decode_publishable_key_domain(encoded_domain)}")
    if not domain:
        raise ClerkAuthenticationError("invalid Clerk publishable key domain")
    return domain


def decode_publishable_key_domain(encoded_domain: str) -> str:
    padding = "=" * (-len(encoded_domain) % 4)
    decoded = urlsafe_b64decode(f"{encoded_domain}{padding}".encode()).decode("utf-8")
    return decoded.removesuffix("$")


def normalize_origin(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ClerkAuthenticationError("invalid origin")
    return f"{parsed.scheme}://{parsed.netloc}"


@lru_cache(maxsize=4)
def build_jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)
