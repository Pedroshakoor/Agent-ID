"""Tests for credential issuance and verification."""

import pytest
from httpx import AsyncClient


async def _create_agent(client: AsyncClient, name: str = "cred-agent") -> tuple[str, str]:
    resp = await client.post(
        "/v1/agents",
        json={"name": name, "owner_id": "owner-cred"},
    )
    data = resp.json()
    return data["id"], data["api_key"]


@pytest.mark.asyncio
async def test_issue_credential(client: AsyncClient):
    agent_id, api_key = await _create_agent(client)

    resp = await client.post(
        "/v1/credentials/issue",
        json={"agent_id": agent_id},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "jti" in data
    assert "expires_at" in data
    assert "scope" in data


@pytest.mark.asyncio
async def test_issue_credential_wrong_key(client: AsyncClient):
    agent_id, _ = await _create_agent(client, "bad-key-agent")

    resp = await client.post(
        "/v1/credentials/issue",
        json={"agent_id": agent_id},
        headers={"X-API-Key": "agid_wrong_key"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_valid_token(client: AsyncClient):
    agent_id, api_key = await _create_agent(client, "verify-agent")

    issue_resp = await client.post(
        "/v1/credentials/issue",
        json={"agent_id": agent_id},
        headers={"X-API-Key": api_key},
    )
    token = issue_resp.json()["token"]

    verify_resp = await client.post(
        "/v1/verify",
        json={"action": "read", "resource": "file:report.pdf"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["allowed"] is True
    assert data["agent_id"] == agent_id


@pytest.mark.asyncio
async def test_verify_invalid_token(client: AsyncClient):
    resp = await client.post(
        "/v1/verify",
        json={"action": "read", "resource": "file:test"},
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False


@pytest.mark.asyncio
async def test_revoke_credential(client: AsyncClient):
    agent_id, api_key = await _create_agent(client, "revoke-agent")

    issue_resp = await client.post(
        "/v1/credentials/issue",
        json={"agent_id": agent_id},
        headers={"X-API-Key": api_key},
    )
    data = issue_resp.json()
    cred_id = data["credential_id"]
    token = data["token"]

    # Revoke it
    revoke_resp = await client.post(
        f"/v1/credentials/{cred_id}/revoke",
        params={"reason": "test revocation"},
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked"] is True

    # Verify should now fail
    verify_resp = await client.post(
        "/v1/verify",
        json={"action": "read", "resource": "anything"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_resp.json()["allowed"] is False
    assert "revoked" in verify_resp.json()["reason"].lower()
