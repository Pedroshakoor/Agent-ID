"""Agent registration and management endpoints."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.agent import Agent, AgentCreate, AgentRead, AgentReadWithKey, AgentUpdate
from app.models.policy import Policy, PolicyCreate
from app.services.jwt_service import generate_api_key, hash_api_key

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentReadWithKey, status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: AgentCreate,
    session: AsyncSession = Depends(get_session),
) -> AgentReadWithKey:
    """Register a new agent. Returns the agent record + a one-time API key."""
    api_key = generate_api_key()
    agent_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        name=body.name,
        description=body.description,
        owner_id=body.owner_id,
        framework=body.framework,
        tags=body.tags,
        status=body.status,
        metadata_json=body.metadata_json,
        api_key_hash=hash_api_key(api_key),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(agent)

    # Create initial policies
    initial_policies = body.policies or [
        {
            "effect": "allow",
            "resources": ["*"],
            "actions": ["*"],
            "conditions": {},
        }
    ]
    for i, pol_dict in enumerate(initial_policies):
        policy = Policy(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            name=f"policy-{i + 1}",
            policy_json=json.dumps(pol_dict),
            enabled=True,
            priority=i,
        )
        session.add(policy)

    await session.flush()

    return AgentReadWithKey(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        owner_id=agent.owner_id,
        framework=agent.framework,
        tags=agent.tags,
        status=agent.status,
        metadata_json=agent.metadata_json,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_active_at=agent.last_active_at,
        api_key=api_key,
    )


@router.get("", response_model=list[AgentRead])
async def list_agents(
    owner_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[AgentRead]:
    stmt = select(Agent).order_by(Agent.created_at.desc()).offset(offset).limit(limit)
    if owner_id:
        stmt = stmt.where(Agent.owner_id == owner_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())  # type: ignore


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> AgentRead:
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent  # type: ignore


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    session: AsyncSession = Depends(get_session),
) -> AgentRead:
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)
    agent.updated_at = datetime.now(timezone.utc)
    session.add(agent)

    return agent  # type: ignore


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.delete(agent)


@router.post("/{agent_id}/policies", status_code=status.HTTP_201_CREATED)
async def add_policy(
    agent_id: str,
    body: PolicyCreate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate JSON
    try:
        json.loads(body.policy_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid policy JSON: {e}") from e

    policy = Policy(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        name=body.name,
        description=body.description,
        policy_json=body.policy_json,
        enabled=body.enabled,
        priority=body.priority,
    )
    session.add(policy)
    await session.flush()
    return {"id": policy.id, "name": policy.name}


@router.get("/{agent_id}/policies")
async def list_policies(
    agent_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    agent = await session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    stmt = select(Policy).where(Policy.agent_id == agent_id).order_by(Policy.priority.desc())
    result = await session.execute(stmt)
    policies = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "policy": json.loads(p.policy_json),
            "enabled": p.enabled,
            "priority": p.priority,
        }
        for p in policies
    ]
