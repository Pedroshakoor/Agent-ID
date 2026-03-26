"""Tests for agent registration and management."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_agent(client: AsyncClient):
    resp = await client.post(
        "/v1/agents",
        json={
            "name": "test-agent",
            "owner_id": "user-123",
            "description": "A test agent",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-agent"
    assert data["owner_id"] == "user-123"
    assert "api_key" in data
    assert data["api_key"].startswith("agid_")
    assert "id" in data


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    # Create two agents
    for i in range(2):
        await client.post(
            "/v1/agents",
            json={"name": f"agent-{i}", "owner_id": "owner-1"},
        )

    resp = await client.get("/v1/agents", params={"owner_id": "owner-1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient):
    create_resp = await client.post(
        "/v1/agents",
        json={"name": "fetch-me", "owner_id": "owner-x"},
    )
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == agent_id


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient):
    resp = await client.get("/v1/agents/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient):
    create_resp = await client.post(
        "/v1/agents",
        json={"name": "before-update", "owner_id": "owner-y"},
    )
    agent_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/v1/agents/{agent_id}",
        json={"name": "after-update", "description": "updated desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "after-update"
    assert resp.json()["description"] == "updated desc"


@pytest.mark.asyncio
async def test_list_agent_policies(client: AsyncClient):
    create_resp = await client.post(
        "/v1/agents",
        json={"name": "policy-agent", "owner_id": "owner-p"},
    )
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/v1/agents/{agent_id}/policies")
    assert resp.status_code == 200
    policies = resp.json()
    assert len(policies) >= 1  # default policy created on registration
