"""RS256 JWT service — issues and verifies short-lived agent credentials."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings


def generate_key_pair() -> tuple[str, str]:
    """Generate RSA key pair and write to disk. Returns (private_pem, public_pem)."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    settings.private_key_path.parent.mkdir(parents=True, exist_ok=True)
    settings.private_key_path.write_text(private_pem)
    settings.public_key_path.write_text(public_pem)

    # Set restrictive permissions on private key
    settings.private_key_path.chmod(0o600)

    return private_pem, public_pem


def ensure_keys() -> None:
    """Generate keys if they don't exist yet."""
    if not settings.private_key_path.exists():
        generate_key_pair()


def _load_private_key() -> str:
    ensure_keys()
    return settings.private_key_path.read_text()


def _load_public_key() -> str:
    ensure_keys()
    return settings.public_key_path.read_text()


def issue_token(
    agent_id: str,
    owner_id: str,
    scope: dict,
    ttl_minutes: int | None = None,
) -> tuple[str, str, datetime]:
    """
    Issue a signed RS256 JWT for an agent.
    Returns (token, jti, expires_at).
    """
    if ttl_minutes is None:
        ttl_minutes = settings.default_token_ttl_minutes

    ttl_minutes = min(ttl_minutes, settings.max_token_ttl_minutes)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ttl_minutes)
    jti = secrets.token_urlsafe(32)

    payload = {
        "iss": "agentid",
        "sub": agent_id,
        "owner_id": owner_id,
        "agent_id": agent_id,
        "scope": scope,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(payload, _load_private_key(), algorithm="RS256")
    return token, jti, exp


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT. Raises jwt.exceptions on failure.
    Returns the decoded payload.
    """
    return jwt.decode(
        token,
        _load_public_key(),
        algorithms=["RS256"],
        options={"require": ["exp", "iat", "sub", "jti", "scope"]},
    )


def get_public_key_pem() -> str:
    return _load_public_key()


def hash_api_key(api_key: str) -> str:
    """One-way hash for storing API keys."""
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a secure agent API key."""
    return f"agid_{secrets.token_urlsafe(32)}"
