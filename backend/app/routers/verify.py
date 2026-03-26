"""
/verify endpoint — called by external services to check if an agent token
is valid and allowed to perform a specific action on a resource.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

import jwt as pyjwt

from app.database import get_session
from app.models.credential import Credential, CredentialStatus
from app.services.jwt_service import verify_token, get_public_key_pem
from app.services.policy_engine import PolicyEngine
from app.services.audit_service import get_daily_action_count

router = APIRouter(prefix="/verify", tags=["verify"])


class VerifyRequest(BaseModel):
    action: str
    resource: str
    ip_address: str | None = None


class VerifyResponse(BaseModel):
    allowed: bool
    reason: str
    agent_id: str | None = None
    owner_id: str | None = None
    jti: str | None = None
    scope_summary: dict | None = None


@router.post("", response_model=VerifyResponse)
async def verify_token_and_action(
    body: VerifyRequest,
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_session),
) -> VerifyResponse:
    """
    Verify that a bearer token is valid AND that the agent is allowed
    to perform the requested action on the resource.

    External services (Gmail tool, Stripe API, internal systems) call this
    before granting access.
    """
    if not authorization.startswith("Bearer "):
        return VerifyResponse(allowed=False, reason="Bearer token required")

    token = authorization[7:]

    # 1. Verify signature + expiry
    try:
        payload = verify_token(token)
    except pyjwt.ExpiredSignatureError:
        return VerifyResponse(allowed=False, reason="Token expired")
    except pyjwt.InvalidTokenError as e:
        return VerifyResponse(allowed=False, reason=f"Invalid token: {e}")

    agent_id = payload.get("agent_id")
    owner_id = payload.get("owner_id")
    jti = payload.get("jti")
    scope = payload.get("scope", {})

    # 2. Check revocation
    if jti:
        stmt = select(Credential).where(Credential.jti == jti)
        result = await session.execute(stmt)
        cred = result.scalar_one_or_none()
        if cred and cred.status == CredentialStatus.revoked:
            return VerifyResponse(
                allowed=False,
                reason="Credential has been revoked",
                agent_id=agent_id,
                jti=jti,
            )

    # 3. Evaluate policy
    engine = PolicyEngine.from_scope(scope)
    daily_count = await get_daily_action_count(session, agent_id, body.action)

    allowed, reason = engine.evaluate(
        body.action,
        body.resource,
        daily_count=daily_count,
        ip_address=body.ip_address,
    )

    return VerifyResponse(
        allowed=allowed,
        reason=reason,
        agent_id=agent_id,
        owner_id=owner_id,
        jti=jti,
        scope_summary=engine.get_scope_summary(),
    )


@router.get("/public-key")
async def get_public_key() -> dict:
    """Return the RS256 public key for client-side token verification."""
    return {"public_key": get_public_key_pem(), "algorithm": "RS256"}
