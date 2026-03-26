"""Audit log endpoints — log and retrieve agent actions."""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.audit_log import AuditLog, AuditLogCreate, AuditLogRead, AuditResult
from app.models.credential import Credential, CredentialStatus
from app.services.audit_service import get_audit_logs, log_action
from app.services.jwt_service import verify_token
import jwt

router = APIRouter(prefix="/audit", tags=["audit"])


async def _resolve_token(
    authorization: str,
    session: AsyncSession,
) -> tuple[str, str | None, str | None]:
    """
    Decode Bearer token, check revocation.
    Returns (agent_id, credential_id, jti).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")

    token = authorization[7:]
    try:
        payload = verify_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    jti = payload.get("jti")
    agent_id = payload.get("agent_id")

    # Check revocation
    if jti:
        stmt = select(Credential).where(Credential.jti == jti)
        result = await session.execute(stmt)
        cred = result.scalar_one_or_none()
        if cred and cred.status == CredentialStatus.revoked:
            raise HTTPException(status_code=401, detail="Credential has been revoked")
        return agent_id, cred.id if cred else None, jti

    return agent_id, None, jti


@router.post("/log")
async def log_agent_action(
    body: AuditLogCreate,
    authorization: str = Header(...),
    x_forwarded_for: str | None = Header(None),
    user_agent: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Log an action performed by an agent.
    Must be called with the agent's JWT in Authorization header.
    """
    agent_id, credential_id, jti = await _resolve_token(authorization, session)

    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    entry = await log_action(
        session=session,
        agent_id=agent_id,
        credential_id=credential_id,
        jti=jti,
        log_data=body,
        ip_address=ip,
        user_agent=user_agent,
    )

    return {"logged": True, "log_id": entry.id, "created_at": entry.created_at}


@router.get("/logs", response_model=list[AuditLogRead])
async def get_logs(
    agent_id: str | None = Query(None),
    result: AuditResult | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLogRead]:
    """Retrieve audit logs (dashboard use)."""
    logs = await get_audit_logs(
        session,
        agent_id=agent_id,
        limit=limit,
        offset=offset,
        result_filter=result,
    )
    return logs  # type: ignore


@router.get("/logs/{agent_id}/stats")
async def get_agent_stats(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get aggregate stats for an agent."""
    stmt = select(AuditLog).where(AuditLog.agent_id == agent_id)
    result = await session.execute(stmt)
    logs = result.scalars().all()

    total = len(logs)
    allowed = sum(1 for l in logs if l.result == AuditResult.allowed)
    denied = sum(1 for l in logs if l.result == AuditResult.denied)
    errors = sum(1 for l in logs if l.result == AuditResult.error)
    total_cost = sum(l.cost_usd or 0 for l in logs)

    # Top actions
    from collections import Counter
    action_counts = Counter(l.action for l in logs)
    top_actions = action_counts.most_common(10)

    return {
        "agent_id": agent_id,
        "total_actions": total,
        "allowed": allowed,
        "denied": denied,
        "errors": errors,
        "total_cost_usd": round(total_cost, 6),
        "top_actions": [{"action": a, "count": c} for a, c in top_actions],
    }
