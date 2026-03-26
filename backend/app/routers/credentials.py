"""Credential issuance and management endpoints."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.agent import Agent
from app.models.credential import (
    Credential,
    CredentialIssueRequest,
    CredentialIssueResponse,
    CredentialRead,
    CredentialStatus,
)
from app.models.policy import Policy
from app.services.jwt_service import generate_api_key, hash_api_key, issue_token
from app.config import settings

router = APIRouter(prefix="/credentials", tags=["credentials"])


async def _authenticate_agent(
    agent_id: str,
    api_key: str,
    session: AsyncSession,
) -> Agent:
    """Validate agent API key."""
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.api_key_hash != hash_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    if agent.status != "active":
        raise HTTPException(status_code=403, detail=f"Agent is {agent.status}")
    return agent


@router.post("/issue", response_model=CredentialIssueResponse)
async def issue_credential(
    body: CredentialIssueRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> CredentialIssueResponse:
    """
    Issue a short-lived JWT credential for an agent.
    Agent must authenticate with its API key.
    """
    agent = await _authenticate_agent(body.agent_id, x_api_key, session)

    # Load agent's enabled policies
    stmt = (
        select(Policy)
        .where(Policy.agent_id == agent.id, Policy.enabled == True)  # noqa: E712
        .order_by(Policy.priority.desc())
    )
    result = await session.execute(stmt)
    policies = result.scalars().all()

    # Build scope: use override if provided, else use agent's policies
    if body.scope_override:
        scope = {"policies": [body.scope_override]}
    else:
        scope = {
            "policies": [json.loads(p.policy_json) for p in policies],
            "agent_name": agent.name,
            "owner_id": agent.owner_id,
        }

    ttl = body.ttl_minutes or settings.default_token_ttl_minutes
    token, jti, expires_at = issue_token(
        agent_id=agent.id,
        owner_id=agent.owner_id,
        scope=scope,
        ttl_minutes=ttl,
    )

    cred = Credential(
        id=str(uuid.uuid4()),
        agent_id=agent.id,
        jti=jti,
        scope_json=json.dumps(scope),
        ttl_minutes=ttl,
        status=CredentialStatus.active,
        issued_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    session.add(cred)
    await session.flush()

    return CredentialIssueResponse(
        token=token,
        credential_id=cred.id,
        jti=jti,
        expires_at=expires_at,
        scope=scope,
    )


@router.post("/{credential_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_credential(
    credential_id: str,
    reason: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Revoke a credential (adds jti to revocation list)."""
    cred = await session.get(Credential, credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    if cred.status == CredentialStatus.revoked:
        raise HTTPException(status_code=409, detail="Already revoked")

    cred.status = CredentialStatus.revoked
    cred.revoked_at = datetime.now(timezone.utc)
    cred.revoke_reason = reason
    session.add(cred)

    return {"revoked": True, "credential_id": credential_id}


@router.get("/{agent_id}/list", response_model=list[CredentialRead])
async def list_credentials(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[CredentialRead]:
    stmt = (
        select(Credential)
        .where(Credential.agent_id == agent_id)
        .order_by(Credential.issued_at.desc())
        .limit(100)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())  # type: ignore
