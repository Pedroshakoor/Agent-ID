"""Audit log service — structured action logging for every agent action."""

import json
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit_log import AuditLog, AuditLogCreate, AuditResult
from app.models.agent import Agent

logger = structlog.get_logger()


async def log_action(
    session: AsyncSession,
    agent_id: str,
    credential_id: str | None,
    jti: str | None,
    log_data: AuditLogCreate,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Persist an audit log entry."""
    entry = AuditLog(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        credential_id=credential_id,
        jti=jti,
        action=log_data.action,
        resource=log_data.resource,
        result=log_data.result,
        prompt_snippet=log_data.prompt_snippet[:1024] if log_data.prompt_snippet else None,
        tool_called=log_data.tool_called,
        result_summary=log_data.result_summary,
        cost_usd=log_data.cost_usd,
        duration_ms=log_data.duration_ms,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=log_data.metadata_json,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)

    # Update agent last_active_at
    agent = await session.get(Agent, agent_id)
    if agent:
        agent.last_active_at = datetime.now(timezone.utc)

    await session.flush()

    logger.info(
        "agent_action",
        agent_id=agent_id,
        action=log_data.action,
        resource=log_data.resource,
        result=log_data.result,
        jti=jti,
    )

    return entry


async def get_daily_action_count(
    session: AsyncSession,
    agent_id: str,
    action: str | None = None,
) -> int:
    """Count actions today for rate limiting against max_daily conditions."""
    from datetime import date
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(
        tzinfo=timezone.utc
    )

    stmt = select(AuditLog).where(
        AuditLog.agent_id == agent_id,
        AuditLog.created_at >= today_start,
        AuditLog.result == AuditResult.allowed,
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)

    result = await session.execute(stmt)
    return len(result.scalars().all())


async def get_audit_logs(
    session: AsyncSession,
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    result_filter: AuditResult | None = None,
) -> list[AuditLog]:
    """Paginated audit log retrieval."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

    if agent_id:
        stmt = stmt.where(AuditLog.agent_id == agent_id)
    if result_filter:
        stmt = stmt.where(AuditLog.result == result_filter)

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
